from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import base_cli

from .errors import ArtifactError


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_check(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    # Keep stdout live for installer progress; capture stderr for persistent failure logs.
    completed = subprocess.run(command, cwd=cwd, stderr=subprocess.PIPE, text=True, check=False)
    if completed.returncode:
        stderr = (completed.stderr or "").strip()
        message = f"Command failed with exit {completed.returncode}: {format_command(command)}"
        if stderr:
            message = f"{message}\n{stderr}"
        raise ArtifactError(message)
    if cwd is not None:
        ctx.log.debug("Command succeeded in '%s': %s", cwd, format_command(command))
    else:
        ctx.log.debug("Command succeeded: %s", format_command(command))


def dry_run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    if cwd is not None:
        ctx.log.info("[DRY-RUN] Would run in '%s': %s", cwd, format_command(command))
        return
    ctx.log.info("[DRY-RUN] Would run: %s", format_command(command))


def format_command(command: list[str]) -> str:
    return shlex.join(command)
