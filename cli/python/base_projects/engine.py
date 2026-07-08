from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_projects.build_targets import build_targets_project_from_args
from base_projects.build_targets import list_build_targets_from_args
from base_projects.command_helpers import ProjectUsageError
from base_projects.project_discovery import Project
from base_projects.project_discovery import discover_projects_cached
from base_projects.project_discovery import find_project_in_projects
from base_projects.project_discovery import current_project
from base_projects.project_discovery import read_project
from base_projects.project_discovery import resolve_active_project
from base_projects.project_commands import CommandConfig  # pylint: disable=unused-import
from base_projects.project_commands import ProjectCommandError
from base_projects.project_commands import TestConfig  # pylint: disable=unused-import
from base_projects.project_commands import activation_source_paths
from base_projects.project_commands import command_output as _command_output
from base_projects.project_commands import demo_output as _demo_output
from base_projects.project_commands import named_command_output as _named_command_output
from base_projects.project_commands import project_command
from base_projects.project_commands import project_commands
from base_projects.project_commands import project_output as _project_output
from base_projects.project_commands import resolve_activation_source_path  # pylint: disable=unused-import
from base_projects.project_commands import test_command
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_clone_command import clone_workspace_repo  # pylint: disable=unused-import
from base_projects.workspace_clone_command import print_optional_clone_skip  # pylint: disable=unused-import
from base_projects.workspace_clone_command import require_workspace_clone_manifest  # pylint: disable=unused-import
from base_projects.workspace_clone_command import should_skip_optional_clone  # pylint: disable=unused-import
from base_projects.workspace_clone_command import workspace_clone_command
from base_projects.workspace_clone_command import workspace_clone_repo_spec  # pylint: disable=unused-import
from base_projects.workspace_configure import workspace_configure_from_options
from base_projects.workspace_context import effective_workspace_manifest
from base_projects.workspace_context import resolve_workspace_root
from base_projects.workspace_init import workspace_init_command
from base_projects.workspace_pull_command import workspace_pull_command
from base_projects.workspace_reports import dumps_json
from base_projects.workspace_reports import print_workspace_check
from base_projects.workspace_reports import print_workspace_doctor
from base_projects.workspace_reports import print_workspace_status
from base_projects.workspace_reports import resolve_workspace_manifest
from base_projects.workspace_reports import workspace_check_to_json
from base_projects.workspace_reports import workspace_doctor_to_json
from base_projects.workspace_reports import workspace_error_count
from base_projects.workspace_reports import workspace_project_check_results
from base_projects.workspace_reports import workspace_project_statuses
from base_projects.workspace_reports import workspace_status_to_json
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.demo import resolve_demo_script_path
from base_setup.errors import ArtifactError
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError


app = base_cli.App(name="base_projects")


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


ProjectCommandHandler = Callable[[base_cli.Context, tuple[str, ...], WorkspaceCommandOptions], int]


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("arguments", nargs=-1)
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option("--format", "output_format", default="text", help="Output format: text or json.")
@base_cli.option("--manifest", "workspace_manifest", help="Local workspace manifest to read.")
@base_cli.option("--source", "workspace_manifest_source", help="Canonical workspace manifest source URL or path.")
@base_cli.option("--path", "workspace_config_path", help="Workspace configuration repository checkout path.")
@base_cli.option("--owner", "workspace_owner", help="GitHub owner for short workspace repository names.")
@base_cli.option(
    "--include-optional",
    is_flag=True,
    help="Include optional workspace manifest repositories when cloning.",
)
@base_cli.option("--dry-run", is_flag=True, dry_run=True, help="Show planned clone or pull work without writing.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    output_format: str,
    workspace_manifest: str | None,
    workspace_manifest_source: str | None,
    workspace_config_path: str | None,
    workspace_owner: str | None,
    include_optional: bool,
    dry_run: bool,
) -> int:
    try:
        return dispatch_projects_command(
            ctx,
            arguments,
            WorkspaceCommandOptions(
                workspace=workspace,
                output_format=output_format,
                workspace_manifest=workspace_manifest,
                workspace_manifest_source=workspace_manifest_source,
                workspace_config_path=workspace_config_path,
                workspace_owner=workspace_owner,
                include_optional=include_optional,
                dry_run=dry_run,
            ),
        )
    except ProjectUsageError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR


def dispatch_projects_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    command = arguments[0] if arguments else "list"
    command_arguments = arguments[1:] if arguments else ()
    handler = PROJECT_COMMAND_HANDLERS.get(command)
    if handler is not None:
        return handler(ctx, command_arguments, options)

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


def list_projects_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    output_format: str,
) -> int:
    require_argument_count("list", arguments, 0, 0)
    return list_projects_command(ctx, workspace, output_format)


def workspace_status_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    require_argument_count("status", arguments, 0, 0)
    return workspace_status_command(ctx, options.workspace, options.output_format, options.workspace_manifest)


def current_project_from_args(ctx: base_cli.Context, arguments: tuple[str, ...]) -> int:
    require_argument_count("current", arguments, 0, 0)
    return current_project_command(ctx)


def manifest_project_from_args(ctx: base_cli.Context, arguments: tuple[str, ...]) -> int:
    require_argument_count("manifest", arguments, 0, 1)
    return manifest_project_command(ctx, arguments[0] if arguments else None)


def resolve_project_from_args(ctx: base_cli.Context, arguments: tuple[str, ...], workspace: str | None) -> int:
    require_argument_count("resolve", arguments, 1, 1)
    return resolve_project_command(ctx, arguments[0], workspace)


def test_command_project_from_args(ctx: base_cli.Context, arguments: tuple[str, ...], workspace: str | None) -> int:
    project = optional_project_argument("test-command", arguments)
    return test_command_project_command(ctx, project, workspace)


def demo_script_project_from_args(ctx: base_cli.Context, arguments: tuple[str, ...], workspace: str | None) -> int:
    project = optional_project_argument("demo-script", arguments)
    return demo_script_project_command(ctx, project, workspace)


def activation_sources_project_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
) -> int:
    require_argument_count("activation-sources", arguments, 1, 1)
    return activation_sources_project_command(ctx, arguments[0], workspace)


def run_command_project_from_args(ctx: base_cli.Context, arguments: tuple[str, ...], workspace: str | None) -> int:
    require_argument_count("run-command", arguments, 2, 2)
    return run_command_project_command(ctx, arguments[0], arguments[1], workspace)


def list_run_commands_from_args(ctx: base_cli.Context, arguments: tuple[str, ...], workspace: str | None) -> int:
    project = optional_project_argument("run-commands", arguments)
    return list_run_commands_command(ctx, project, workspace)


def workspace_init_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    require_argument_count("init", arguments, 1, 1)
    return workspace_init_command(
        ctx,
        arguments[0],
        options,
        workspace_clone_command=workspace_clone_command,
    )


def _handle_list(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return list_projects_from_args(ctx, arguments, options.workspace, options.output_format)


def _handle_status(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return workspace_status_from_args(ctx, arguments, options)


def _handle_check(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    require_argument_count("check", arguments, 0, 0)
    return workspace_check_command(ctx, options.workspace, options.output_format, options.workspace_manifest)


def _handle_doctor(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    require_argument_count("doctor", arguments, 0, 0)
    return workspace_doctor_command(ctx, options.workspace, options.output_format, options.workspace_manifest)


def _handle_clone(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    require_argument_count("clone", arguments, 0, 0)
    return workspace_clone_command(ctx, options)


def _handle_pull(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    require_argument_count("pull", arguments, 0, 0)
    return workspace_pull_command(ctx, options)


def _handle_init(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return workspace_init_from_args(ctx, arguments, options)


def _handle_configure(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    require_argument_count("configure", arguments, 0, 0)
    return workspace_configure_from_options(ctx, options)


def _handle_current(ctx: base_cli.Context, arguments: tuple[str, ...], _options: WorkspaceCommandOptions) -> int:
    return current_project_from_args(ctx, arguments)


def _handle_manifest(ctx: base_cli.Context, arguments: tuple[str, ...], _options: WorkspaceCommandOptions) -> int:
    return manifest_project_from_args(ctx, arguments)


def _handle_resolve(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return resolve_project_from_args(ctx, arguments, options.workspace)


def _handle_test_command(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return test_command_project_from_args(ctx, arguments, options.workspace)


def _handle_demo_script(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return demo_script_project_from_args(ctx, arguments, options.workspace)


def _handle_activation_sources(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    return activation_sources_project_from_args(ctx, arguments, options.workspace)


def _handle_run_command(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return run_command_project_from_args(ctx, arguments, options.workspace)


def _handle_run_commands(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return list_run_commands_from_args(ctx, arguments, options.workspace)


def _handle_build_targets(ctx: base_cli.Context, arguments: tuple[str, ...], options: WorkspaceCommandOptions) -> int:
    return build_targets_project_from_args(ctx, arguments, options.workspace, resolve_named_project)


def _handle_build_target_list(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    return list_build_targets_from_args(ctx, arguments, options.workspace, resolve_named_project)


SUPPORTED_PROJECT_COMMANDS = (
    "list",
    "current",
    "manifest",
    "resolve",
    "status",
    "check",
    "doctor",
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


def list_projects_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        projects = discover_projects_cached(ctx, workspace_root)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "json":
        print(
            json.dumps(
                [{"name": project.name, "path": str(project.root)} for project in projects],
                separators=(",", ":"),
            )
        )
        return base_cli.ExitCode.SUCCESS

    for project in projects:
        print(f"{project.name}\t{project.root}")
    return base_cli.ExitCode.SUCCESS


def workspace_status_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        effective_manifest = effective_workspace_manifest(ctx, workspace_manifest)
        log_workspace_status_discovery(ctx, workspace, workspace_root, workspace_manifest, effective_manifest)
        manifest = resolve_workspace_manifest(effective_manifest)
        statuses = workspace_project_statuses(workspace_root, manifest)
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "json":
        print(dumps_json(workspace_status_to_json(workspace_root, statuses, manifest)))
    else:
        print_workspace_status(workspace_root, statuses, manifest)

    if any(project.status == "error" for project in statuses):
        return base_cli.ExitCode.FAILURE
    return base_cli.ExitCode.SUCCESS


def workspace_check_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
        results = workspace_project_check_results(ctx, workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "json":
        print(dumps_json(workspace_check_to_json(workspace_root, results, manifest)))
    else:
        print_workspace_check(workspace_root, results, manifest)

    if any(result.status == "error" for result in results):
        return base_cli.ExitCode.FAILURE
    return base_cli.ExitCode.SUCCESS


def workspace_doctor_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
        results = workspace_project_check_results(ctx, workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "json":
        print(dumps_json(workspace_doctor_to_json(workspace_root, results, manifest)))
    else:
        print_workspace_doctor(workspace_root, results, manifest)

    return min(workspace_error_count(results), 125)


def log_workspace_status_discovery(
    ctx: base_cli.Context,
    workspace: str | None,
    workspace_root: Path,
    workspace_manifest: str | None,
    effective_manifest: str | None,
) -> None:
    ctx.log.debug(
        "Workspace status root: %s (source: %s).",
        workspace_root,
        workspace_root_source(ctx, workspace),
    )
    if effective_manifest is None:
        ctx.log.debug(
            "Workspace status manifest: none supplied or configured; scanning immediate child directories "
            "under %s for base_manifest.yaml.",
            workspace_root,
        )
        return
    ctx.log.debug(
        "Workspace status manifest: %s (source: %s).",
        Path(effective_manifest).expanduser().resolve(strict=False),
        workspace_manifest_source_label(ctx, workspace_manifest),
    )


def workspace_root_source(ctx: base_cli.Context, workspace: str | None) -> str:
    if workspace:
        return "--workspace"
    if ctx.workspace_root is not None:
        return "workspace.root"
    return "BASE_HOME parent"


def workspace_manifest_source_label(ctx: base_cli.Context, workspace_manifest: str | None) -> str:
    if workspace_manifest is not None:
        return "--manifest"
    if ctx.user_config.workspace.manifest is not None:
        return "workspace.manifest"
    return "none"


def resolve_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print(_project_output(project.name, project.root, project.manifest_path, manifest))
    return base_cli.ExitCode.SUCCESS


def test_command_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    try:
        if project_name:
            project = resolve_named_project(ctx, project_name, workspace)
        else:
            project = current_project()
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if manifest.test is None:
        ctx.log.error(
            "Project '%s' does not declare test.command or test.mise in '%s'.",
            project.name,
            project.manifest_path,
        )
        return base_cli.ExitCode.FAILURE

    command_config = test_command(manifest.test)
    print(_command_output(project.name, project.root, project.manifest_path, command_config, manifest))
    return base_cli.ExitCode.SUCCESS


def demo_script_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    try:
        if project_name:
            project = resolve_named_project(ctx, project_name, workspace)
        else:
            project = current_project()
        manifest = read_manifest(project.manifest_path)
        if manifest.demo is None:
            ctx.log.error(
                "No demo declared for project '%s'. Add demo.script to '%s'.",
                project.name,
                project.manifest_path,
            )
            return base_cli.ExitCode.FAILURE
        demo_script = resolve_demo_script_path(manifest)
    except (ProjectDiscoveryError, ManifestError, ArtifactError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print(_demo_output(project.name, project.root, project.manifest_path, demo_script, manifest))
    return base_cli.ExitCode.SUCCESS


def activation_sources_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
        sources = activation_source_paths(project, manifest.activate.source)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    for source in sources:
        print(source)
    return base_cli.ExitCode.SUCCESS


def run_command_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    command_name: str | None,
    workspace: str | None,
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR
    if not command_name:
        ctx.log.error("Command name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
        command_config = project_command(manifest, command_name)
    except (ProjectDiscoveryError, ManifestError, ProjectCommandError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print(_command_output(project.name, project.root, project.manifest_path, command_config, manifest))
    return base_cli.ExitCode.SUCCESS


def list_run_commands_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    try:
        if project_name:
            project = resolve_named_project(ctx, project_name, workspace)
        else:
            project = current_project()
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    commands = project_commands(manifest)
    if not commands:
        ctx.log.error("Project '%s' does not declare runnable commands in '%s'.", project.name, project.manifest_path)
        return base_cli.ExitCode.FAILURE

    for command_name, command_config in commands.items():
        print(_named_command_output(project.name, project.root, project.manifest_path, command_name, command_config))
    return base_cli.ExitCode.SUCCESS


def current_project_command(ctx: base_cli.Context) -> int:
    try:
        project = current_project()
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    return base_cli.ExitCode.SUCCESS


def manifest_project_command(ctx: base_cli.Context, manifest: str | None) -> int:
    if not manifest:
        ctx.log.error("Manifest path is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = read_project(Path(manifest).expanduser().resolve())
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    return base_cli.ExitCode.SUCCESS


def resolve_named_project(ctx: base_cli.Context, project_name: str, workspace: str | None) -> Project:
    if workspace is None and project_name == "base" and ctx.base_home is not None:
        return read_project(ctx.base_home / "base_manifest.yaml")

    if workspace is None:
        active_project = resolve_active_project(project_name)
        if active_project is not None:
            ctx.log.debug("Resolved active project '%s' from BASE_PROJECT_MANIFEST.", project_name)
            return active_project

    workspace_root = resolve_workspace_root(ctx, workspace)
    projects = discover_projects_cached(ctx, workspace_root)
    return find_project_in_projects(projects, workspace_root, project_name)
