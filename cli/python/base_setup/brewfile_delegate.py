from __future__ import annotations

import os
import subprocess
from pathlib import Path

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest
from .platform_policy import brewfile_delegates_supported, platform_label


def check_brewfile(manifest: BaseManifest) -> ArtifactCheck:
    try:
        brewfile_path = resolve_brewfile_path(manifest)
    except ArtifactError as exc:
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=str(exc),
            fix=f"Update '{manifest.path}' or run 'basectl setup {manifest.project_name}'.",
            finding_id="BASE-P010",
        )

    if not brewfile_delegates_supported():
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=(
                f"Brewfile delegates are macOS/Homebrew-only; skipping '{brewfile_path}' "
                f"on BASE_PLATFORM='{platform_label()}'."
            ),
            fix="Use a platform-native project setup path; for uv projects, install uv and rerun basectl setup/check.",
            finding_id="BASE-P011",
            status="warn",
        )

    if not process.command_exists("brew"):
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=f"Homebrew is required to check Brewfile dependencies from '{brewfile_path}'.",
            fix="basectl setup",
            finding_id="BASE-P011",
        )

    try:
        ok = process.run_check(
            ["brew", "bundle", "check", f"--file={brewfile_path}"],
            env=homebrew_no_auto_update_env(),
            timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ArtifactCheck(
            name="brewfile",
            ok=False,
            message=(
                f"Homebrew Brewfile check for '{brewfile_path}' timed out after "
                f"{process.DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
            ),
            fix=f"Retry 'basectl doctor {manifest.project_name}' or inspect Homebrew with 'brew doctor'.",
            status="warn",
            finding_id="BASE-P012",
        )
    if ok:
        return ArtifactCheck(
            name="brewfile",
            ok=True,
            message=f"Brewfile dependencies are satisfied for '{brewfile_path}'.",
            fix="",
            finding_id="BASE-P012",
        )
    return ArtifactCheck(
        name="brewfile",
        ok=False,
        message=f"Brewfile dependencies are not satisfied for '{brewfile_path}'.",
        fix=f"basectl setup {manifest.project_name}",
        finding_id="BASE-P012",
    )


def reconcile_brewfile(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    if manifest.brewfile is None:
        return

    brewfile_path = resolve_brewfile_path(manifest)
    command = ["brew", "bundle", f"--file={brewfile_path}"]
    check_command = ["brew", "bundle", "check", f"--file={brewfile_path}"]

    if not brewfile_delegates_supported():
        ctx.log.info(
            "Skipping Brewfile '%s' on BASE_PLATFORM='%s'; Brewfile delegates are macOS/Homebrew-only.",
            brewfile_path,
            platform_label(),
        )
        return

    if dry_run:
        process.dry_run_command(ctx, command)
        return

    if not process.command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install Brewfile dependencies from '{brewfile_path}'.")

    env = homebrew_no_auto_update_env()
    if process.run_check(
        check_command,
        env=env,
        timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
    ):
        ctx.log.info("Brewfile dependencies are already satisfied for '%s'.", brewfile_path)
        return

    ctx.log.info("Installing Homebrew dependencies from Brewfile '%s'.", brewfile_path)
    process.run_command(ctx, command, env=env)


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


def homebrew_no_auto_update_env() -> dict[str, str]:
    env = os.environ.copy()
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    return env

