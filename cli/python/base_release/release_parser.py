from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import base_cli


class ReleaseUsageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseArguments:
    command: str
    version: str
    manifest_path: Path | None
    output_format: str = "text"
    dry_run: bool = False
    yes: bool = False


@dataclass
class ReleaseOptionState:
    version: str | None = None
    manifest_path: Path | None = None
    output_format: str = "text"
    dry_run: bool = False
    yes: bool = False


def parse_release_args(arguments: tuple[str, ...]) -> ReleaseArguments:
    if not arguments or arguments[0] in ("-h", "--help", "help"):
        print_usage()
        raise SystemExit(0)

    command = arguments[0]
    if command not in ("check", "plan", "notes", "publish"):
        raise ReleaseUsageError(f"Unknown release command '{command}'.")

    state = ReleaseOptionState()
    remaining = list(arguments[1:])
    index = 0
    while index < len(remaining):
        index = parse_release_option(command, remaining, index, state)

    if state.version is None:
        raise ReleaseUsageError(f"The 'release {command}' command requires --version.")
    return ReleaseArguments(
        command=command,
        version=state.version,
        manifest_path=state.manifest_path,
        output_format=state.output_format,
        dry_run=state.dry_run,
        yes=state.yes,
    )


def parse_release_option(
    command: str,
    arguments: list[str],
    index: int,
    state: ReleaseOptionState,
) -> int:
    arg = arguments[index]
    if arg in ("-h", "--help"):
        print_usage()
        raise SystemExit(0)
    if arg == "--version":
        state.version = read_release_option_value(arguments, index, "--version")
        return index + 2
    if arg == "--manifest":
        state.manifest_path = Path(read_release_option_value(arguments, index, "--manifest")).expanduser()
        return index + 2
    if arg == "--format":
        require_check_option(command, "--format")
        state.output_format = read_release_option_value(arguments, index, "--format")
        if state.output_format not in ("text", "json"):
            raise ReleaseUsageError(
                f"Unsupported release check format '{state.output_format}'. Expected text or json."
            )
        return index + 2
    if arg == "--dry-run":
        require_publish_option(command, "--dry-run")
        state.dry_run = True
        return index + 1
    if arg == "--yes":
        require_publish_option(command, "--yes")
        state.yes = True
        return index + 1
    raise ReleaseUsageError(f"Unknown release {command} option '{arg}'.")


def read_release_option_value(arguments: list[str], index: int, option_name: str) -> str:
    value_index = index + 1
    if value_index >= len(arguments) or not arguments[value_index]:
        raise ReleaseUsageError(f"Option '{option_name}' requires an argument.")
    return arguments[value_index]


def require_publish_option(command: str, option_name: str) -> None:
    if command != "publish":
        raise ReleaseUsageError(f"Option '{option_name}' is only supported by release publish.")


def require_check_option(command: str, option_name: str) -> None:
    if command != "check":
        raise ReleaseUsageError(f"Option '{option_name}' is only supported by release check.")


def selected_release_check_format(arguments: tuple[str, ...]) -> str:
    if not arguments or arguments[0] != "check":
        return "text"
    selected = "text"
    for index, argument in enumerate(arguments):
        if argument == "--format" and index + 1 < len(arguments):
            candidate = arguments[index + 1]
            if candidate in ("text", "json"):
                selected = candidate
    return selected


def print_usage(file: TextIO = sys.stdout) -> None:
    command = base_cli.delegated_display_command("base_release")
    print(
        f"""Usage:
  {command} check --version <version> [--manifest <path>] [--format <text|json>]
  {command} plan --version <version> [--manifest <path>]
  {command} notes --version <version> [--manifest <path>]
  {command} publish --version <version> [--manifest <path>] [--dry-run] [--yes]

Purpose:
  Inspect release readiness and guarded GitHub publishing for a Base-managed
  project. Homebrew tap changes remain a manual handoff.""",
        file=file,
    )
