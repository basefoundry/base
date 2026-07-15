from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import base_cli
from base_projects.command_helpers import ProjectUsageError


@dataclass(frozen=True)
class WorkspaceCommandOptions:
    workspace: str | None
    output_format: str
    workspace_manifest: str | None = None
    workspace_manifest_source: str | None = None
    workspace_config_path: str | None = None
    workspace_owner: str | None = None
    include_optional: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class ProjectCommandActions:
    list_projects: Callable[[base_cli.Context, str | None, str], int]
    workspace_status: Callable[[base_cli.Context, str | None, str, str | None], int]
    workspace_check: Callable[[base_cli.Context, str | None, str, str | None], int]
    workspace_doctor: Callable[[base_cli.Context, str | None, str, str | None], int]
    workspace_onboarding: Callable[[base_cli.Context, str | None, str, str | None], int]
    workspace_clone: Callable[[base_cli.Context, WorkspaceCommandOptions], int]
    workspace_pull: Callable[[base_cli.Context, WorkspaceCommandOptions], int]
    workspace_init: Callable[[base_cli.Context, str, WorkspaceCommandOptions], int]
    workspace_configure: Callable[[base_cli.Context, WorkspaceCommandOptions], int]
    current_project: Callable[[base_cli.Context, str], int]
    manifest_project: Callable[[base_cli.Context, str | None, str], int]
    resolve_project: Callable[[base_cli.Context, str | None, str | None, str], int]
    test_command_project: Callable[[base_cli.Context, str | None, str | None, str], int]
    demo_script_project: Callable[[base_cli.Context, str | None, str | None, str], int]
    activation_sources_project: Callable[[base_cli.Context, str | None, str | None, str], int]
    run_command_project: Callable[[base_cli.Context, str | None, str | None, str | None, str], int]
    list_run_commands: Callable[[base_cli.Context, str | None, str | None, str], int]
    build_targets: Callable[[base_cli.Context, tuple[str, ...], str | None, str], int]
    build_target_list: Callable[[base_cli.Context, tuple[str, ...], str | None, str], int]


ProjectCommandHandler = Callable[
    [base_cli.Context, tuple[str, ...], WorkspaceCommandOptions, ProjectCommandActions],
    int,
]


def dispatch_projects_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    command = arguments[0] if arguments else "list"
    command_arguments = arguments[1:] if arguments else ()
    handler = PROJECT_COMMAND_HANDLERS.get(command)
    if handler is not None:
        return handler(ctx, command_arguments, options, actions)

    ctx.log.error(
        "Unknown projects command '%s'. Supported commands: %s.",
        command,
        ", ".join(SUPPORTED_PROJECT_COMMANDS),
    )
    return base_cli.ExitCode.USAGE_ERROR


def require_argument_count(command: str, arguments: tuple[str, ...], minimum: int, maximum: int) -> None:
    if len(arguments) < minimum:
        raise ProjectUsageError(f"Project command '{command}' requires at least {minimum} argument(s).")
    if len(arguments) > maximum:
        raise ProjectUsageError(f"Project command '{command}' accepts at most {maximum} argument(s).")


def optional_project_argument(command: str, arguments: tuple[str, ...]) -> str | None:
    require_argument_count(command, arguments, 0, 1)
    return arguments[0] if arguments else None


def _handle_list(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("list", arguments, 0, 0)
    return actions.list_projects(ctx, options.workspace, options.output_format)


def _handle_status(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("status", arguments, 0, 0)
    return actions.workspace_status(ctx, options.workspace, options.output_format, options.workspace_manifest)


def _handle_check(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("check", arguments, 0, 0)
    return actions.workspace_check(ctx, options.workspace, options.output_format, options.workspace_manifest)


def _handle_doctor(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("doctor", arguments, 0, 0)
    return actions.workspace_doctor(ctx, options.workspace, options.output_format, options.workspace_manifest)


def _handle_onboarding(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("onboarding", arguments, 0, 0)
    return actions.workspace_onboarding(ctx, options.workspace, options.output_format, options.workspace_manifest)


def _handle_clone(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("clone", arguments, 0, 0)
    return actions.workspace_clone(ctx, options)


def _handle_pull(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("pull", arguments, 0, 0)
    return actions.workspace_pull(ctx, options)


def _handle_init(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("init", arguments, 1, 1)
    return actions.workspace_init(ctx, arguments[0], options)


def _handle_configure(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("configure", arguments, 0, 0)
    return actions.workspace_configure(ctx, options)


def _handle_current(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("current", arguments, 0, 0)
    return actions.current_project(ctx, options.output_format)


def _handle_manifest(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("manifest", arguments, 0, 1)
    return actions.manifest_project(ctx, arguments[0] if arguments else None, options.output_format)


def _handle_resolve(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("resolve", arguments, 1, 1)
    return actions.resolve_project(ctx, arguments[0], options.workspace, options.output_format)


def _handle_test_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    project = optional_project_argument("test-command", arguments)
    return actions.test_command_project(ctx, project, options.workspace, options.output_format)


def _handle_demo_script(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    project = optional_project_argument("demo-script", arguments)
    return actions.demo_script_project(ctx, project, options.workspace, options.output_format)


def _handle_activation_sources(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("activation-sources", arguments, 1, 1)
    return actions.activation_sources_project(ctx, arguments[0], options.workspace, options.output_format)


def _handle_run_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    require_argument_count("run-command", arguments, 2, 2)
    return actions.run_command_project(ctx, arguments[0], arguments[1], options.workspace, options.output_format)


def _handle_run_commands(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    project = optional_project_argument("run-commands", arguments)
    return actions.list_run_commands(ctx, project, options.workspace, options.output_format)


def _handle_build_targets(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    return actions.build_targets(ctx, arguments, options.workspace, options.output_format)


def _handle_build_target_list(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
    actions: ProjectCommandActions,
) -> int:
    return actions.build_target_list(ctx, arguments, options.workspace, options.output_format)


SUPPORTED_PROJECT_COMMANDS = (
    "list",
    "current",
    "manifest",
    "resolve",
    "status",
    "check",
    "doctor",
    "onboarding",
    "clone",
    "configure",
    "init",
    "test-command",
    "demo-script",
    "activation-sources",
    "run-command",
    "run-commands",
    "build-targets",
    "build-target-list",
    "pull",
)


PROJECT_COMMAND_HANDLERS: dict[str, ProjectCommandHandler] = {
    "list": _handle_list,
    "status": _handle_status,
    "check": _handle_check,
    "doctor": _handle_doctor,
    "onboarding": _handle_onboarding,
    "clone": _handle_clone,
    "pull": _handle_pull,
    "init": _handle_init,
    "configure": _handle_configure,
    "current": _handle_current,
    "manifest": _handle_manifest,
    "resolve": _handle_resolve,
    "test-command": _handle_test_command,
    "demo-script": _handle_demo_script,
    "activation-sources": _handle_activation_sources,
    "run-command": _handle_run_command,
    "run-commands": _handle_run_commands,
    "build-targets": _handle_build_targets,
    "build-target-list": _handle_build_target_list,
}
