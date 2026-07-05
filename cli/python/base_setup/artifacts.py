from __future__ import annotations

from dataclasses import replace

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import ArtifactRequest
from .platform_policy import current_base_platform
from .prerequisites import HomebrewPackageCheckRequest
from .prerequisites import PrerequisiteCheck
from .prerequisites import check_homebrew_package
from .prerequisites import homebrew_package_outdated
# Keep these re-exports until downstream callers move to base_setup.python_artifacts.
from .python_artifacts import PIP_INSTALL_COMMAND_PREFIX  # pylint: disable=unused-import
from .python_artifacts import backup_existing_project_venv  # pylint: disable=unused-import
from .python_artifacts import create_project_virtualenv  # pylint: disable=unused-import
from .python_artifacts import ensure_existing_project_venv_matches_requirement  # pylint: disable=unused-import
from .python_artifacts import pip_install_command  # pylint: disable=unused-import
from .python_artifacts import project_python_interpreter  # pylint: disable=unused-import
from .python_artifacts import project_runtime_config
from .python_artifacts import project_venv_dir
from .python_artifacts import project_venv_recreate_enabled  # pylint: disable=unused-import
from .python_artifacts import ProjectRuntimeConfig
from .python_artifacts import python_artifact_installed
from .python_artifacts import python_package_requirement  # pylint: disable=unused-import
from .python_artifacts import PYTHON_ARTIFACT_PROBE_TIMEOUT_SECONDS  # pylint: disable=unused-import
from .python_artifacts import reconcile_python_artifact
from .python_artifacts import reconcile_python_artifacts
from .python_artifacts import reconcile_python_artifacts_sequential  # pylint: disable=unused-import
from .registry import ArtifactDefinition, get_artifact_definition

PYTHON_ARTIFACT_COMPAT_EXPORTS = (
    "PIP_INSTALL_COMMAND_PREFIX",
    "ProjectRuntimeConfig",
    "PYTHON_ARTIFACT_PROBE_TIMEOUT_SECONDS",
    "backup_existing_project_venv",
    "create_project_virtualenv",
    "ensure_existing_project_venv_matches_requirement",
    "pip_install_command",
    "project_python_interpreter",
    "project_runtime_config",
    "project_venv_dir",
    "project_venv_recreate_enabled",
    "python_artifact_installed",
    "python_package_requirement",
    "reconcile_python_artifact",
    "reconcile_python_artifacts",
    "reconcile_python_artifacts_sequential",
)

__all__ = (
    "LINUX_DEBIAN_SYSTEM_TOOL_PACKAGES",
    "PYTHON_ARTIFACT_COMPAT_EXPORTS",
    "artifact_check_from_prerequisite",
    "artifact_details",
    "check_artifact",
    "check_homebrew_artifact",
    "check_python_artifact",
    "check_system_package_artifact",
    "merge_artifacts",
    "platform_artifact_definition",
    "reconcile_artifact",
    "reconcile_artifacts",
    "reconcile_homebrew_artifact",
    "reconcile_system_package_artifact",
    "resolve_artifact_definitions",
    *PYTHON_ARTIFACT_COMPAT_EXPORTS,
)

LINUX_DEBIAN_SYSTEM_TOOL_PACKAGES = {
    ("tool", "bats-core"): "bats",
}


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
        definitions.append(platform_artifact_definition(definition))
    return tuple(definitions)


def platform_artifact_definition(definition: ArtifactDefinition) -> ArtifactDefinition:
    if current_base_platform() != "linux-debian":
        return definition

    system_package = LINUX_DEBIAN_SYSTEM_TOOL_PACKAGES.get((definition.artifact_type, definition.name))
    if system_package is None:
        return definition

    return replace(
        definition,
        manager="system-package",
        package=system_package,
        check_kind="system_command",
    )


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
    if definition.manager == "system-package":
        return check_system_package_artifact(project, artifact, definition)
    if definition.manager == "pip":
        return check_python_artifact(project, artifact, definition)
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact manager '{definition.manager}' is not implemented.",
        fix=f"basectl setup {project}",
        finding_id="BASE-P030",
        details=artifact_details(definition),
    )


def artifact_details(definition: ArtifactDefinition) -> dict[str, str]:
    return {
        "artifact_type": definition.artifact_type,
        "artifact": definition.name,
        "manager": definition.manager,
        "package": definition.package,
        "target": definition.target,
        "version_policy": definition.version_policy,
        "check_kind": definition.check_kind,
        "registry_source": definition.registry_source,
    }


def check_homebrew_artifact(
    project: str,
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
) -> ArtifactCheck:
    request = HomebrewPackageCheckRequest(
        name=artifact.name,
        manager=definition.manager,
        version=artifact.version,
        package=definition.package,
        timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        unsupported_manager_message=f"Artifact manager '{definition.manager}' is not implemented.",
        unsupported_manager_fix=f"basectl setup {project}",
        unsupported_manager_finding_id="BASE-P030",
        unsupported_version_message=(
            f"Homebrew artifact '{artifact.name}' specifies version '{artifact.version}', "
            "but Base only supports Homebrew artifact version 'latest' right now."
        ),
        unsupported_version_fix=f"Update '{artifact.name}' in the project manifest to use version 'latest'.",
        unsupported_version_finding_id="BASE-P031",
        missing_homebrew_message=f"Homebrew is required to check artifact '{artifact.name}'.",
        missing_homebrew_fix="basectl setup",
        missing_homebrew_finding_id="BASE-P032",
        timeout_message=(
            f"Homebrew check for artifact '{artifact.name}' timed out after "
            f"{process.DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
        ),
        timeout_fix=f"Retry 'basectl doctor {project}' or inspect Homebrew with 'brew doctor'.",
        timeout_finding_id="BASE-P033",
        outdated_message=f"Artifact '{artifact.name}' is outdated via Homebrew package '{definition.package}'.",
        outdated_fix=f"basectl setup {project}",
        package_finding_id="BASE-P033",
        installed_message=(
            f"Artifact '{artifact.name}' is installed via Homebrew package "
            f"'{definition.package}' and is current."
        ),
        missing_package_message=(
            f"Artifact '{artifact.name}' is not installed via Homebrew package '{definition.package}'."
        ),
        missing_package_fix=f"basectl setup {project}",
        details=artifact_details(definition),
    )
    return artifact_check_from_prerequisite(
        check_homebrew_package(
            request,
            command_exists=process.command_exists,
            run_check=process.run_check,
            package_outdated=homebrew_package_outdated,
        )
    )


def artifact_check_from_prerequisite(check: PrerequisiteCheck) -> ArtifactCheck:
    return ArtifactCheck(
        name=check.name,
        ok=check.ok,
        message=check.message,
        fix=check.fix,
        finding_id=check.finding_id,
        status=check.status,
        details=check.details,
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
            details=artifact_details(definition),
        )
    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Python artifact '{artifact.name}' is not installed in the project virtual environment.",
        fix=f"basectl setup {project}",
        finding_id="BASE-P040",
        details=artifact_details(definition),
    )


def check_system_package_artifact(
    _project: str,
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
) -> ArtifactCheck:
    if artifact.version != "latest":
        return ArtifactCheck(
            name=artifact.name,
            ok=False,
            message=(
                f"System package artifact '{artifact.name}' specifies version '{artifact.version}', "
                "but Base only supports system package artifact version 'latest' right now."
            ),
            fix=f"Update '{artifact.name}' in the project manifest to use version 'latest'.",
            finding_id="BASE-P034",
            details=artifact_details(definition),
        )

    if process.command_exists(definition.package):
        return ArtifactCheck(
            name=artifact.name,
            ok=True,
            message=f"Artifact '{artifact.name}' is available through system package '{definition.package}'.",
            fix="",
            finding_id="BASE-P034",
            details=artifact_details(definition),
        )

    return ArtifactCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact '{artifact.name}' is missing system package '{definition.package}'.",
        fix=f"Run 'basectl setup --yes' or install Ubuntu/Debian package '{definition.package}'.",
        finding_id="BASE-P034",
        details=artifact_details(definition),
    )


def reconcile_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    project: str | ProjectRuntimeConfig,
    dry_run: bool,
) -> None:
    runtime_config = project_runtime_config(project)
    if definition.manager == "homebrew":
        reconcile_homebrew_artifact(ctx, definition, version, dry_run=dry_run)
        return
    if definition.manager == "system-package":
        reconcile_system_package_artifact(ctx, definition, version, dry_run=dry_run)
        return
    if definition.manager == "pip":
        reconcile_python_artifact(ctx, definition, version, runtime_config, dry_run=dry_run)
        return
    raise ArtifactError(f"Artifact manager '{definition.manager}' is not implemented.")


def reconcile_artifacts(
    ctx: base_cli.Context,
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    project: str | ProjectRuntimeConfig,
    dry_run: bool,
) -> None:
    runtime_config = project_runtime_config(project)
    pending_python_artifacts: list[tuple[ArtifactDefinition, str]] = []

    def flush_python_artifacts() -> None:
        nonlocal pending_python_artifacts
        if not pending_python_artifacts:
            return
        reconcile_python_artifacts(
            ctx,
            tuple(pending_python_artifacts),
            runtime_config,
            dry_run=dry_run,
        )
        pending_python_artifacts = []

    for artifact, definition in zip(artifacts, definitions, strict=True):
        if definition.manager == "pip":
            pending_python_artifacts.append((definition, artifact.version))
            continue
        flush_python_artifacts()
        reconcile_artifact(
            ctx,
            definition,
            artifact.version,
            runtime_config,
            dry_run=dry_run,
        )
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


def reconcile_system_package_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    dry_run: bool,
) -> None:
    if version != "latest":
        raise ArtifactError(
            "System package artifact "
            f"'{definition.name}' specifies version '{version}', but Base only supports "
            "system package artifact version 'latest' right now."
        )

    if process.command_exists(definition.package):
        ctx.log.info(
            "Artifact '%s' is already available through system package '%s'.",
            definition.name,
            definition.package,
        )
        return

    if dry_run:
        ctx.log.info(
            "[DRY-RUN] Would require system package '%s' for artifact '%s'.",
            definition.package,
            definition.name,
        )
        return

    raise ArtifactError(
        f"System package '{definition.package}' is required for artifact '{definition.name}'. "
        "Run 'basectl setup --yes' or install the package manually, then rerun setup."
    )
