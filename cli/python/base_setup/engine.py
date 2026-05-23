from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

from .manifest import BaseManifest, ManifestError, discover_manifest, read_manifest
from .registry import ArtifactDefinition, get_artifact_definition


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Base project artifact setup.")
    parser.add_argument("project", nargs="?", help="Expected project name from base_manifest.yaml.")
    parser.add_argument("--manifest", help="Path to base_manifest.yaml.")
    parser.add_argument("--start-dir", default=os.getcwd(), help="Directory where manifest discovery should start.")
    parser.add_argument("--dry-run", action="store_true", help="Log planned changes without making them.")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).resolve() if args.manifest else discover_manifest(Path(args.start_dir))
    if manifest_path is None:
        if args.project:
            error(f"No base_manifest.yaml found while setting up project '{args.project}'.")
            return 1
        info("No base_manifest.yaml found; skipping project artifact setup.")
        return 0

    try:
        manifest = read_manifest(manifest_path)
        validate_project_name(manifest, args.project)
        reconcile_manifest(manifest, dry_run=args.dry_run)
    except ManifestError as exc:
        error(str(exc))
        return 1
    except ArtifactError as exc:
        error(str(exc))
        return 1

    return 0


class ArtifactError(RuntimeError):
    pass


def validate_project_name(manifest: BaseManifest, expected_project: str | None) -> None:
    if expected_project and manifest.project_name != expected_project:
        raise ManifestError(
            f"{manifest.path}: project.name is '{manifest.project_name}', expected '{expected_project}'."
        )


def reconcile_manifest(manifest: BaseManifest, dry_run: bool) -> None:
    info(f"Reading Base manifest at '{manifest.path}'.")
    info(f"Setting up project '{manifest.project_name}'.")

    project_root = manifest.path.parent
    if not manifest.artifacts:
        info(f"Project '{manifest.project_name}' declares no artifacts.")
        info(f"Project '{manifest.project_name}' artifact setup is complete.")
        return

    for artifact in manifest.artifacts:
        definition = get_artifact_definition(artifact.artifact_type, artifact.name)
        if definition is None:
            raise ArtifactError(
                "Unsupported artifact "
                f"'{artifact.name}' of type '{artifact.artifact_type}'. "
                "Base does not know how to manage this artifact yet."
            )
        reconcile_artifact(project_root, definition, artifact.version, dry_run=dry_run)

    info(f"Project '{manifest.project_name}' artifact setup is complete.")


def reconcile_artifact(project_root: Path, definition: ArtifactDefinition, version: str, dry_run: bool) -> None:
    if definition.manager == "homebrew":
        reconcile_homebrew_artifact(definition, version, dry_run=dry_run)
        return
    if definition.manager == "pip":
        reconcile_python_artifact(project_root, definition, version, dry_run=dry_run)
        return
    raise ArtifactError(f"Artifact manager '{definition.manager}' is not implemented.")


def reconcile_homebrew_artifact(definition: ArtifactDefinition, version: str, dry_run: bool) -> None:
    command = ["brew", "install", definition.package]
    if dry_run:
        dry_run_command(command)
        return

    if not command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install artifact '{definition.name}'.")

    if run_check(["brew", "list", definition.package]):
        info(f"Artifact '{definition.name}' is already installed via Homebrew package '{definition.package}'.")
        return

    info(f"Installing artifact '{definition.name}' via Homebrew package '{definition.package}' ({version}).")
    run_command(command)


def reconcile_python_artifact(project_root: Path, definition: ArtifactDefinition, version: str, dry_run: bool) -> None:
    venv_dir = project_root / ".base" / ".venv"
    python_bin = venv_dir / "bin" / "python"
    requirement = f"{definition.package}=={version}" if version != "latest" else definition.package

    if dry_run:
        if not python_bin.exists():
            info(f"[DRY-RUN] Would create project virtual environment at '{venv_dir}'.")
        dry_run_command([str(python_bin), "-m", "pip", "install", requirement])
        return

    if not python_bin.exists():
        info(f"Creating project virtual environment at '{venv_dir}'.")
        venv.create(venv_dir, with_pip=True)

    info(f"Installing Python artifact '{definition.name}' into project virtual environment.")
    run_command([str(python_bin), "-m", "pip", "install", requirement])


def command_exists(name: str) -> bool:
    return any((Path(directory) / name).is_file() and os.access(Path(directory) / name, os.X_OK) for directory in os.environ.get("PATH", "").split(os.pathsep))


def run_check(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise ArtifactError(f"Command failed with exit {completed.returncode}: {format_command(command)}")


def dry_run_command(command: list[str]) -> None:
    info(f"[DRY-RUN] Would run: {format_command(command)}")


def format_command(command: list[str]) -> str:
    return " ".join(_quote_arg(arg) for arg in command)


def _quote_arg(arg: str) -> str:
    if arg and all(char.isalnum() or char in "/._=:@+-" for char in arg):
        return arg
    return "'" + arg.replace("'", "'\"'\"'") + "'"


def info(message: str) -> None:
    print(f"INFO: {message}")


def error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
