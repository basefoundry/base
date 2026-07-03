from __future__ import annotations

import os
import shutil
from pathlib import Path

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest
from .platform_policy import current_base_platform


UV_INSTALL_COMMAND_TEXT = "curl -LsSf https://astral.sh/uv/install.sh | sh"


def manifest_uses_uv_project_manager(manifest: BaseManifest) -> bool:
    return manifest.python.manager == "uv"


def manifest_declares_uv_runner(manifest: BaseManifest) -> bool:
    if manifest.test is not None and manifest.test.runner == "uv":
        return True
    if any(command.runner == "uv" for command in manifest.commands.values()):
        return True
    if manifest.demo is not None and manifest.demo.runner == "uv":
        return True
    if manifest.release is not None and manifest.release.runner == "uv":
        return True
    if manifest.build is not None:
        return any(target.runner == "uv" for target in manifest.build.targets.values())
    return False


def reconcile_uv_project(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    uses_uv_manager = manifest_uses_uv_project_manager(manifest)
    uses_uv_runner = manifest_declares_uv_runner(manifest)
    if not uses_uv_manager and not uses_uv_runner:
        return

    uv_bin = ensure_uv_available(ctx, manifest, dry_run=dry_run)
    if not uses_uv_manager:
        return

    project_root = manifest.path.parent
    command = ["uv", "sync"] if dry_run else [str(uv_bin), "sync"]
    if dry_run:
        process.dry_run_command(ctx, command, cwd=project_root)
        return
    if process.run_check([str(uv_bin), "sync", "--check"], cwd=project_root):
        ctx.log.info("uv project environment is already synchronized for '%s'.", project_root)
        return
    process.run_command(ctx, command, cwd=project_root)


def check_uv(manifest: BaseManifest) -> tuple[ArtifactCheck, ...]:
    uses_uv_manager = manifest_uses_uv_project_manager(manifest)
    uses_uv_runner = manifest_declares_uv_runner(manifest)
    if not uses_uv_manager and not uses_uv_runner:
        return ()

    checks: list[ArtifactCheck] = []
    uv_available = uv_executable() is not None
    checks.append(uv_tool_check(manifest.project_name, uv_available, uses_uv_manager, uses_uv_runner))

    if uses_uv_manager:
        checks.append(pyproject_check(manifest.path.parent / "pyproject.toml"))
        checks.append(uv_lock_check(manifest.path.parent / "uv.lock"))
        checks.append(uv_project_venv_check(manifest.path.parent / ".venv"))
        stale_check = stale_base_venv_check(manifest)
        if stale_check is not None:
            checks.append(stale_check)

    return tuple(checks)


def uv_tool_check(project_name: str, uv_available: bool, uses_uv_manager: bool, uses_uv_runner: bool) -> ArtifactCheck:
    if uv_available:
        return ArtifactCheck(
            name="uv",
            ok=True,
            message="uv is available for Base-declared uv project or command runner support.",
            fix="",
            finding_id="BASE-P150",
        )

    reason = "uv project manager" if uses_uv_manager else "uv runner"
    if uses_uv_manager and uses_uv_runner:
        reason = "uv project manager and uv runner"
    return ArtifactCheck(
        name="uv",
        ok=False,
        message=f"uv is not available, but the manifest declares {reason} support.",
        fix=(
            f"Run 'basectl setup {project_name} --dry-run' to review the uv bootstrap, "
            "then rerun with '--yes', or install uv manually."
        ),
        finding_id="BASE-P150",
        status="warn",
    )


def ensure_uv_available(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> Path:
    uv_bin = uv_executable()
    if uv_bin is not None:
        return uv_bin

    if current_base_platform() != "linux-debian":
        raise ArtifactError("uv is required to set up this project. Install uv and rerun basectl setup.")

    if dry_run:
        ctx.log.info("[DRY-RUN] Would bootstrap uv: %s", UV_INSTALL_COMMAND_TEXT)
        return Path("uv")

    if os.environ.get("BASE_SETUP_YES") != "true":
        raise ArtifactError(
            f"uv is required to set up project '{manifest.project_name}'. "
            f"Run 'basectl setup {manifest.project_name} --dry-run' to review the uv bootstrap, "
            "then rerun with '--yes' to apply it."
        )

    ctx.log.info("Bootstrapping uv for project '%s'.", manifest.project_name)
    process.run_command(ctx, ["sh", "-c", UV_INSTALL_COMMAND_TEXT])
    prepend_user_local_bin_to_path()
    uv_bin = uv_executable()
    if uv_bin is None:
        raise ArtifactError(
            "uv bootstrap completed, but uv was not found. "
            "Add '$HOME/.local/bin' to PATH or install uv, then rerun basectl setup."
        )
    return uv_bin


def uv_executable() -> Path | None:
    resolved = shutil.which("uv")
    if resolved:
        return Path(resolved)

    candidate = user_local_bin() / "uv"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    return None


def user_local_bin() -> Path:
    return Path.home() / ".local" / "bin"


def prepend_user_local_bin_to_path() -> None:
    bin_dir = str(user_local_bin())
    current_path = os.environ.get("PATH", "")
    path_entries = current_path.split(os.pathsep) if current_path else []
    if bin_dir not in path_entries:
        os.environ["PATH"] = os.pathsep.join([bin_dir, *path_entries]) if path_entries else bin_dir


def pyproject_check(pyproject_path: Path) -> ArtifactCheck:
    if pyproject_path.is_file():
        return ArtifactCheck(
            name="uv pyproject",
            ok=True,
            message=f"uv project pyproject.toml exists at '{pyproject_path}'.",
            fix="",
            finding_id="BASE-P151",
        )
    return ArtifactCheck(
        name="uv pyproject",
        ok=False,
        message=f"uv project manager is declared, but '{pyproject_path}' does not exist.",
        fix="Create pyproject.toml or remove python.manager: uv from base_manifest.yaml.",
        finding_id="BASE-P151",
        status="warn",
    )


def uv_lock_check(lock_path: Path) -> ArtifactCheck:
    if lock_path.is_file():
        return ArtifactCheck(
            name="uv lockfile",
            ok=True,
            message=f"uv lockfile exists at '{lock_path}'.",
            fix="",
            finding_id="BASE-P152",
        )
    return ArtifactCheck(
        name="uv lockfile",
        ok=False,
        message=f"uv project manager is declared, but '{lock_path}' does not exist.",
        fix="Run 'uv lock' or 'uv sync' from the project root.",
        finding_id="BASE-P152",
        status="warn",
    )


def uv_project_venv_check(venv_path: Path) -> ArtifactCheck:
    python_path = venv_path / "bin" / "python"
    if python_path.is_file() and os.access(python_path, os.X_OK):
        return ArtifactCheck(
            name="uv project virtualenv",
            ok=True,
            message=f"uv project virtualenv exists at '{venv_path}'.",
            fix="",
            finding_id="BASE-P154",
        )
    return ArtifactCheck(
        name="uv project virtualenv",
        ok=False,
        message=f"uv project manager is declared, but '{python_path}' does not exist or is not executable.",
        fix="Run 'uv sync' from the project root.",
        finding_id="BASE-P154",
        status="warn",
    )


def stale_base_venv_check(manifest: BaseManifest) -> ArtifactCheck | None:
    stale_venv = Path.home() / ".base.d" / manifest.project_name / ".venv"
    if not stale_venv.exists():
        return None
    return ArtifactCheck(
        name="uv stale Base venv",
        ok=False,
        message=f"uv project manager is declared; Base will ignore stale project venv '{stale_venv}'.",
        fix="Remove the stale Base-managed project venv after confirming the uv project .venv is healthy.",
        finding_id="BASE-P153",
        status="warn",
    )
