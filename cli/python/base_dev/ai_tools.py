from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

import base_cli
from base_setup.errors import ArtifactError
from base_setup.process import dry_run_command, run_command

from .checks import DevCheck


@dataclass(frozen=True)
class AITool:
    name: str
    display_name: str
    version_args: tuple[str, ...]
    installer_url: str
    installer_shell: str


AI_TOOLS = (
    AITool(
        name="codex",
        display_name="Codex CLI",
        version_args=("--version",),
        installer_url="https://chatgpt.com/codex/install.sh",
        installer_shell="sh",
    ),
    AITool(
        name="claude",
        display_name="Claude Code",
        version_args=("--version",),
        installer_url="https://claude.ai/install.sh",
        installer_shell="bash",
    ),
)
AI_REMOTE_INSTALLER_ALLOWLIST = (
    "https://chatgpt.com/codex/install.sh",
    "https://claude.ai/install.sh",
)


def setup_ai_tools(ctx: base_cli.Context, dry_run: bool) -> int:
    ctx.log.info("Setting up Base 'ai' prerequisites.")
    try:
        for tool in AI_TOOLS:
            check = check_ai_tool(tool)
            if check.ok:
                ctx.log.info("%s", check.message)
                continue
            installer_command = ai_tool_installer_command(tool)
            log_ai_remote_installer_policy(ctx, tool)
            ctx.log.info("Installing %s.", tool.display_name)
            if dry_run:
                dry_run_command(ctx, list(installer_command))
            else:
                run_command(ctx, list(installer_command))
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1

    ctx.log.info("Base 'ai' prerequisite setup is complete.")
    return 0


def ai_remote_installer_urls() -> tuple[str, ...]:
    return AI_REMOTE_INSTALLER_ALLOWLIST


def validate_ai_remote_installer(tool: AITool) -> None:
    if tool.installer_url not in AI_REMOTE_INSTALLER_ALLOWLIST:
        raise ArtifactError(
            "Remote installer URL is not allowlisted for Base 'ai' profile: "
            f"{tool.installer_url}"
        )


def ai_tool_installer_command(tool: AITool) -> tuple[str, ...]:
    validate_ai_remote_installer(tool)
    return ("sh", "-c", f"curl -fsSL {tool.installer_url} | {tool.installer_shell}")


def log_ai_remote_installer_policy(ctx: base_cli.Context, tool: AITool) -> None:
    ctx.log.info(
        "Remote installer policy: %s uses allowlisted installer %s; execution requires explicit --profile ai.",
        tool.display_name,
        tool.installer_url,
    )


def ai_tool_checks() -> tuple[DevCheck, ...]:
    return tuple(check_ai_tool(tool) for tool in AI_TOOLS)


def check_ai_tool(tool: AITool) -> DevCheck:
    executable_path = shutil.which(tool.name)
    if executable_path is None:
        return DevCheck(
            name=tool.name,
            ok=False,
            message=f"{tool.display_name} '{tool.name}' was not found.",
            fix=_profile_setup_fix("ai"),
            finding_id="BASE-D107",
        )

    command = [executable_path, *tool.version_args]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = summarize_command_output(completed.stderr) or summarize_command_output(completed.stdout)
        message = f"{tool.display_name} version check failed with exit {completed.returncode}."
        if detail:
            message = f"{message} {detail}"
        return DevCheck(
            name=tool.name,
            ok=False,
            message=message,
            fix=_profile_setup_fix("ai"),
            finding_id="BASE-D107",
        )

    version = (
        summarize_command_output(completed.stdout)
        or summarize_command_output(completed.stderr)
        or "version unknown"
    )
    return DevCheck(
        name=tool.name,
        ok=True,
        message=f"{tool.display_name} is already installed at '{executable_path}' ({version}).",
        fix="",
        finding_id="BASE-D107",
    )


def summarize_command_output(output: str | None) -> str:
    return " ".join((output or "").split())


def _profile_setup_fix(profile: str) -> str:
    return f"basectl setup --profile {profile}"
