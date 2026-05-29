from __future__ import annotations

from pathlib import Path

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest


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

    if not process.command_exists("brew"):
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=f"Homebrew is required to check Brewfile dependencies from '{brewfile_path}'.",
            fix="basectl setup",
        )

    ok = process.run_check(["brew", "bundle", "check", f"--file={brewfile_path}"])
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

    if not process.command_exists("mise"):
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise is required for project config '{mise_path}'.",
            fix="Install mise, then run 'basectl setup'.",
        )

    return ArtifactCheck(
        name="mise",
        ok=False,
        message=(
            f"mise config '{mise_path}' is present and the mise CLI is available, "
            "but installed mise tools are not verified."
        ),
        fix=f"Run 'basectl setup {manifest.project_name}' to install declared mise tools.",
        status="warn",
    )


def reconcile_brewfile(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    if manifest.brewfile is None:
        return

    brewfile_path = resolve_brewfile_path(manifest)
    command = ["brew", "bundle", f"--file={brewfile_path}"]

    if dry_run:
        process.dry_run_command(ctx, command)
        return

    if not process.command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install Brewfile dependencies from '{brewfile_path}'.")

    ctx.log.info("Installing Homebrew dependencies from Brewfile '%s'.", brewfile_path)
    process.run_command(ctx, command)


def reconcile_mise(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    if manifest.mise is None:
        return

    mise_path = resolve_mise_path(manifest)
    project_root = manifest.path.parent.resolve()
    command = ["mise", "install"]
    if dry_run:
        process.dry_run_command(ctx, command, cwd=project_root)
        return

    if not process.command_exists("mise"):
        raise ArtifactError(f"mise is required to install project tool versions from '{mise_path}'.")

    ctx.log.info("Installing mise-managed tools from '%s'.", mise_path)
    process.run_command(ctx, command, cwd=project_root)


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
