from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

from base_setup import process
from base_cli.redaction import redact_text_value


class ProjectUsageError(RuntimeError):
    pass


class ProjectCommandError(RuntimeError):
    pass


PROJECT_COMMAND_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class ProjectCommandResult:
    returncode: int
    stdout: str
    stderr: str


def github_repo_spec(url: str, *, allow_path: bool = False) -> str | None:
    normalized_url = url.strip()
    parsed = urlparse(normalized_url)
    if parsed.scheme and parsed.hostname == "github.com":
        return github_repo_spec_from_path(parsed.path)

    git_ssh_prefix = "git@github.com:"
    if normalized_url.startswith(git_ssh_prefix):
        return github_repo_spec_from_path(normalized_url[len(git_ssh_prefix) :])

    if allow_path and "/" in normalized_url and not parsed.scheme:
        return github_repo_spec_from_path(normalized_url)
    return None


def github_repo_spec_from_path(path: str) -> str | None:
    normalized = path.strip().lstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    parts = normalized.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return f"{parts[0]}/{parts[1]}"


def format_project_command(command: list[str]) -> str:
    return shlex.join(redact_text_value(arg) for arg in command)


def run_project_command(
    command: list[str],
    *,
    error_context: str,
    timeout_seconds: int = PROJECT_COMMAND_TIMEOUT_SECONDS,
) -> ProjectCommandResult:
    try:
        result = process.run_capture(
            command,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        timeout = exc.timeout if exc.timeout is not None else timeout_seconds
        raise ProjectCommandError(
            f"Timed out running {error_context} after {timeout} seconds. "
            f"Command: {format_project_command(command)}"
        ) from exc
    except OSError as exc:
        raise ProjectCommandError(
            f"Could not run {error_context}: {exc}. Command: {format_project_command(command)}"
        ) from exc
    return ProjectCommandResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr or "",
    )


def write_project_command_output(result: ProjectCommandResult) -> None:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
