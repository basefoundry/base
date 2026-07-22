from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import base_cli

from . import process
from . import remote_installers
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest
from .platform_policy import current_base_platform
from .user_paths import prepend_user_local_bin_to_path
from .user_paths import user_local_bin

def check_mise(manifest: BaseManifest) -> ArtifactCheck:
    try:
        mise_path = resolve_mise_path(manifest)
    except ArtifactError as exc:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=str(exc),
            fix=f"Update '{manifest.path}' or run 'basectl setup {manifest.project_name}'.",
            finding_id="BASE-P020",
        )

    mise_bin = mise_executable()
    if mise_bin is None:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise is not available, but the manifest declares project config '{mise_path}'.",
            fix=(
                f"Run 'basectl setup {manifest.project_name} --dry-run' to review the mise bootstrap, "
                "then rerun with '--yes', or install mise manually."
            ),
            finding_id="BASE-P021",
            status="warn",
        )

    project_root = manifest.path.parent.resolve()
    details = mise_details(project_root, mise_path)
    trust_problem = check_mise_trust(project_root, mise_path, mise_bin, details)
    if trust_problem is not None:
        return trust_problem

    verified_details = details | {"trusted": True, "missing_tools_checked": True}
    missing_problem = check_mise_missing_tools(manifest, project_root, mise_path, mise_bin, verified_details)
    if missing_problem is not None:
        return missing_problem

    return ArtifactCheck(
        name="mise",
        ok=True,
        message=f"mise config '{mise_path}' is trusted and mise-managed tools are installed.",
        fix="",
        finding_id="BASE-P022",
        details=verified_details,
    )


def check_mise_trust(
    project_root: Path,
    mise_path: Path,
    mise_bin: Path,
    details: dict[str, object],
) -> ArtifactCheck | None:
    try:
        trust_check = process.run_capture(
            [str(mise_bin), "trust", "--show"],
            cwd=project_root,
            timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=(
                f"mise trust status check for '{mise_path}' timed out after "
                f"{process.DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
            ),
            fix=f"Retry 'mise trust --show' in '{project_root}'.",
            status="warn",
            finding_id="BASE-P022",
            details=details,
        )
    trust_text = command_text(trust_check.stdout, trust_check.stderr)
    if trust_check.returncode != 0:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise trust status could not be checked for '{mise_path}'.",
            fix=f"Run 'mise trust --show' in '{project_root}' for details.",
            status="warn",
            finding_id="BASE-P022",
            details=details | {"returncode": trust_check.returncode},
        )
    if mise_config_untrusted(trust_text):
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise config '{mise_path}' is not trusted by mise.",
            fix=f"mise trust {mise_path}",
            finding_id="BASE-P022",
            details=details | {"trusted": False},
        )
    if "trusted" not in trust_text.lower():
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise trust status for '{mise_path}' could not be determined.",
            fix=f"Run 'mise trust --show' in '{project_root}' for details.",
            status="warn",
            finding_id="BASE-P022",
            details=details,
        )
    return None


def check_mise_missing_tools(
    manifest: BaseManifest,
    project_root: Path,
    mise_path: Path,
    mise_bin: Path,
    details: dict[str, object],
) -> ArtifactCheck | None:
    try:
        missing_check = process.run_capture(
            [str(mise_bin), "ls", "--missing", "--json"],
            cwd=project_root,
            timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=(
                f"mise missing-tool status check for '{mise_path}' timed out after "
                f"{process.DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
            ),
            fix=f"Retry 'mise ls --missing --json' in '{project_root}'.",
            status="warn",
            finding_id="BASE-P022",
            details=details,
        )
    if missing_check.returncode != 0:
        missing_text = command_text(missing_check.stdout, missing_check.stderr)
        if mise_config_untrusted(missing_text):
            return ArtifactCheck(
                name="mise",
                ok=False,
                message=f"mise config '{mise_path}' is not trusted by mise.",
                fix=f"mise trust {mise_path}",
                finding_id="BASE-P022",
                details=details | {"trusted": False, "returncode": missing_check.returncode},
            )
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise missing-tool status could not be checked for '{mise_path}'.",
            fix=f"Run 'mise ls --missing --json' in '{project_root}' for details.",
            status="warn",
            finding_id="BASE-P022",
            details=details | {"returncode": missing_check.returncode},
        )

    try:
        missing_payload = json.loads(missing_check.stdout or "{}")
    except json.JSONDecodeError:
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise missing-tool output for '{mise_path}' could not be parsed as JSON.",
            fix=f"Run 'mise ls --missing --json' in '{project_root}' for details.",
            status="warn",
            finding_id="BASE-P022",
            details=details,
        )

    missing_tools = missing_tool_names(missing_payload)
    if missing_tools:
        tool_list = ", ".join(missing_tools)
        return ArtifactCheck(
            name="mise",
            ok=False,
            message=f"mise-managed tools are missing for project config '{mise_path}': {tool_list}.",
            fix=f"basectl setup {manifest.project_name}",
            finding_id="BASE-P022",
            details=details | {"missing_tools": missing_tools},
        )
    return None


def mise_details(project_root: Path, mise_path: Path) -> dict[str, object]:
    return {
        "project_root": str(project_root),
        "mise_config": str(mise_path),
        "trust_checked": True,
        "missing_tools_checked": False,
    }


def reconcile_mise(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    if manifest.mise is None:
        return

    mise_path = resolve_mise_path(manifest)
    project_root = manifest.path.parent.resolve()
    mise_bin = ensure_mise_available(ctx, manifest, dry_run=dry_run)
    command = ["mise", "install"] if dry_run else [str(mise_bin), "install"]
    if dry_run:
        process.dry_run_command(ctx, command, cwd=project_root)
        return

    require_mise_trusted_for_setup(manifest, project_root, mise_path, mise_bin)
    ctx.log.info("Installing mise-managed tools from '%s'.", mise_path)
    process.run_command(ctx, command, cwd=project_root, echo_output=False)


def require_mise_trusted_for_setup(
    manifest: BaseManifest,
    project_root: Path,
    mise_path: Path,
    mise_bin: Path,
) -> None:
    trust_problem = check_mise_trust(project_root, mise_path, mise_bin, mise_details(project_root, mise_path))
    if trust_problem is None:
        return

    raise ArtifactError(
        f"{trust_problem.message} "
        f"Run '{trust_problem.fix}', then rerun 'basectl setup {manifest.project_name} --yes'."
    )


def ensure_mise_available(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> Path:
    mise_bin = mise_executable()
    if mise_bin is not None:
        return mise_bin

    if current_base_platform() != "linux-debian":
        raise ArtifactError("mise is required to set up this project. Install mise and rerun basectl setup.")

    if dry_run:
        remote_installers.run_remote_installer(ctx, remote_installers.MISE_REMOTE_INSTALLER, dry_run=True)
        return Path("mise")

    if os.environ.get("BASE_SETUP_YES") != "true":
        raise ArtifactError(
            f"mise is required to set up project '{manifest.project_name}'. "
            f"Run 'basectl setup {manifest.project_name} --dry-run' to review the mise bootstrap, "
            "then rerun with '--yes' to apply it."
        )

    ctx.log.info("Bootstrapping mise for project '%s'.", manifest.project_name)
    remote_installers.run_remote_installer(ctx, remote_installers.MISE_REMOTE_INSTALLER, dry_run=False)
    prepend_user_local_bin_to_path()
    mise_bin = mise_executable()
    if mise_bin is None:
        raise ArtifactError(
            "mise bootstrap completed, but mise was not found. "
            "Add '$HOME/.local/bin' to PATH or install mise, then rerun basectl setup."
        )
    return mise_bin


def command_text(stdout: str, stderr: str) -> str:
    return "\n".join(part for part in (stdout, stderr) if part)


def mise_config_untrusted(output: str) -> bool:
    normalized = output.lower()
    return "untrusted" in normalized or "no trusted config files found" in normalized or "not trusted" in normalized


def missing_tool_names(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["unknown"] if payload else []
    names = [str(name) for name, value in payload.items() if value]
    return sorted(names)


def mise_executable() -> Path | None:
    resolved = shutil.which("mise")
    if resolved:
        return Path(resolved)

    candidate = user_local_bin() / "mise"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    return None


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
