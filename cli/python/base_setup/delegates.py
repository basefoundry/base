from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest
from .platform_policy import brewfile_delegates_supported, current_base_platform, platform_label
from .user_paths import prepend_user_local_bin_to_path
from .user_paths import user_local_bin


MISE_INSTALL_COMMAND_TEXT = "curl https://mise.run | sh"


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
    process.run_command(ctx, command, cwd=project_root)


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
        ctx.log.info("[DRY-RUN] Would bootstrap mise: %s", MISE_INSTALL_COMMAND_TEXT)
        return Path("mise")

    if os.environ.get("BASE_SETUP_YES") != "true":
        raise ArtifactError(
            f"mise is required to set up project '{manifest.project_name}'. "
            f"Run 'basectl setup {manifest.project_name} --dry-run' to review the mise bootstrap, "
            "then rerun with '--yes' to apply it."
        )

    ctx.log.info("Bootstrapping mise for project '%s'.", manifest.project_name)
    process.run_command(ctx, ["sh", "-c", MISE_INSTALL_COMMAND_TEXT])
    prepend_user_local_bin_to_path()
    mise_bin = mise_executable()
    if mise_bin is None:
        raise ArtifactError(
            "mise bootstrap completed, but mise was not found. "
            "Add '$HOME/.local/bin' to PATH or install mise, then rerun basectl setup."
        )
    return mise_bin


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
