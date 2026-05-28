from __future__ import annotations

import json
import os
import shlex
import subprocess
import venv
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.paths import discover_manifest

from .manifest import ArtifactRequest, BaseManifest, ManifestError, read_manifest
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

    artifacts = merge_artifacts(default_manifest.artifacts, manifest.artifacts)
    definitions = resolve_artifact_definitions(artifacts)
    if not manifest.artifacts:
        if artifacts:
            ctx.log.info(
                "Project '%s' declares no artifacts; installing Base default artifacts only.",
                manifest.project_name,
            )
        else:
            ctx.log.info("Project '%s' has no artifacts to install.", manifest.project_name)

    reconcile_brewfile(ctx, manifest, dry_run=dry_run)

    for artifact, definition in zip(artifacts, definitions, strict=True):
        reconcile_artifact(ctx, definition, artifact.version, dry_run=dry_run)

    ctx.log.info("Project '%s' artifact setup is complete.", manifest.project_name)


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
        reconcile_artifact(ctx, definition, artifact.version, dry_run=dry_run)


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
        ctx.log.info("Checking project '%s' artifacts.", manifest.project_name)
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
    return 0 if all(check.ok for check in checks) else 1


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
    artifacts = merge_artifacts(default_manifest.artifacts, manifest.artifacts)
    definitions = resolve_artifact_definitions(artifacts)

    if manifest.brewfile is not None:
        checks.append(check_brewfile(manifest))

    for artifact, definition in zip(artifacts, definitions, strict=True):
        checks.append(check_artifact(manifest.project_name, artifact, definition))

    if not checks:
        checks.append(
            ArtifactCheck(
                name="manifest",
                ok=True,
                message=f"Project '{manifest.project_name}' declares no artifacts.",
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


def reconcile_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    dry_run: bool,
) -> None:
    if definition.manager == "homebrew":
        reconcile_homebrew_artifact(ctx, definition, version, dry_run=dry_run)
        return
    if definition.manager == "pip":
        reconcile_python_artifact(ctx, definition, version, dry_run=dry_run)
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
    dry_run: bool,
) -> None:
    project = os.environ.get("BASE_PROJECT", "base")
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
    return any(
        (Path(directory) / name).is_file() and os.access(Path(directory) / name, os.X_OK)
        for directory in os.environ.get("PATH", "").split(os.pathsep)
    )


def run_check(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def run_command(ctx: base_cli.Context, command: list[str]) -> None:
    # Keep stdout live for installer progress; capture stderr for persistent failure logs.
    completed = subprocess.run(command, stderr=subprocess.PIPE, text=True, check=False)
    if completed.returncode:
        stderr = (completed.stderr or "").strip()
        message = f"Command failed with exit {completed.returncode}: {format_command(command)}"
        if stderr:
            message = f"{message}\n{stderr}"
        raise ArtifactError(message)
    ctx.log.debug("Command succeeded: %s", format_command(command))


def dry_run_command(ctx: base_cli.Context, command: list[str]) -> None:
    ctx.log.info("[DRY-RUN] Would run: %s", format_command(command))


def format_command(command: list[str]) -> str:
    return shlex.join(command)
