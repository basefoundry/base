from __future__ import annotations

import subprocess
import venv
from pathlib import Path

import base_cli

from .manifest import BaseManifest, ManifestError, discover_manifest, read_manifest
from .registry import ArtifactDefinition, get_artifact_definition


app = base_cli.App(name="base_setup")


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option("--manifest", help="Path to base_manifest.yaml.")
@base_cli.option("--start-dir", default=".", help="Directory where manifest discovery should start.")
@base_cli.option("--dry-run", is_flag=True, help="Log planned changes without making them.")
def run(
    ctx: base_cli.Context,
    project: str | None,
    manifest: str | None,
    start_dir: str,
    dry_run: bool,
) -> int:
    manifest_path = Path(manifest).resolve() if manifest else discover_manifest(Path(start_dir))
    if manifest_path is None:
        if project:
            ctx.log.error("No base_manifest.yaml found while setting up project '%s'.", project)
            return 1
        ctx.log.info("No base_manifest.yaml found; skipping project artifact setup.")
        return 0

    try:
        base_manifest = read_manifest(manifest_path)
        validate_project_name(base_manifest, project)
        reconcile_manifest(ctx, base_manifest, dry_run=dry_run)
        return 0
    except ManifestError as exc:
        ctx.log.error(str(exc))
        return 1
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1


class ArtifactError(RuntimeError):
    pass


def validate_project_name(manifest: BaseManifest, expected_project: str | None) -> None:
    if expected_project and manifest.project_name != expected_project:
        raise ManifestError(
            f"{manifest.path}: project.name is '{manifest.project_name}', expected '{expected_project}'."
        )


def reconcile_manifest(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    ctx.log.info("Reading Base manifest at '%s'.", manifest.path)
    ctx.log.info("Setting up project '%s'.", manifest.project_name)

    project_root = manifest.path.parent
    if not manifest.artifacts:
        ctx.log.info("Project '%s' declares no artifacts.", manifest.project_name)
        ctx.log.info("Project '%s' artifact setup is complete.", manifest.project_name)
        return

    for artifact in manifest.artifacts:
        definition = get_artifact_definition(artifact.artifact_type, artifact.name)
        if definition is None:
            raise ArtifactError(
                "Unsupported artifact "
                f"'{artifact.name}' of type '{artifact.artifact_type}'. "
                "Base does not know how to manage this artifact yet."
            )
        reconcile_artifact(ctx, project_root, definition, artifact.version, dry_run=dry_run)

    ctx.log.info("Project '%s' artifact setup is complete.", manifest.project_name)


def reconcile_artifact(
    ctx: base_cli.Context,
    project_root: Path,
    definition: ArtifactDefinition,
    version: str,
    dry_run: bool,
) -> None:
    if definition.manager == "homebrew":
        reconcile_homebrew_artifact(ctx, definition, version, dry_run=dry_run)
        return
    if definition.manager == "pip":
        reconcile_python_artifact(ctx, project_root, definition, version, dry_run=dry_run)
        return
    raise ArtifactError(f"Artifact manager '{definition.manager}' is not implemented.")


def reconcile_homebrew_artifact(
    ctx: base_cli.Context,
    definition: ArtifactDefinition,
    version: str,
    dry_run: bool,
) -> None:
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
    run_command(command)


def reconcile_python_artifact(
    ctx: base_cli.Context,
    project_root: Path,
    definition: ArtifactDefinition,
    version: str,
    dry_run: bool,
) -> None:
    venv_dir = project_root / ".base" / ".venv"
    python_bin = venv_dir / "bin" / "python"
    requirement = f"{definition.package}=={version}" if version != "latest" else definition.package

    if dry_run:
        if not python_bin.exists():
            ctx.log.info("[DRY-RUN] Would create project virtual environment at '%s'.", venv_dir)
        dry_run_command(ctx, [str(python_bin), "-m", "pip", "install", requirement])
        return

    if not python_bin.exists():
        ctx.log.info("Creating project virtual environment at '%s'.", venv_dir)
        venv.create(venv_dir, with_pip=True)

    ctx.log.info("Installing Python artifact '%s' into project virtual environment.", definition.name)
    run_command([str(python_bin), "-m", "pip", "install", requirement])


def command_exists(name: str) -> bool:
    return any((Path(directory) / name).is_file() and os.access(Path(directory) / name, os.X_OK) for directory in os.environ.get("PATH", "").split(os.pathsep))


def run_check(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise ArtifactError(f"Command failed with exit {completed.returncode}: {format_command(command)}")


def dry_run_command(ctx: base_cli.Context, command: list[str]) -> None:
    ctx.log.info("[DRY-RUN] Would run: %s", format_command(command))


def format_command(command: list[str]) -> str:
    return " ".join(_quote_arg(arg) for arg in command)


def _quote_arg(arg: str) -> str:
    if arg and all(char.isalnum() or char in "/._=:@+-" for char in arg):
        return arg
    return "'" + arg.replace("'", "'\"'\"'") + "'"
