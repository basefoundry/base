from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import base_cli
from base_cli.command_protocol import dumps_record
from base_cli.command_protocol import dumps_records
from base_projects.build_targets import build_targets_project_from_args
from base_projects.build_targets import list_build_targets_from_args
from base_projects.command_helpers import ProjectUsageError
from base_projects.project_discovery import Project
from base_projects.project_discovery import discover_projects_cached
from base_projects.project_discovery import current_project
from base_projects.project_discovery import read_project
from base_projects.project_discovery import resolve_active_project
from base_projects.project_commands import CommandConfig  # pylint: disable=unused-import
from base_projects.project_commands import ProjectCommandError
from base_projects.project_commands import TestConfig  # pylint: disable=unused-import
from base_projects.project_commands import activation_source_paths
from base_projects.project_commands import command_record
from base_projects.project_commands import command_output as _command_output
from base_projects.project_commands import demo_record
from base_projects.project_commands import demo_output as _demo_output
from base_projects.project_commands import named_command_record
from base_projects.project_commands import named_command_output as _named_command_output
from base_projects.project_commands import project_command
from base_projects.project_commands import project_commands
from base_projects.project_commands import project_record
from base_projects.project_commands import project_output as _project_output
from base_projects.project_commands import resolve_activation_source_path  # pylint: disable=unused-import
from base_projects.project_commands import test_command
from base_projects.project_dispatch import ProjectCommandActions
from base_projects.project_dispatch import WorkspaceCommandOptions
from base_projects.project_dispatch import dispatch_projects_command
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_agent_brief import workspace_agent_brief
from base_projects.workspace_clone_command import clone_workspace_repo  # pylint: disable=unused-import
from base_projects.workspace_clone_command import print_optional_clone_skip  # pylint: disable=unused-import
from base_projects.workspace_clone_command import require_workspace_clone_manifest  # pylint: disable=unused-import
from base_projects.workspace_clone_command import should_skip_optional_clone  # pylint: disable=unused-import
from base_projects.workspace_clone_command import workspace_clone_command
from base_projects.workspace_clone_command import workspace_clone_repo_spec  # pylint: disable=unused-import
from base_projects.workspace_configure import workspace_configure_from_options
from base_projects.workspace_context import effective_workspace_manifest
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_context import resolve_workspace_root
from base_projects.workspace_init import workspace_init_command
from base_projects.workspace_pull_command import workspace_pull_command
from base_projects.workspace_onboarding import workspace_onboarding_summary
from base_projects.workspace_report_json import workspace_check_to_json
from base_projects.workspace_report_json import workspace_doctor_to_json
from base_projects.workspace_report_json import workspace_agent_brief_to_json
from base_projects.workspace_report_json import workspace_onboarding_to_json
from base_projects.workspace_report_json import workspace_status_to_json
from base_projects.workspace_report_text import print_workspace_check
from base_projects.workspace_report_text import print_workspace_doctor
from base_projects.workspace_report_text import print_workspace_agent_brief
from base_projects.workspace_report_text import print_workspace_onboarding
from base_projects.workspace_report_text import print_workspace_status
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_projects.workspace_checks import workspace_error_count
from base_projects.workspace_checks import workspace_project_check_results
from base_projects.workspace_statuses import workspace_project_statuses
from base_setup.demo import resolve_demo_script_path
from base_setup.errors import ArtifactError
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError


app = base_cli.App(name="base_projects")


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("arguments", nargs=-1)
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option("--project", "project_name", help="Select a project explicitly.")
@base_cli.option(
    "--format",
    "output_format",
    default="text",
    help="Output format: text, csv, tsv, yaml, or json.",
)
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
    project_name: str | None,
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
                project_name=project_name,
                workspace_manifest=workspace_manifest,
                workspace_manifest_source=workspace_manifest_source,
                workspace_config_path=workspace_config_path,
                workspace_owner=workspace_owner,
                include_optional=include_optional,
                dry_run=dry_run,
            ),
            project_command_actions(),
        )
    except ProjectUsageError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR


def project_command_actions() -> ProjectCommandActions:
    return ProjectCommandActions(
        list_projects=list_projects_command,
        workspace_status=workspace_status_command,
        workspace_check=workspace_check_command,
        workspace_doctor=workspace_doctor_command,
        workspace_onboarding=workspace_onboarding_command,
        workspace_agent_brief=workspace_agent_brief_command,
        workspace_clone=workspace_clone_command,
        workspace_pull=workspace_pull_command,
        workspace_init=workspace_init_project_command,
        workspace_configure=workspace_configure_from_options,
        current_project=current_project_command,
        manifest_project=manifest_project_command,
        resolve_project=resolve_project_command,
        test_command_project=test_command_project_command,
        demo_script_project=demo_script_project_command,
        activation_sources_project=activation_sources_project_command,
        run_command_project=run_command_project_from_args,
        list_run_commands=list_run_commands_command,
        build_targets=build_targets_project_command,
        build_target_list=build_target_list_project_command,
    )


def workspace_init_project_command(
    ctx: base_cli.Context,
    workspace_source: str,
    options: WorkspaceCommandOptions,
) -> int:
    return workspace_init_command(
        ctx,
        workspace_source,
        options,
        workspace_clone_command=workspace_clone_command,
    )


def build_targets_project_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    explicit_project: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
    return build_targets_project_from_args(
        ctx,
        arguments,
        explicit_project,
        workspace,
        select_invocation_project,
        output_format,
    )


def build_target_list_project_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    explicit_project: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
    return list_build_targets_from_args(
        ctx,
        arguments,
        explicit_project,
        workspace,
        select_invocation_project,
        output_format,
    )


def list_projects_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format != "command-protocol":
        try:
            base_cli.resolve_output_format(output_format)
        except base_cli.OutputFormatError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        projects = discover_projects_cached(ctx, workspace_root)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "command-protocol":
        print(
            dumps_records(
                "project-list-entry",
                [
                    {
                        "project_name": project.name,
                        "project_root": str(project.root),
                    }
                    for project in projects
                ],
            )
        )
        return base_cli.ExitCode.SUCCESS

    try:
        base_cli.render_records(
            ({"name": project.name, "path": str(project.root)} for project in projects),
            requested_format=output_format,
            columns=(("PROJECT", "name"), ("PATH", "path")),
            footer=f"{len(projects)} project(s).",
        )
    except base_cli.OutputFormatError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def workspace_status_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if not validate_report_format(ctx, output_format):
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

    if not emit_workspace_report(
        ctx,
        workspace_status_to_json(workspace_root, statuses, manifest),
        output_format,
        records_key="projects",
        columns=(
            ("PROJECT", "name"),
            ("STATUS", "status"),
            ("PATH", "path"),
            ("VENV", "venv"),
            ("MANIFEST", "manifest"),
            ("LAST CHECK", "last_check"),
        ),
        text_renderer=lambda: print_workspace_status(workspace_root, statuses, manifest),
    ):
        return base_cli.ExitCode.USAGE_ERROR

    if any(project.status == "error" for project in statuses):
        return base_cli.ExitCode.FAILURE
    return base_cli.ExitCode.SUCCESS


def workspace_check_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if not validate_report_format(ctx, output_format):
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
        results = workspace_project_check_results(ctx, workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if not emit_workspace_report(
        ctx,
        workspace_check_to_json(workspace_root, results, manifest),
        output_format,
        records_key="projects",
        columns=(("PROJECT", "name"), ("STATUS", "status"), ("PATH", "path"), ("MANIFEST", "manifest")),
        text_renderer=lambda: print_workspace_check(workspace_root, results, manifest),
    ):
        return base_cli.ExitCode.USAGE_ERROR

    if any(result.status == "error" for result in results):
        return base_cli.ExitCode.FAILURE
    return base_cli.ExitCode.SUCCESS


def workspace_doctor_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if not validate_report_format(ctx, output_format):
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
        results = workspace_project_check_results(ctx, workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if not emit_workspace_report(
        ctx,
        workspace_doctor_to_json(workspace_root, results, manifest),
        output_format,
        records_key="projects",
        columns=(("PROJECT", "name"), ("STATUS", "status"), ("PATH", "path"), ("MANIFEST", "manifest")),
        text_renderer=lambda: print_workspace_doctor(workspace_root, results, manifest),
    ):
        return base_cli.ExitCode.USAGE_ERROR

    return min(workspace_error_count(results), 125)


def workspace_onboarding_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if not validate_report_format(ctx, output_format):
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
        if manifest is None:
            ctx.log.error("Workspace onboarding requires a workspace manifest. Use --manifest or workspace.manifest.")
            return base_cli.ExitCode.USAGE_ERROR
        summary = workspace_onboarding_summary(workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if not emit_workspace_report(
        ctx,
        workspace_onboarding_to_json(summary),
        output_format,
        records_key="repositories",
        columns=(
            ("REPOSITORY", "repository"),
            ("REQUIRED", "required"),
            ("STATUS", "status"),
            ("PATH", "path"),
            ("VENV", "venv"),
        ),
        text_renderer=lambda: print_workspace_onboarding(summary),
    ):
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def workspace_agent_brief_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if not validate_report_format(ctx, output_format):
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
        if manifest is None:
            ctx.log.error("Workspace agent brief requires a workspace manifest. Use --manifest or workspace.manifest.")
            return base_cli.ExitCode.USAGE_ERROR
        brief = workspace_agent_brief(workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if not emit_workspace_report(
        ctx,
        workspace_agent_brief_to_json(brief),
        output_format,
        records_key="repositories",
        columns=(
            ("REPOSITORY", "repository"),
            ("PROJECT", "project"),
            ("PATH", "path"),
            ("SCOPE", "scope"),
            ("HANDOFF", "handoff_status"),
            ("VENV", "venv"),
        ),
        text_renderer=lambda: print_workspace_agent_brief(brief),
    ):
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def validate_report_format(ctx: base_cli.Context, output_format: str) -> bool:
    try:
        base_cli.resolve_output_format(output_format)
    except base_cli.OutputFormatError as exc:
        ctx.log.error(str(exc))
        return False
    return True


# pylint: disable=too-many-arguments
def emit_workspace_report(
    ctx: base_cli.Context,
    document: dict,
    output_format: str,
    *,
    records_key: str,
    columns: Sequence[tuple[str, str]],
    text_renderer: Callable[[], None],
) -> bool:
    try:
        resolved = base_cli.render_document(
            document,
            requested_format=output_format,
            records_key=records_key,
            columns=columns,
        )
    except base_cli.OutputFormatError as exc:
        ctx.log.error(str(exc))
        return False
    if resolved == "text":
        text_renderer()
    return True


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


def resolve_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "command-protocol":
        record = project_record(project.name, project.root, project.manifest_path, manifest)
        print(dumps_record("project-route", record))
    elif output_format == "text":
        print(_project_output(project.name, project.root, project.manifest_path, manifest))
    else:
        ctx.log.error("Unsupported resolve output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def test_command_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
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
    if output_format == "command-protocol":
        print(
            dumps_record(
                "project-command",
                command_record(project.name, project.root, project.manifest_path, command_config, manifest),
            )
        )
    elif output_format == "text":
        print(_command_output(project.name, project.root, project.manifest_path, command_config, manifest))
    else:
        ctx.log.error("Unsupported test-command output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def demo_script_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
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

    if output_format == "command-protocol":
        print(
            dumps_record(
                "demo",
                demo_record(project.name, project.root, project.manifest_path, demo_script, manifest),
            )
        )
    elif output_format == "text":
        print(_demo_output(project.name, project.root, project.manifest_path, demo_script, manifest))
    else:
        ctx.log.error("Unsupported demo-script output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def activation_sources_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
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

    if output_format == "command-protocol":
        print(dumps_records("activation-source", [{"source_path": str(source)} for source in sources]))
    elif output_format == "text":
        for source in sources:
            print(source)
    else:
        ctx.log.error("Unsupported activation-sources output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def run_command_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    command_name: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR
    if not command_name:
        ctx.log.error("Command name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_named_project(ctx, project_name, workspace)
    except (ProjectDiscoveryError, ManifestError, ProjectCommandError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    return run_command_for_project(ctx, project, command_name, output_format)


def run_command_project_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    explicit_project: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
    try:
        project, command_arguments = select_invocation_project(ctx, explicit_project, arguments, workspace)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if len(command_arguments) != 1:
        if not command_arguments:
            ctx.log.error("Command name is required for project '%s'.", project.name)
        else:
            ctx.log.error("Command 'run-command' accepts exactly one command name; got %d.", len(command_arguments))
        return base_cli.ExitCode.USAGE_ERROR
    return run_command_for_project(ctx, project, command_arguments[0], output_format)


def run_command_for_project(
    ctx: base_cli.Context,
    project: Project,
    command_name: str,
    output_format: str = "text",
) -> int:
    try:
        manifest = read_manifest(project.manifest_path)
        command_config = project_command(manifest, command_name)
    except (ManifestError, ProjectCommandError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "command-protocol":
        print(
            dumps_record(
                "project-command",
                command_record(project.name, project.root, project.manifest_path, command_config, manifest),
            )
        )
    elif output_format == "text":
        print(_command_output(project.name, project.root, project.manifest_path, command_config, manifest))
    else:
        ctx.log.error("Unsupported run-command output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def list_run_commands_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    output_format: str = "text",
) -> int:
    if output_format != "command-protocol":
        try:
            base_cli.resolve_output_format(output_format)
        except base_cli.OutputFormatError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
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

    records = [
        named_command_record(
            project.name,
            project.root,
            project.manifest_path,
            command_name,
            command_config,
        )
        for command_name, command_config in commands.items()
    ]
    if output_format == "command-protocol":
        print(
            dumps_records("named-command", records)
        )
    elif output_format in {"json", "yaml"}:
        base_cli.render_document(
            {
                "schema_version": 1,
                "project": {
                    "name": project.name,
                    "root": str(project.root),
                    "manifest_path": str(project.manifest_path),
                },
                "commands": [
                    {
                        "name": command_name,
                        "command": command_config.command,
                        "runner": command_config.runner,
                    }
                    for command_name, command_config in commands.items()
                ],
            },
            requested_format=output_format,
        )
    elif output_format in {"csv", "tsv"} or not base_cli.is_terminal():
        base_cli.render_records(
            records,
            requested_format=output_format,
            columns=(
                ("PROJECT", "project_name"),
                ("COMMAND", "command_name"),
                ("COMMAND LINE", "command"),
                ("RUNNER", "runner"),
            ),
        )
    else:
        for command_name, command_config in commands.items():
            print(
                _named_command_output(
                    project.name,
                    project.root,
                    project.manifest_path,
                    command_name,
                    command_config,
                )
            )
    return base_cli.ExitCode.SUCCESS


def current_project_command(ctx: base_cli.Context, output_format: str = "text") -> int:
    try:
        project = current_project()
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "command-protocol":
        print(
            dumps_record(
                "project-reference",
                {
                    "project_name": project.name,
                    "project_root": str(project.root),
                    "manifest_path": str(project.manifest_path),
                },
            )
        )
    elif output_format == "text":
        print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    else:
        ctx.log.error("Unsupported current output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def manifest_project_command(ctx: base_cli.Context, manifest: str | None, output_format: str = "text") -> int:
    if not manifest:
        ctx.log.error("Manifest path is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = read_project(Path(manifest).expanduser().resolve())
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE
    bind_project_context(ctx, project)

    if output_format == "command-protocol":
        print(
            dumps_record(
                "project-reference",
                {
                    "project_name": project.name,
                    "project_root": str(project.root),
                    "manifest_path": str(project.manifest_path),
                },
            )
        )
    elif output_format == "text":
        print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    else:
        ctx.log.error("Unsupported manifest output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def resolve_named_project(ctx: base_cli.Context, project_name: str, workspace: str | None) -> Project:
    project = find_named_project(ctx, project_name, workspace)
    if project is not None:
        return bind_project_context(ctx, project)

    workspace_root = resolve_workspace_root(ctx, workspace)
    raise ProjectDiscoveryError(f"Project '{project_name}' was not found in workspace '{workspace_root}'.")


def bind_project_context(ctx: base_cli.Context, project: Project) -> Project:
    """Associate a resolved project with the invocation history context."""
    ctx.bind_project(project.name, project.root, project.manifest_path)
    return project


def find_named_project(ctx: base_cli.Context, project_name: str, workspace: str | None) -> Project | None:
    if workspace is None and project_name == "base" and ctx.base_home is not None:
        return read_project(ctx.base_home / "base_manifest.yaml")

    if workspace is None:
        active_project = resolve_active_project(project_name)
        if active_project is not None:
            ctx.log.debug("Resolved active project '%s' from BASE_PROJECT_MANIFEST.", project_name)
            return active_project

    workspace_root = resolve_workspace_root(ctx, workspace)
    projects = discover_projects_cached(ctx, workspace_root)
    return next((project for project in projects if project.name == project_name), None)


def select_invocation_project(
    ctx: base_cli.Context,
    explicit_project: str | None,
    arguments: tuple[str, ...],
    workspace: str | None,
) -> tuple[Project, tuple[str, ...]]:
    if explicit_project is not None:
        return resolve_named_project(ctx, explicit_project, workspace), arguments

    if arguments:
        legacy_project = find_named_project(ctx, arguments[0], workspace)
        if legacy_project is not None:
            return bind_project_context(ctx, legacy_project), arguments[1:]

    return bind_project_context(ctx, current_project()), arguments
