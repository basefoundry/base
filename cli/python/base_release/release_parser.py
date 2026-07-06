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
    dry_run: bool = False
    yes: bool = False


@dataclass
class ReleaseOptionState:
    version: str | None = None
    manifest_path: Path | None = None
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


def print_usage(file: TextIO = sys.stdout) -> None:
    command = base_cli.delegated_display_command("base_release")
    print(
        f"""Usage:
  {command} check --version <version> [--manifest <path>]
  {command} plan --version <version> [--manifest <path>]
  {command} notes --version <version> [--manifest <path>]
  {command} publish --version <version> [--manifest <path>] [--dry-run] [--yes]

Purpose:
  Inspect release readiness and guarded GitHub publishing for a Base-managed
  project. Homebrew tap changes remain a manual handoff.""",
        file=file,
    )
