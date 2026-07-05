from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

import base_cli
from base_projects.command_helpers import ProjectUsageError

from .project_model import ProjectArguments

HELP_OPTIONS = ("-h", "--help", "help")
PROJECT_VALUE_OPTIONS = (
    "--project",
    "--owner",
    "--repo",
    "--schema",
    "--config",
    "--copy-fields-from",
    "--initiative-option",
)
ISSUE_FIELD_OPTIONS = ("--status", "--priority", "--area", "--initiative", "--size")
OPTION_NOT_CONSUMED = 0
SPACED_OPTION_TOKEN_COUNT = 2


@dataclass
class OptionState:
    project_title: str | None = None
    owner: str | None = None
    repo: str | None = None
    schema: str = "base-project"
    config_path: str | None = None
    copy_fields_from_project: str | None = None
    initiative_options: list[str] | None = None
    replace_project: bool = False
    dry_run: bool = False
    field_values: dict[str, str] | None = None


def print_usage(file=sys.stdout) -> None:
    command = base_cli.delegated_display_command("base_github_projects")
    print(
        "\n".join(
            (
                "Usage:",
                f"  {command} project doctor --project <title> "
                "[--owner <login>] [--schema base-project]",
                f"  {command} project configure --project <title> "
                "[--owner <login>] [--repo <owner/name>] [--schema base-project] [--config <path>] "
                "[--copy-fields-from <title>] [--replace-project] [--initiative-option <name>] [--dry-run]",
                f"  {command} project issue set-fields <number> "
                "--repo <owner/name> --project <title> [--config <path>] [field options...]",
                f"  {command} project issue defaults --config <path>",
            )
        ),
        file=file,
    )


def parse_args(
    arguments: tuple[str, ...],
    *,
    infer_owner_from_git: Callable[[], str | None] | None = None,
    infer_repo_from_git: Callable[[], str | None] | None = None,
) -> ProjectArguments:
    infer_owner = infer_owner_from_git or no_inferred_value
    infer_repo = infer_repo_from_git or no_inferred_value
    if not arguments or arguments[0] in HELP_OPTIONS:
        print_usage()
        raise SystemExit(0)
    if arguments[0] != "project":
        raise ProjectUsageError(f"Unknown area '{arguments[0]}'.")
    if len(arguments) < 2:
        raise ProjectUsageError("The 'project' area requires a command.")

    command = arguments[1]
    remaining = list(arguments[2:])
    if command == "doctor":
        state = parse_project_options(
            remaining,
            allow_fields=False,
            allow_issue=False,
            infer_owner_from_git=infer_owner,
        )
        require_project_title(state)
        return state_to_args("doctor", state)
    if command == "configure":
        state = parse_project_options(
            remaining,
            allow_fields=False,
            allow_issue=False,
            infer_owner_from_git=infer_owner,
        )
        require_project_title(state)
        return state_to_args("configure", state)
    if command == "issue":
        if remaining and remaining[0] == "defaults":
            state = parse_project_options(
                remaining[1:],
                allow_fields=False,
                allow_issue=False,
                infer_owner_from_git=infer_owner,
            )
            if not state.config_path:
                raise ProjectUsageError("The 'project issue defaults' command requires --config.")
            return state_to_args("issue-defaults", state)
        if len(remaining) < 2 or remaining[0] != "set-fields":
            raise ProjectUsageError("Expected 'project issue set-fields <number>'.")
        try:
            issue_number = int(remaining[1])
        except ValueError as exc:
            raise ProjectUsageError(f"Invalid issue number '{remaining[1]}'.") from exc
        state = parse_project_options(
            remaining[2:],
            allow_fields=True,
            allow_issue=True,
            infer_owner_from_git=infer_owner,
        )
        require_project_title(state)
        if not state.repo:
            state.repo = infer_repo()
        if not state.repo:
            raise ProjectUsageError("The 'project issue set-fields' command requires --repo.")
        return state_to_args("issue-set-fields", state, issue_number=issue_number)
    raise ProjectUsageError(f"Unknown project command '{command}'.")


def parse_project_options(
    remaining: list[str],
    *,
    allow_fields: bool,
    allow_issue: bool,
    infer_owner_from_git: Callable[[], str | None] | None = None,
) -> OptionState:
    state = OptionState(initiative_options=[], field_values={})
    index = 0
    while index < len(remaining):
        arg = remaining[index]
        if arg in HELP_OPTIONS:
            print_usage()
            raise SystemExit(0)
        if arg == "--dry-run":
            state.dry_run = True
            index += 1
            continue
        if arg == "--replace-project":
            state.replace_project = True
            index += 1
            continue
        consumed = apply_spaced_option(state, remaining, index, allow_fields=allow_fields)
        if consumed:
            index += consumed
            continue
        if allow_issue:
            raise ProjectUsageError(f"Unknown issue field option '{arg}'.")
        raise ProjectUsageError(f"Unknown option '{arg}'.")
    if state.schema != "base-project":
        raise ProjectUsageError("Only project schema 'base-project' is supported.")
    if not state.owner and state.repo:
        state.owner = state.repo.split("/", 1)[0]
    if not state.owner:
        infer_owner = infer_owner_from_git or no_inferred_value
        state.owner = infer_owner()
    return state


def apply_spaced_option(state: OptionState, remaining: list[str], index: int, *, allow_fields: bool) -> int:
    """Apply a spaced option and return the number of consumed tokens."""
    option = remaining[index]
    if option in PROJECT_VALUE_OPTIONS:
        apply_project_option(state, option, option_value(remaining, index))
        return SPACED_OPTION_TOKEN_COUNT
    if allow_fields and option in ISSUE_FIELD_OPTIONS:
        state.field_values[option[2:]] = option_value(remaining, index)
        return SPACED_OPTION_TOKEN_COUNT
    return OPTION_NOT_CONSUMED


def option_value(remaining: list[str], index: int) -> str:
    option = remaining[index]
    if index + 1 >= len(remaining):
        raise ProjectUsageError(f"Option '{option}' requires an argument.")
    return remaining[index + 1]


def apply_project_option(state: OptionState, option: str, value: str) -> None:
    if option == "--project":
        state.project_title = value
    elif option == "--owner":
        state.owner = value
    elif option == "--repo":
        state.repo = value
    elif option == "--schema":
        state.schema = value
    elif option == "--config":
        state.config_path = value
    elif option == "--copy-fields-from":
        state.copy_fields_from_project = value
    elif option == "--initiative-option":
        state.initiative_options.append(value)


def require_project_title(state: OptionState) -> None:
    if not state.project_title:
        raise ProjectUsageError("The project command requires --project.")


def state_to_args(command: str, state: OptionState, issue_number: int | None = None) -> ProjectArguments:
    return ProjectArguments(
        area="project",
        command=command,
        project_title=state.project_title,
        owner=state.owner,
        repo=state.repo,
        schema=state.schema,
        config_path=state.config_path,
        copy_fields_from_project=state.copy_fields_from_project,
        initiative_options=tuple(state.initiative_options or ()),
        replace_project=state.replace_project,
        dry_run=state.dry_run,
        issue_number=issue_number,
        field_values=dict(state.field_values or {}),
    )


def no_inferred_value() -> str | None:
    return None
