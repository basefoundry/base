from __future__ import annotations

import os
import subprocess
import time
import venv
from collections.abc import Iterable
from pathlib import Path

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import ArtifactRequest
from .registry import ArtifactDefinition, get_artifact_definition

PIP_INSTALL_COMMAND_PREFIX = ("-m", "pip", "install", "--disable-pip-version-check")


def homebrew_no_auto_update_env() -> dict[str, str]:
    env = os.environ.copy()
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    return env


def homebrew_package_outdated(package: str) -> bool:
    completed = process.run_capture(
        ["brew", "outdated", package],
        env=homebrew_no_auto_update_env(),
    )
    return homebrew_outdated_output_contains_package(completed.stdout, package)


def homebrew_outdated_output_contains_package(output: str, package: str) -> bool:
    for line in output.splitlines():
        fields = line.split()
        if fields and fields[0] == package:
            return True
    return False


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
        finding_id="BASE-P030",
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
            finding_id="BASE-P031",
        )
    if not process.command_exists("brew"):
        return ArtifactCheck(
            name=artifact.name,
            ok=False,
            message=f"Homebrew is required to check artifact '{artifact.name}'.",
            fix="basectl setup",
            finding_id="BASE-P032",
        )
    if process.run_check(["brew", "list", definition.package]):
        if homebrew_package_outdated(definition.package):
            return ArtifactCheck(
                name=artifact.name,
                ok=False,
                message=f"Artifact '{artifact.name}' is outdated via Homebrew package '{definition.package}'.",
                fix=f"basectl setup {project}",
                finding_id="BASE-P033",
            )
        return ArtifactCheck(
            name=artifact.name,
            ok=True,
            message=(
                f"Artifact '{artifact.name}' is installed via Homebrew package "
                f"'{definition.package}' and is current."
            ),
            fix="",
            finding_id="BASE-P033",
        )
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact '{artifact.name}' is not installed via Homebrew package '{definition.package}'.",
        fix=f"basectl setup {project}",
        finding_id="BASE-P033",
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
            finding_id="BASE-P040",
        )
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Python artifact '{artifact.name}' is not installed in the project virtual environment.",
        fix=f"basectl setup {project}",
        finding_id="BASE-P040",
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


def reconcile_artifacts(
    ctx: base_cli.Context,
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    project: str,
    dry_run: bool,
) -> None:
    pending_python_artifacts: list[tuple[ArtifactDefinition, str]] = []

    def flush_python_artifacts() -> None:
        nonlocal pending_python_artifacts
        if not pending_python_artifacts:
            return
        reconcile_python_artifacts(ctx, tuple(pending_python_artifacts), project, dry_run=dry_run)
        pending_python_artifacts = []

    for artifact, definition in zip(artifacts, definitions, strict=True):
        if definition.manager == "pip":
            pending_python_artifacts.append((definition, artifact.version))
            continue
        flush_python_artifacts()
        reconcile_artifact(ctx, definition, artifact.version, project, dry_run=dry_run)
    flush_python_artifacts()


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

    install_command = ["brew", "install", definition.package]
    upgrade_command = ["brew", "upgrade", definition.package]
    if dry_run:
        if process.command_exists("brew") and process.run_check(["brew", "list", definition.package]):
            if homebrew_package_outdated(definition.package):
                process.dry_run_command(ctx, upgrade_command)
                return
            ctx.log.info(
                "Artifact '%s' is already installed via Homebrew package '%s' and is current.",
                definition.name,
                definition.package,
            )
            return
        process.dry_run_command(ctx, install_command)
        return

    if not process.command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install artifact '{definition.name}'.")

    if process.run_check(["brew", "list", definition.package]):
        if homebrew_package_outdated(definition.package):
            ctx.log.info(
                "Upgrading outdated artifact '%s' via Homebrew package '%s'.",
                definition.name,
                definition.package,
            )
            process.run_command(ctx, upgrade_command)
            return
        ctx.log.info(
            "Artifact '%s' is already installed via Homebrew package '%s' and is current.",
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
    process.run_command(ctx, install_command)


def reconcile_python_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    project: str,
    dry_run: bool,
) -> None:
    reconcile_python_artifacts(ctx, ((definition, version),), project, dry_run=dry_run)


def reconcile_python_artifacts(
    ctx: base_cli.Context,
    artifact_definitions: tuple[tuple[ArtifactDefinition, str], ...],
    project: str,
    dry_run: bool,
) -> None:
    venv_dir = project_venv_dir(project)
    python_bin = venv_dir / "bin" / "python"
    recreate_venv = project_venv_recreate_enabled()
    missing = []

    if recreate_venv:
        backup_existing_project_venv(ctx, venv_dir, dry_run=dry_run)

    for definition, version in artifact_definitions:
        if not recreate_venv and python_artifact_installed(python_bin, definition.package, version):
            ctx.log.info(
                "Python artifact '%s' is already installed in the project virtual environment.",
                definition.name,
            )
            continue
        missing.append((definition, version, python_requirement(definition, version)))

    if not missing:
        return

    requirements = [requirement for _definition, _version, requirement in missing]

    if dry_run:
        if recreate_venv or not python_bin.exists():
            ctx.log.info("[DRY-RUN] Would create project virtual environment at '%s'.", venv_dir)
        process.dry_run_command(ctx, pip_install_command(python_bin, requirements))
        return

    if recreate_venv or not python_bin.exists():
        ctx.log.info("Creating project virtual environment at '%s'.", venv_dir)
        venv.create(venv_dir, with_pip=True)

    names = ", ".join(definition.name for definition, _version, _requirement in missing)
    ctx.log.info("Installing Python artifacts into project virtual environment: %s.", names)
    command = pip_install_command(python_bin, requirements)
    try:
        process.run_command(ctx, command)
    except ArtifactError as exc:
        if len(missing) == 1:
            raise
        ctx.log.warning("Batch Python artifact install failed; retrying one artifact at a time.")
        ctx.log.debug("Batch Python artifact install failed: %s", exc)
        reconcile_python_artifacts_sequential(ctx, python_bin, missing)


def project_venv_recreate_enabled() -> bool:
    return os.environ.get("BASE_SETUP_RECREATE_PROJECT_VENV") == "true"


def backup_existing_project_venv(ctx: base_cli.Context, venv_dir: Path, dry_run: bool) -> None:
    if not venv_dir.exists():
        return
    timestamp = time.strftime("%Y%m%dT%H%M%S")
    backup_path = venv_dir.with_name(f"{venv_dir.name}.backup.{timestamp}")
    if backup_path.exists():
        raise ArtifactError(f"Project virtual environment backup path already exists at '{backup_path}'.")
    if dry_run:
        ctx.log.info(
            "[DRY-RUN] Would move existing project virtual environment '%s' to '%s'.",
            venv_dir,
            backup_path,
        )
        return
    ctx.log.info("Moving existing project virtual environment '%s' to '%s'.", venv_dir, backup_path)
    venv_dir.rename(backup_path)


def reconcile_python_artifacts_sequential(
    ctx: base_cli.Context,
    python_bin: Path,
    missing: list[tuple[ArtifactDefinition, str, str]],
) -> None:
    for definition, version, requirement in missing:
        if python_artifact_installed(python_bin, definition.package, version):
            ctx.log.info(
                "Python artifact '%s' is already installed in the project virtual environment.",
                definition.name,
            )
            continue
        ctx.log.info("Installing Python artifact '%s' into project virtual environment.", definition.name)
        process.run_command(ctx, pip_install_command(python_bin, (requirement,)))


def python_requirement(definition: ArtifactDefinition, version: str) -> str:
    return f"{definition.package}=={version}" if version != "latest" else definition.package


def pip_install_command(python_bin: Path, requirements: Iterable[str]) -> list[str]:
    return [str(python_bin), *PIP_INSTALL_COMMAND_PREFIX, *requirements]


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
