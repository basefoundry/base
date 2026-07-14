from __future__ import annotations

import os
import subprocess
import time
import venv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import base_cli

from . import process
from .errors import ArtifactError
from .python_policy import evaluate_python_requirement
from .python_policy import inspect_python_interpreter
from .python_policy import PythonInterpreter
from .python_policy import resolve_python_interpreter
from .python_policy import version_label
from .project_environment import project_venv_dir_override
from .registry import ArtifactDefinition

PIP_INSTALL_COMMAND_PREFIX = ("-m", "pip", "install", "--disable-pip-version-check")
PYTHON_ARTIFACT_PROBE_TIMEOUT_SECONDS = process.DIAGNOSTIC_TIMEOUT_SECONDS


@dataclass(frozen=True)
class ProjectRuntimeConfig:
    name: str
    python_requirement: str | None = None
    venv_dir: Path | None = None


def reconcile_python_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    project: str | ProjectRuntimeConfig,
    dry_run: bool,
) -> None:
    reconcile_python_artifacts(ctx, ((definition, version),), project, dry_run=dry_run)


def reconcile_python_artifacts(
    ctx: base_cli.Context,
    artifact_definitions: tuple[tuple[ArtifactDefinition, str], ...],
    project: str | ProjectRuntimeConfig,
    dry_run: bool,
) -> None:
    runtime_config = project_runtime_config(project)
    python_requirement = runtime_config.python_requirement
    venv_dir = runtime_config.venv_dir or project_venv_dir(runtime_config.name)
    python_bin = venv_dir / "bin" / "python"
    recreate_venv = project_venv_recreate_enabled()
    missing = []

    if recreate_venv:
        backup_existing_project_venv(ctx, venv_dir, dry_run=dry_run)
    elif python_requirement is not None and python_bin.exists():
        ensure_existing_project_venv_matches_requirement(python_bin, runtime_config.name, python_requirement)

    for definition, version in artifact_definitions:
        if not recreate_venv and python_artifact_installed(python_bin, definition.package, version):
            ctx.log.info(
                "Python artifact '%s' is already installed in the project virtual environment.",
                definition.name,
            )
            continue
        missing.append((definition, version, python_package_requirement(definition, version)))

    if not missing:
        return

    requirements = [requirement for _definition, _version, requirement in missing]

    if dry_run:
        if recreate_venv or not python_bin.exists():
            if python_requirement is None:
                ctx.log.info("[DRY-RUN] Would create project virtual environment at '%s'.", venv_dir)
            else:
                interpreter = project_python_interpreter(python_requirement)
                ctx.log.info(
                    "[DRY-RUN] Would create project virtual environment at '%s' with Python %s from '%s'.",
                    venv_dir,
                    version_label(interpreter.version),
                    interpreter.path,
                )
        process.dry_run_command(ctx, pip_install_command(python_bin, requirements))
        return

    if recreate_venv or not python_bin.exists():
        create_project_virtualenv(ctx, venv_dir, python_requirement)

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


def project_runtime_config(project: str | ProjectRuntimeConfig) -> ProjectRuntimeConfig:
    if isinstance(project, ProjectRuntimeConfig):
        return project
    return ProjectRuntimeConfig(name=project)


def create_project_virtualenv(ctx: base_cli.Context, venv_dir: Path, python_requirement: str | None) -> None:
    if python_requirement is None:
        ctx.log.info("Creating project virtual environment at '%s'.", venv_dir)
        venv.create(venv_dir, with_pip=True)
        return

    interpreter = project_python_interpreter(python_requirement)
    ctx.log.info(
        "Creating project virtual environment at '%s' with Python %s.",
        venv_dir,
        version_label(interpreter.version),
    )
    process.run_command(ctx, [str(interpreter.path), "-m", "venv", str(venv_dir)])


def project_python_interpreter(python_requirement: str) -> PythonInterpreter:
    policy = evaluate_python_requirement(python_requirement)
    if not policy.ok or policy.selected_version is None:
        raise ArtifactError(
            f"python.requires_python '{python_requirement}' {policy.error}. "
            "Choose a Python version supported by Base."
        )
    interpreter = resolve_python_interpreter(policy.selected_version)
    if interpreter is None:
        selected = version_label(policy.selected_version)
        raise ArtifactError(
            f"Python {selected} is not available for python.requires_python '{python_requirement}'. "
            f"Install Python {selected} or update base_manifest.yaml."
        )
    return interpreter


def ensure_existing_project_venv_matches_requirement(
    python_bin: Path,
    project: str,
    python_requirement: str,
) -> None:
    policy = evaluate_python_requirement(python_requirement)
    if not policy.ok or policy.selected_version is None:
        raise ArtifactError(
            f"python.requires_python '{python_requirement}' {policy.error}. "
            "Choose a Python version supported by Base."
        )

    interpreter = inspect_python_interpreter(python_bin)
    if interpreter is None or interpreter.version == policy.selected_version:
        return

    expected = version_label(policy.selected_version)
    actual = version_label(interpreter.version)
    raise ArtifactError(
        f"Project virtual environment '{python_bin.parent.parent}' uses Python {actual}, "
        f"but python.requires_python '{python_requirement}' selects Python {expected}. "
        f"Run 'basectl setup {project} --recreate-venv' to recreate the project virtual environment."
    )


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


def python_package_requirement(definition: ArtifactDefinition, version: str) -> str:
    return f"{definition.package}=={version}" if version != "latest" else definition.package


def pip_install_command(python_bin: Path, requirements: Iterable[str]) -> list[str]:
    return [str(python_bin), *PIP_INSTALL_COMMAND_PREFIX, *requirements]


def project_venv_dir(project: str) -> Path:
    override = project_venv_dir_override(project)
    if override is not None:
        return override
    return Path.home() / ".base.d" / project / ".venv"


def python_artifact_installed(python_bin: Path, package: str, version: str) -> bool:
    if not python_bin.exists():
        return False
    command = [str(python_bin), "-m", "pip", "show", package]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=PYTHON_ARTIFACT_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode:
        return False
    if version == "latest":
        return True
    for line in completed.stdout.splitlines():
        if line.startswith("Version: "):
            return line.removeprefix("Version: ").strip() == version
    return False
