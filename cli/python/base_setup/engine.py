from __future__ import annotations

# pylint: disable=too-many-lines

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import venv
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.config import UserConfig, read_user_config
from base_cli.paths import discover_manifest

from .manifest import ArtifactRequest, BaseManifest, IdeConfig, ManifestError, read_manifest
from .registry import ArtifactDefinition, get_artifact_definition


app = base_cli.App(name="base_setup")


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    ok: bool
    message: str
    fix: str
    status: str = ""


@dataclass(frozen=True)
class ManifestAction:
    action: str
    dry_run: bool
    output_format: str


@dataclass(frozen=True)
class IdeDefinition:
    name: str
    label: str
    cli: str
    cask: str
    settings_app_dir: str


IDE_DEFINITIONS = {
    "vscode": IdeDefinition(
        name="vscode",
        label="VS Code",
        cli="code",
        cask="visual-studio-code",
        settings_app_dir="Code",
    ),
    "cursor": IdeDefinition(
        name="cursor",
        label="Cursor",
        cli="cursor",
        cask="cursor",
        settings_app_dir="Cursor",
    ),
}


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option("--manifest", help="Path to base_manifest.yaml.")
@base_cli.option("--start-dir", default=".", help="Directory where manifest discovery should start.")
@base_cli.option("--dry-run", is_flag=True, help="Log planned changes without making them.")
@base_cli.option(
    "--action",
    default="setup",
    help="Action to run: setup, bootstrap, check, or doctor. Defaults to setup.",
)
@base_cli.option("--format", "output_format", default="text", help="Output format for check/doctor: text or json.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    project: str | None,
    manifest: str | None,
    start_dir: str,
    dry_run: bool,
    action: str,
    output_format: str,
) -> int:
    manifest_path = Path(manifest).resolve() if manifest else discover_manifest(Path(start_dir))
    if manifest_path is None:
        if project:
            ctx.log.error("No base_manifest.yaml found for project '%s'.", project)
            return 1
        ctx.log.info("No base_manifest.yaml found; skipping project artifact work.")
        return 0

    try:
        base_manifest = read_manifest(manifest_path)
        validate_project_name(base_manifest, project)
        default_manifest = read_default_manifest(ctx)
        return run_manifest_action(ctx, ManifestAction(action, dry_run, output_format), default_manifest, base_manifest)
    except ManifestError as exc:
        ctx.log.error(str(exc))
        return 1
    except ValueError as exc:
        ctx.log.error(str(exc))
        return 1
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1


def run_manifest_action(
    ctx: base_cli.Context,
    manifest_action: ManifestAction,
    default_manifest: BaseManifest,
    base_manifest: BaseManifest,
) -> int:
    action = manifest_action.action
    if action == "setup":
        reconcile_manifest(ctx, default_manifest, base_manifest, dry_run=manifest_action.dry_run)
        return 0
    if action == "bootstrap":
        reconcile_bootstrap_artifacts(ctx, default_manifest, base_manifest, dry_run=manifest_action.dry_run)
        return 0
    if action == "check":
        return check_manifest(ctx, default_manifest, base_manifest, output_format=manifest_action.output_format)
    if action == "doctor":
        return doctor_manifest(default_manifest, base_manifest, output_format=manifest_action.output_format)
    ctx.log.error("Unsupported base_setup action '%s'. Expected setup, bootstrap, check, or doctor.", action)
    return 2


class ArtifactError(RuntimeError):
    pass


def validate_project_name(manifest: BaseManifest, expected_project: str | None) -> None:
    if expected_project and manifest.project_name != expected_project:
        raise ManifestError(
            f"{manifest.path}: project.name is '{manifest.project_name}', expected '{expected_project}'."
        )


def read_default_manifest(ctx: base_cli.Context) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's default artifact manifest.")
    default_manifest_path = ctx.base_home / "lib" / "base" / "default_manifest.yaml"
    return read_manifest(default_manifest_path)


def reconcile_manifest(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    dry_run: bool,
) -> None:
    ctx.log.info("Reading Base manifest at '%s'.", manifest.path)
    ctx.log.info("Setting up project '%s'.", manifest.project_name)
    user_config = read_user_config()
    log_ide_preference_warnings(ctx, ide_preference_warning_checks(manifest, user_config))
    effective_manifest = effective_manifest_with_user_config(manifest, user_config)

    artifacts = merge_artifacts(default_manifest.artifacts, effective_manifest.artifacts)
    definitions = resolve_artifact_definitions(artifacts)
    if not effective_manifest.artifacts:
        if artifacts:
            ctx.log.info(
                "Project '%s' declares no artifacts; installing Base default artifacts only.",
                effective_manifest.project_name,
            )
        else:
            ctx.log.info("Project '%s' has no artifacts to install.", effective_manifest.project_name)

    reconcile_brewfile(ctx, effective_manifest, dry_run=dry_run)
    reconcile_mise(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_installs(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_extensions(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_settings(ctx, effective_manifest, dry_run=dry_run)

    for artifact, definition in zip(artifacts, definitions, strict=True):
        reconcile_artifact(ctx, definition, artifact.version, effective_manifest.project_name, dry_run=dry_run)

    ctx.log.info("Project '%s' setup is complete.", effective_manifest.project_name)


def reconcile_bootstrap_artifacts(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    dry_run: bool,
) -> None:
    ctx.log.info("Bootstrapping project '%s' Python runtime.", manifest.project_name)

    artifacts = tuple(artifact for artifact in default_manifest.artifacts if artifact.bootstrap)
    definitions = resolve_artifact_definitions(artifacts)
    if not artifacts:
        ctx.log.info("Base default manifest declares no bootstrap artifacts.")
        return

    for artifact, definition in zip(artifacts, definitions, strict=True):
        reconcile_artifact(ctx, definition, artifact.version, manifest.project_name, dry_run=dry_run)


def check_manifest(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    output_format: str,
) -> int:
    checks = manifest_checks(default_manifest, manifest)
    if output_format == "json":
        print(json.dumps([check_to_json(check) for check in checks], indent=2))
    elif output_format == "text":
        ctx.log.info("Checking project '%s' manifest requirements.", manifest.project_name)
        for check in checks:
            if check.ok:
                ctx.log.info(check.message)
            else:
                ctx.log.warning(check.message)
                if check.fix:
                    ctx.log.warning("Fix: %s", check.fix)
    else:
        ctx.log.error("Unsupported check output format '%s'. Expected text or json.", output_format)
        return 2
    return 0 if all(check.ok or doctor_status(check) == "warn" for check in checks) else 1


def doctor_manifest(default_manifest: BaseManifest, manifest: BaseManifest, output_format: str) -> int:
    checks = manifest_checks(default_manifest, manifest)
    if output_format == "json":
        print(json.dumps([check_to_doctor_json(check) for check in checks], indent=2))
        return min(sum(1 for check in checks if doctor_status(check) == "error"), 125)
    if output_format != "text":
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.")
        return 2

    error_count = 0
    print(f"\nProject doctor: {manifest.project_name}\n")
    for check in checks:
        status = doctor_status(check)
        if status == "error":
            print_doctor_finding("error", check.name, check.message, check.fix)
            error_count += 1
        else:
            print_doctor_finding(status, check.name, check.message, check.fix)
    return min(error_count, 125)


def manifest_checks(default_manifest: BaseManifest, manifest: BaseManifest) -> tuple[ArtifactCheck, ...]:
    checks: list[ArtifactCheck] = []
    user_config = read_user_config()
    effective_manifest = effective_manifest_with_user_config(manifest, user_config)
    artifacts = merge_artifacts(default_manifest.artifacts, effective_manifest.artifacts)
    definitions = resolve_artifact_definitions(artifacts)

    checks.extend(ide_preference_warning_checks(manifest, user_config))

    if effective_manifest.brewfile is not None:
        checks.append(check_brewfile(effective_manifest))
    if effective_manifest.mise is not None:
        checks.append(check_mise(effective_manifest))

    checks.extend(check_ide_installs(effective_manifest))
    checks.extend(check_ide_extensions(effective_manifest))
    checks.extend(check_ide_settings(effective_manifest))

    for artifact, definition in zip(artifacts, definitions, strict=True):
        checks.append(check_artifact(effective_manifest.project_name, artifact, definition))

    if not checks:
        checks.append(
            ArtifactCheck(
                name="manifest",
                ok=True,
                message=f"Project '{effective_manifest.project_name}' declares no artifacts.",
                fix="",
            )
        )
    return tuple(checks)


def check_brewfile(manifest: BaseManifest) -> ArtifactCheck:
    try:
        brewfile_path = resolve_brewfile_path(manifest)
    except ArtifactError as exc:
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=str(exc),
            fix=f"Update '{manifest.path}' or run 'basectl setup {manifest.project_name}'.",
        )

    if not command_exists("brew"):
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=f"Homebrew is required to check Brewfile dependencies from '{brewfile_path}'.",
            fix="basectl setup",
        )

    ok = run_check(["brew", "bundle", "check", f"--file={brewfile_path}"])
    if ok:
        return ArtifactCheck(
            name="brewfile",
            ok=True,
            message=f"Brewfile dependencies are satisfied for '{brewfile_path}'.",
            fix="",
        )
    return ArtifactCheck(
        name="brewfile",
        ok=False,
        message=f"Brewfile dependencies are not satisfied for '{brewfile_path}'.",
        fix=f"basectl setup {manifest.project_name}",
    )


def check_mise(manifest: BaseManifest) -> ArtifactCheck:
    try:
        mise_path = resolve_mise_path(manifest)
    except ArtifactError as exc:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=str(exc),
            fix=f"Update '{manifest.path}' or run 'basectl setup {manifest.project_name}'.",
        )

    if not command_exists("mise"):
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise is required for project config '{mise_path}'.",
            fix="Install mise, then run 'basectl setup'.",
        )

    return ArtifactCheck(
        name="mise",
        ok=True,
        message=f"mise config '{mise_path}' is present and the mise CLI is available.",
        fix="",
    )


def check_artifact(
    project: str,
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
) -> ArtifactCheck:
    if definition.manager == "homebrew":
        return check_homebrew_artifact(project, artifact, definition)
    if definition.manager == "pip":
        return check_python_artifact(project, artifact, definition)
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact manager '{definition.manager}' is not implemented.",
        fix=f"basectl setup {project}",
    )


def check_homebrew_artifact(
    project: str,
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
) -> ArtifactCheck:
    if artifact.version != "latest":
        return ArtifactCheck(
            name=artifact.name,
            ok=False,
            message=(
                f"Homebrew artifact '{artifact.name}' specifies version '{artifact.version}', "
                "but Base only supports Homebrew artifact version 'latest' right now."
            ),
            fix=f"Update '{artifact.name}' in the project manifest to use version 'latest'.",
        )
    if not command_exists("brew"):
        return ArtifactCheck(
            name=artifact.name,
            ok=False,
            message=f"Homebrew is required to check artifact '{artifact.name}'.",
            fix="basectl setup",
        )
    ok = run_check(["brew", "list", definition.package])
    if ok:
        return ArtifactCheck(
            name=artifact.name,
            ok=True,
            message=f"Artifact '{artifact.name}' is installed via Homebrew package '{definition.package}'.",
            fix="",
        )
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact '{artifact.name}' is not installed via Homebrew package '{definition.package}'.",
        fix=f"basectl setup {project}",
    )


def check_python_artifact(
    project: str,
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
) -> ArtifactCheck:
    venv_dir = project_venv_dir(project)
    python_bin = venv_dir / "bin" / "python"
    if python_artifact_installed(python_bin, definition.package, artifact.version):
        return ArtifactCheck(
            name=artifact.name,
            ok=True,
            message=f"Python artifact '{artifact.name}' is installed in the project virtual environment.",
            fix="",
        )
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Python artifact '{artifact.name}' is not installed in the project virtual environment.",
        fix=f"basectl setup {project}",
    )


def check_to_json(check: ArtifactCheck) -> dict[str, str | bool]:
    return {
        "name": check.name,
        "ok": check.ok,
        "message": check.message,
        "fix": check.fix,
    }


def check_to_doctor_json(check: ArtifactCheck) -> dict[str, str]:
    return {
        "status": doctor_status(check),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def doctor_status(check: ArtifactCheck) -> str:
    return check.status or ("ok" if check.ok else "error")


def print_doctor_finding(status: str, name: str, message: str, fix: str = "") -> None:
    print(f"{status:<5}  {name:<26}  {message}")
    if fix:
        print(f"       Fix: {fix}")


def resolve_artifact_definitions(artifacts: tuple[ArtifactRequest, ...]) -> tuple[ArtifactDefinition, ...]:
    definitions: list[ArtifactDefinition] = []
    for artifact in artifacts:
        definition = get_artifact_definition(artifact.artifact_type, artifact.name)
        if definition is None:
            raise ArtifactError(
                "Unsupported artifact "
                f"'{artifact.name}' of type '{artifact.artifact_type}'. "
                "Base does not know how to manage this artifact yet."
            )
        definitions.append(definition)
    return tuple(definitions)


def effective_manifest_with_user_config(manifest: BaseManifest, user_config: UserConfig) -> BaseManifest:
    return BaseManifest(
        path=manifest.path,
        project_name=manifest.project_name,
        brewfile=manifest.brewfile,
        artifacts=manifest.artifacts,
        ide=effective_ide_config(manifest.ide, user_config),
        mise=manifest.mise,
    )


def effective_ide_config(project_ide: dict[str, IdeConfig], user_config: UserConfig) -> dict[str, IdeConfig]:
    if user_config.ide.enabled is False:
        return {}

    effective: dict[str, IdeConfig] = {}
    ide_names = sorted(set(project_ide) | set(user_config.ide.preferences))
    for ide_name in ide_names:
        user_preference = user_config.ide.preferences.get(ide_name)
        if user_preference is not None and user_preference.enabled is False:
            continue

        project_config = project_ide.get(ide_name, IdeConfig(install=False, extensions=(), settings={}))
        install = project_config.install
        if user_preference is not None and user_preference.install is not None:
            install = user_preference.install

        extensions = list(project_config.extensions)
        if user_preference is not None:
            for extension in user_preference.extra_extensions:
                if extension not in extensions:
                    extensions.append(extension)

        settings = {}
        if user_preference is not None:
            settings.update(user_preference.settings)
        settings.update(project_config.settings)

        if install or extensions or settings:
            effective[ide_name] = IdeConfig(
                install=install,
                extensions=tuple(extensions),
                settings=settings,
            )
    return effective


def ide_preference_warning_checks(manifest: BaseManifest, user_config: UserConfig) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    if user_config.ide.enabled is False and manifest.ide:
        checks.append(
            ArtifactCheck(
                name="user IDE config",
                ok=False,
                message="User config disables all IDE setup and checks for this machine.",
                fix="Remove or change 'ide.enabled: false' in ~/.base.d/config.yaml to re-enable IDE work.",
                status="warn",
            )
        )

    for ide_name, project_config in manifest.ide.items():
        user_preference = user_config.ide.preferences.get(ide_name)
        if user_preference is None:
            continue
        if user_preference.enabled is False:
            checks.append(
                ArtifactCheck(
                    name=f"user IDE config: {ide_name}",
                    ok=False,
                    message=f"User config disables {ide_name} IDE setup and checks for this machine.",
                    fix=f"Remove or change 'ide.{ide_name}.enabled: false' in ~/.base.d/config.yaml to re-enable it.",
                    status="warn",
                )
            )
            continue
        conflicting_settings = sorted(set(project_config.settings) & set(user_preference.settings))
        for key in conflicting_settings:
            if project_config.settings[key] == user_preference.settings[key]:
                continue
            checks.append(
                ArtifactCheck(
                    name=f"user IDE setting: {ide_name}.{key}",
                    ok=False,
                    message=(
                        f"User config setting 'ide.{ide_name}.settings.{key}' is ignored because "
                        "the project manifest declares the same setting."
                    ),
                    fix=(
                        f"Remove 'ide.{ide_name}.settings.{key}' from ~/.base.d/config.yaml "
                        "or update the project manifest."
                    ),
                    status="warn",
                )
            )
    return checks


def log_ide_preference_warnings(ctx: base_cli.Context, checks: list[ArtifactCheck]) -> None:
    for check in checks:
        ctx.log.warning(check.message)
        if check.fix:
            ctx.log.warning("Fix: %s", check.fix)


def merge_artifacts(
    default_artifacts: tuple[ArtifactRequest, ...],
    manifest_artifacts: tuple[ArtifactRequest, ...],
) -> tuple[ArtifactRequest, ...]:
    merged: dict[tuple[str, str], ArtifactRequest] = {}

    for artifact in default_artifacts:
        merged[(artifact.artifact_type, artifact.name)] = artifact

    for artifact in manifest_artifacts:
        key = (artifact.artifact_type, artifact.name)
        existing = merged.get(key)
        if existing is not None and existing.version != artifact.version:
            raise ArtifactError(
                "Artifact "
                f"'{artifact.name}' of type '{artifact.artifact_type}' is declared by defaults "
                f"as version '{existing.version}' and by the project manifest as version '{artifact.version}'."
            )
        if existing is not None:
            artifact = ArtifactRequest(
                artifact_type=artifact.artifact_type,
                name=artifact.name,
                version=artifact.version,
                bootstrap=existing.bootstrap or artifact.bootstrap,
            )
        merged[key] = artifact

    return tuple(merged.values())


def reconcile_brewfile(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    if manifest.brewfile is None:
        return

    brewfile_path = resolve_brewfile_path(manifest)
    command = ["brew", "bundle", f"--file={brewfile_path}"]

    if dry_run:
        dry_run_command(ctx, command)
        return

    if not command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install Brewfile dependencies from '{brewfile_path}'.")

    ctx.log.info("Installing Homebrew dependencies from Brewfile '%s'.", brewfile_path)
    run_command(ctx, command)


def reconcile_mise(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    if manifest.mise is None:
        return

    mise_path = resolve_mise_path(manifest)
    project_root = manifest.path.parent.resolve()
    command = ["mise", "install"]
    if dry_run:
        dry_run_command(ctx, command, cwd=project_root)
        return

    if not command_exists("mise"):
        raise ArtifactError(f"mise is required to install project tool versions from '{mise_path}'.")

    ctx.log.info("Installing mise-managed tools from '%s'.", mise_path)
    run_command(ctx, command, cwd=project_root)


def resolve_brewfile_path(manifest: BaseManifest) -> Path:
    if manifest.brewfile is None:
        raise ArtifactError(f"{manifest.path}: brewfile is not configured.")

    brewfile = Path(manifest.brewfile)
    if brewfile.is_absolute():
        raise ArtifactError(f"{manifest.path}: brewfile must be relative to the project root.")

    project_root = manifest.path.parent.resolve()
    brewfile_path = (project_root / brewfile).resolve()
    if not brewfile_path.is_relative_to(project_root):
        raise ArtifactError(f"{manifest.path}: brewfile must stay inside the project root.")
    if not brewfile_path.is_file():
        raise ArtifactError(f"{manifest.path}: brewfile '{manifest.brewfile}' does not exist.")
    return brewfile_path


def resolve_mise_path(manifest: BaseManifest) -> Path:
    if manifest.mise is None:
        raise ArtifactError(f"{manifest.path}: mise is not configured.")

    mise = Path(manifest.mise)
    if mise.is_absolute():
        raise ArtifactError(f"{manifest.path}: mise must be relative to the project root.")
    project_root = manifest.path.parent.resolve()
    mise_path = (project_root / mise).resolve()
    if not mise_path.is_relative_to(project_root):
        raise ArtifactError(f"{manifest.path}: mise must stay inside the project root.")
    if not mise_path.is_file():
        raise ArtifactError(f"{manifest.path}: mise config '{manifest.mise}' does not exist.")
    return mise_path



def reconcile_ide_installs(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        definition = IDE_DEFINITIONS[ide_name]
        if not ide_config.install:
            ctx.log.debug("IDE '%s' does not request installation; skipping cask install.", ide_name)
            continue
        reconcile_ide_install(ctx, definition, dry_run=dry_run)


def reconcile_ide_install(ctx: base_cli.Context, definition: IdeDefinition, dry_run: bool) -> None:
    command = ["brew", "install", "--cask", definition.cask]
    if dry_run:
        dry_run_command(ctx, command)
        return

    if not command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install {definition.label}.")

    if run_check(["brew", "list", "--cask", definition.cask]):
        ctx.log.info("%s is already installed via Homebrew cask '%s'.", definition.label, definition.cask)
    else:
        ctx.log.info("Installing %s via Homebrew cask '%s'.", definition.label, definition.cask)
        run_command(ctx, command)

    if command_exists(definition.cli):
        ctx.log.info("%s CLI '%s' is available on PATH.", definition.label, definition.cli)
    else:
        ctx.log.warning(
            "%s is installed, but CLI '%s' is not on PATH. Enable the IDE shell command before extension setup.",
            definition.label,
            definition.cli,
        )


def check_ide_installs(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        definition = IDE_DEFINITIONS[ide_name]
        if ide_config.install:
            checks.append(check_ide_install(manifest.project_name, definition))
    return checks


def reconcile_ide_extensions(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.extensions:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        if dry_run:
            for extension in ide_config.extensions:
                dry_run_command(ctx, [definition.cli, "--install-extension", extension])
            continue
        if not command_exists(definition.cli):
            ctx.log.warning(
                "%s CLI '%s' is not on PATH; skipping extension setup.",
                definition.label,
                definition.cli,
            )
            continue
        installed_extensions = list_ide_extensions(definition)
        for extension in ide_config.extensions:
            if extension in installed_extensions:
                ctx.log.debug(
                    "%s extension '%s' is already installed.",
                    definition.label,
                    extension,
                )
                continue
            ctx.log.info("Installing %s extension '%s'.", definition.label, extension)
            run_command(ctx, [definition.cli, "--install-extension", extension])


def list_ide_extensions(definition: IdeDefinition) -> set[str]:
    completed = subprocess.run(
        [definition.cli, "--list-extensions"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        stderr = (completed.stderr or "").strip()
        message = f"Unable to list {definition.label} extensions with '{definition.cli} --list-extensions'."
        if stderr:
            message = f"{message}\n{stderr}"
        raise ArtifactError(message)
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def check_ide_extensions(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.extensions:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        checks.extend(
            check_ide_extension(manifest.project_name, definition, extension)
            for extension in ide_config.extensions
        )
    return checks


def check_ide_extension(project: str, definition: IdeDefinition, extension: str) -> ArtifactCheck:
    if not command_exists(definition.cli):
        return ArtifactCheck(
            name=extension,
            ok=False,
            message=(
                f"Cannot check {definition.label} extension '{extension}' "
                f"because CLI '{definition.cli}' is not on PATH."
            ),
            fix=(
                f"Enable the '{definition.cli}' shell command from {definition.label}, "
                f"then run 'basectl setup {project}'."
            ),
        )

    try:
        installed_extensions = list_ide_extensions(definition)
    except ArtifactError as exc:
        return ArtifactCheck(
            name=extension,
            ok=False,
            message=str(exc),
            fix=f"basectl setup {project}",
        )

    if extension in installed_extensions:
        return ArtifactCheck(
            name=extension,
            ok=True,
            message=f"{definition.label} extension '{extension}' is installed.",
            fix="",
        )
    return ArtifactCheck(
        name=extension,
        ok=False,
        message=f"{definition.label} extension '{extension}' is not installed.",
        fix=f"basectl setup {project}",
    )


def reconcile_ide_settings(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.settings:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        resolved_settings = resolve_ide_settings(manifest.project_name, ide_config.settings)
        merge_ide_settings(ctx, definition, resolved_settings, dry_run=dry_run)


def resolve_ide_settings(project: str, settings: dict[str, object]) -> dict[str, object]:
    resolved: dict[str, object] = {}
    for key, value in settings.items():
        if key == "python.defaultInterpreterPath" and value == "auto":
            resolved[key] = str(project_venv_dir(project) / "bin" / "python")
        else:
            resolved[key] = value
    return resolved


def ide_settings_file(definition: IdeDefinition) -> Path:
    home = Path(os.environ.get("HOME") or Path.home()).expanduser()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / definition.settings_app_dir / "User" / "settings.json"
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config").expanduser()
    return config_home / definition.settings_app_dir / "User" / "settings.json"


def read_ide_settings(definition: IdeDefinition) -> dict[str, object]:
    settings_file = ide_settings_file(definition)
    if not settings_file.exists():
        return {}
    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"{settings_file}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ArtifactError(f"{settings_file}: expected a JSON object.")
    return data


def merge_ide_settings(
    ctx: base_cli.Context,
    definition: IdeDefinition,
    desired_settings: dict[str, object],
    dry_run: bool,
) -> None:
    settings_file = ide_settings_file(definition)
    current_settings = read_ide_settings(definition)
    merged_settings = dict(current_settings)
    added: dict[str, object] = {}

    for key, value in desired_settings.items():
        if key not in current_settings:
            merged_settings[key] = value
            added[key] = value
        elif current_settings[key] != value:
            ctx.log.info(
                "%s setting '%s' already set by user; leaving intact.",
                definition.label,
                key,
            )

    if not added:
        ctx.log.debug("%s user settings already contain all Base-managed keys.", definition.label)
        return

    if dry_run:
        for key, value in added.items():
            ctx.log.info(
                "[DRY-RUN] Would set %s user setting '%s' to %s.",
                definition.label,
                key,
                json.dumps(value, sort_keys=True),
            )
        return

    settings_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(settings_file, merged_settings)
    ctx.log.info("Updated %s user settings at '%s'.", definition.label, settings_file)


def write_json_atomic(path: Path, data: dict[str, object]) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        json.dump(data, tmp_file, indent=2, sort_keys=True)
        tmp_file.write("\n")
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


def check_ide_settings(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.settings:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        resolved_settings = resolve_ide_settings(manifest.project_name, ide_config.settings)
        checks.extend(
            check_ide_setting(manifest.project_name, definition, key, value)
            for key, value in resolved_settings.items()
        )
    return checks


def check_ide_setting(
    project: str,
    definition: IdeDefinition,
    key: str,
    expected_value: object,
) -> ArtifactCheck:
    settings_file = ide_settings_file(definition)
    try:
        current_settings = read_ide_settings(definition)
    except ArtifactError as exc:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=False,
            message=str(exc),
            fix=f"Repair '{settings_file}' and run 'basectl setup {project}'.",
        )

    if key not in current_settings:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=False,
            message=f"{definition.label} setting '{key}' is absent from '{settings_file}'.",
            fix=f"basectl setup {project}",
        )
    if current_settings[key] == expected_value:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=True,
            message=f"{definition.label} setting '{key}' matches the Base manifest.",
            fix="",
        )
    return ArtifactCheck(
        name=f"{definition.label} setting: {key}",
        ok=False,
        message=(
            f"{definition.label} setting '{key}' is set to {json.dumps(current_settings[key], sort_keys=True)}; "
            f"expected {json.dumps(expected_value, sort_keys=True)}. Base will not overwrite user settings."
        ),
        fix=f"Update '{settings_file}' manually or remove the key and run 'basectl setup {project}'.",
    )


def check_ide_install(project: str, definition: IdeDefinition) -> ArtifactCheck:
    if not command_exists("brew"):
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=f"Homebrew is required to check {definition.label} installation.",
            fix="basectl setup",
        )

    cask_installed = run_check(["brew", "list", "--cask", definition.cask])
    cli_available = command_exists(definition.cli)

    if cask_installed and cli_available:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=True,
            message=f"{definition.label} is installed and CLI '{definition.cli}' is on PATH.",
            fix="",
        )
    if not cask_installed:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=f"{definition.label} is not installed via Homebrew cask '{definition.cask}'.",
            fix=f"basectl setup {project}",
        )
    return ArtifactCheck(
        name=f"{definition.label} CLI",
        ok=False,
        message=f"{definition.label} is installed, but CLI '{definition.cli}' is not on PATH.",
        fix=f"Enable the '{definition.cli}' shell command from {definition.label}.",
    )


def reconcile_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    project: str,
    dry_run: bool,
) -> None:
    if definition.manager == "homebrew":
        reconcile_homebrew_artifact(ctx, definition, version, dry_run=dry_run)
        return
    if definition.manager == "pip":
        reconcile_python_artifact(ctx, definition, version, project, dry_run=dry_run)
        return
    raise ArtifactError(f"Artifact manager '{definition.manager}' is not implemented.")


def reconcile_homebrew_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    dry_run: bool,
) -> None:
    if version != "latest":
        raise ArtifactError(
            "Homebrew artifact "
            f"'{definition.name}' specifies version '{version}', but Base only supports "
            "Homebrew artifact version 'latest' right now."
        )

    command = ["brew", "install", definition.package]
    if dry_run:
        dry_run_command(ctx, command)
        return

    if not command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install artifact '{definition.name}'.")

    if run_check(["brew", "list", definition.package]):
        ctx.log.info(
            "Artifact '%s' is already installed via Homebrew package '%s'.",
            definition.name,
            definition.package,
        )
        return

    ctx.log.info(
        "Installing artifact '%s' via Homebrew package '%s' (%s).",
        definition.name,
        definition.package,
        version,
    )
    run_command(ctx, command)


def reconcile_python_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    project: str,
    dry_run: bool,
) -> None:
    venv_dir = project_venv_dir(project)
    python_bin = venv_dir / "bin" / "python"
    requirement = f"{definition.package}=={version}" if version != "latest" else definition.package

    if python_artifact_installed(python_bin, definition.package, version):
        ctx.log.info("Python artifact '%s' is already installed in the project virtual environment.", definition.name)
        return

    if dry_run:
        if not python_bin.exists():
            ctx.log.info("[DRY-RUN] Would create project virtual environment at '%s'.", venv_dir)
        dry_run_command(ctx, [str(python_bin), "-m", "pip", "install", requirement])
        return

    if not python_bin.exists():
        ctx.log.info("Creating project virtual environment at '%s'.", venv_dir)
        venv.create(venv_dir, with_pip=True)

    ctx.log.info("Installing Python artifact '%s' into project virtual environment.", definition.name)
    run_command(ctx, [str(python_bin), "-m", "pip", "install", requirement])


def project_venv_dir(project: str) -> Path:
    override = os.environ.get("BASE_PROJECT_VENV_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".base.d" / project / ".venv"


def python_artifact_installed(python_bin: Path, package: str, version: str) -> bool:
    if not python_bin.exists():
        return False
    command = [str(python_bin), "-m", "pip", "show", package]
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
    if completed.returncode:
        return False
    if version == "latest":
        return True
    for line in completed.stdout.splitlines():
        if line.startswith("Version: "):
            return line.removeprefix("Version: ").strip() == version
    return False


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_check(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    # Keep stdout live for installer progress; capture stderr for persistent failure logs.
    completed = subprocess.run(command, cwd=cwd, stderr=subprocess.PIPE, text=True, check=False)
    if completed.returncode:
        stderr = (completed.stderr or "").strip()
        message = f"Command failed with exit {completed.returncode}: {format_command(command)}"
        if stderr:
            message = f"{message}\n{stderr}"
        raise ArtifactError(message)
    if cwd is not None:
        ctx.log.debug("Command succeeded in '%s': %s", cwd, format_command(command))
    else:
        ctx.log.debug("Command succeeded: %s", format_command(command))


def dry_run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    if cwd is not None:
        ctx.log.info("[DRY-RUN] Would run in '%s': %s", cwd, format_command(command))
        return
    ctx.log.info("[DRY-RUN] Would run: %s", format_command(command))


def format_command(command: list[str]) -> str:
    return shlex.join(command)
