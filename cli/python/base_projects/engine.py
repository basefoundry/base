from __future__ import annotations

import hashlib
import json
import os
import subprocess
import shlex
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import base_cli
from base_cli.config import read_user_config
from base_cli.paths import base_cache_root
from base_cli.paths import discover_manifest
from base_projects.build_targets import build_targets_project_from_args
from base_projects.build_targets import list_build_targets_from_args
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_reports import ManifestEntry
from base_projects.workspace_reports import ProjectDiscoveryError
from base_projects.workspace_reports import dumps_json
from base_projects.workspace_reports import print_workspace_check
from base_projects.workspace_reports import print_workspace_doctor
from base_projects.workspace_reports import print_workspace_status
from base_projects.workspace_reports import resolve_workspace_manifest
from base_projects.workspace_reports import workspace_check_to_json
from base_projects.workspace_reports import workspace_doctor_to_json
from base_projects.workspace_reports import workspace_error_count
from base_projects.workspace_reports import workspace_manifest_entries
from base_projects.workspace_reports import workspace_project_check_results
from base_projects.workspace_reports import workspace_project_statuses
from base_projects.workspace_reports import workspace_status_to_json
from base_setup.demo import resolve_demo_script_path
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest, CommandConfig, ManifestError, TestConfig, read_manifest


app = base_cli.App(name="base_projects")


@dataclass(frozen=True, order=True)
class Project:
    name: str
    root: Path
    manifest_path: Path


@dataclass(frozen=True)
class WorkspaceCommandOptions:
    workspace: str | None
    output_format: str
    workspace_manifest: str | None = None
    include_optional: bool = False
    dry_run: bool = False


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("arguments", nargs=-1)
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option("--format", "output_format", default="text", help="Output format: text or json.")
@base_cli.option("--manifest", "workspace_manifest", help="Local workspace manifest to read.")
@base_cli.option(
    "--include-optional",
    is_flag=True,
    help="Include optional workspace manifest repositories when cloning.",
)
@base_cli.option("--dry-run", is_flag=True, dry_run=True, help="Show planned clone work without cloning.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    output_format: str,
    workspace_manifest: str | None,
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
                include_optional=include_optional,
                dry_run=dry_run,
            ),
        )
    except ProjectUsageError as exc:
        ctx.log.error(str(exc))
        return 2


def dispatch_projects_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    command = arguments[0] if arguments else "list"
    command_arguments = arguments[1:] if arguments else ()
    resolver = resolve_named_project
    handlers = {
        "list": lambda: list_projects_from_args(ctx, command_arguments, options.workspace, options.output_format),
        "status": lambda: workspace_status_from_args(
            ctx,
            command_arguments,
            options,
        ),
        "check": lambda: require_no_args_and_run(
            "check",
            command_arguments,
            lambda: workspace_check_command(
                ctx,
                options.workspace,
                options.output_format,
                options.workspace_manifest,
            ),
        ),
        "doctor": lambda: require_no_args_and_run(
            "doctor",
            command_arguments,
            lambda: workspace_doctor_command(
                ctx,
                options.workspace,
                options.output_format,
                options.workspace_manifest,
            ),
        ),
        "clone": lambda: require_no_args_and_run(
            "clone",
            command_arguments,
            lambda: workspace_clone_command(ctx, options),
        ),
        "current": lambda: current_project_from_args(ctx, command_arguments),
        "manifest": lambda: manifest_project_from_args(ctx, command_arguments),
        "resolve": lambda: resolve_project_from_args(ctx, command_arguments, options.workspace),
        "test-command": lambda: test_command_project_from_args(ctx, command_arguments, options.workspace),
        "demo-script": lambda: demo_script_project_from_args(ctx, command_arguments, options.workspace),
        "activation-sources": lambda: activation_sources_project_from_args(ctx, command_arguments, options.workspace),
        "run-command": lambda: run_command_project_from_args(ctx, command_arguments, options.workspace),
        "run-commands": lambda: list_run_commands_from_args(ctx, command_arguments, options.workspace),
        "build-targets": lambda: build_targets_project_from_args(ctx, command_arguments, options.workspace, resolver),
        "build-target-list": lambda: list_build_targets_from_args(ctx, command_arguments, options.workspace, resolver),
    }
    handler = handlers.get(command)
    if handler is not None:
        return handler()

    ctx.log.error(
        "Unknown projects command '%s'. Supported commands: list, current, manifest, resolve, "
        "status, check, doctor, clone, test-command, demo-script, activation-sources, run-command, run-commands, "
        "build-targets, build-target-list.",
        command,
    )
    return 2


class ProjectUsageError(RuntimeError):
    pass


def require_argument_count(command: str, arguments: tuple[str, ...], minimum: int, maximum: int) -> None:
    if len(arguments) < minimum:
        raise ProjectUsageError(f"Project command '{command}' requires at least {minimum} argument(s).")
    if len(arguments) > maximum:
        raise ProjectUsageError(f"Project command '{command}' accepts at most {maximum} argument(s).")


def require_no_args_and_run(command: str, arguments: tuple[str, ...], callback: Callable[[], int]) -> int:
    require_argument_count(command, arguments, 0, 0)
    return callback()


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


def list_projects_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        projects = discover_projects_cached(ctx, workspace_root)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(
            json.dumps(
                [{"name": project.name, "path": str(project.root)} for project in projects],
                separators=(",", ":"),
            )
        )
        return 0

    for project in projects:
        print(f"{project.name}\t{project.root}")
    return 0


def workspace_status_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(workspace_manifest)
        statuses = workspace_project_statuses(workspace_root, manifest)
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(dumps_json(workspace_status_to_json(workspace_root, statuses, manifest)))
    else:
        print_workspace_status(workspace_root, statuses, manifest)

    return 1 if any(project.status == "error" for project in statuses) else 0


def workspace_check_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(workspace_manifest)
        results = workspace_project_check_results(ctx, workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(dumps_json(workspace_check_to_json(workspace_root, results, manifest)))
    else:
        print_workspace_check(workspace_root, results, manifest)

    return 1 if any(result.status == "error" for result in results) else 0


def workspace_doctor_command(
    ctx: base_cli.Context,
    workspace: str | None,
    output_format: str = "text",
    workspace_manifest: str | None = None,
) -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        manifest = resolve_workspace_manifest(workspace_manifest)
        results = workspace_project_check_results(ctx, workspace_root, manifest)
    except (ProjectDiscoveryError, ManifestError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(dumps_json(workspace_doctor_to_json(workspace_root, results, manifest)))
    else:
        print_workspace_doctor(workspace_root, results, manifest)

    return min(workspace_error_count(results), 125)


def workspace_clone_command(ctx: base_cli.Context, options: WorkspaceCommandOptions) -> int:
    if options.output_format != "text":
        raise ProjectUsageError(f"Unsupported output format '{options.output_format}'. Expected: text.")

    try:
        workspace_root = resolve_workspace_root(ctx, options.workspace)
        manifest = require_workspace_clone_manifest(options.workspace_manifest)
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if ctx.base_home is None:
        ctx.log.error("BASE_HOME is required to clone workspace repositories.")
        return 1

    basectl = ctx.base_home / "bin" / "basectl"
    print(f"Workspace clone: {workspace_root} ({len(manifest.repos)} repositories)")
    print(f"Workspace manifest: {manifest.path} ({manifest.name})")

    errors = 0
    for repo in manifest.repos:
        target = (workspace_root / repo.name).resolve()
        required_label = "required" if repo.required else "optional"
        if should_skip_optional_clone(repo, target, options.include_optional):
            print_optional_clone_skip(repo, target)
            continue

        verb = "CHECK" if target.exists() else "CLONE"
        preposition = "at" if target.exists() else "into"
        print(f"{verb} {required_label} repository '{repo.name}' {preposition} '{target}'.")
        errors += clone_workspace_repo(ctx, basectl, repo, target, dry_run=options.dry_run)

    if errors:
        print(f"Workspace clone completed with {errors} error(s).")
        return 1

    print("Workspace clone completed.")
    return 0


def require_workspace_clone_manifest(workspace_manifest: str | None) -> WorkspaceManifest:
    if workspace_manifest is None:
        raise ProjectUsageError("workspace clone requires --manifest <path>.")
    manifest = resolve_workspace_manifest(workspace_manifest)
    if manifest is None:
        raise ProjectUsageError("workspace clone requires --manifest <path>.")
    return manifest


def should_skip_optional_clone(repo: WorkspaceManifestRepo, target: Path, include_optional: bool) -> bool:
    return not repo.required and not include_optional and not target.exists()


def print_optional_clone_skip(repo: WorkspaceManifestRepo, target: Path) -> None:
    print(
        f"SKIP optional repository '{repo.name}' is missing at '{target}'. "
        "Pass --include-optional to clone it."
    )


def clone_workspace_repo(
    ctx: base_cli.Context,
    basectl: Path,
    repo: WorkspaceManifestRepo,
    target: Path,
    *,
    dry_run: bool,
) -> int:
    repo_spec = workspace_clone_repo_spec(repo)
    if repo_spec is None:
        ctx.log.error(
            "Repository '%s' has unsupported clone URL '%s'. Only github.com repository URLs are supported.",
            repo.name,
            repo.url,
        )
        return 1

    command = [str(basectl), "repo", "clone", repo_spec, "--path", str(target)]
    if dry_run:
        command.append("--dry-run")

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        ctx.log.error("Could not run basectl repo clone for repository '%s': %s", repo.name, exc)
        return 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0:
        return 0

    ctx.log.error("Clone failed for repository '%s'.", repo.name)
    return 1


def workspace_clone_repo_spec(repo: WorkspaceManifestRepo) -> str | None:
    if repo.url is None:
        return repo.name

    url = repo.url
    parsed = urlparse(url)
    if parsed.scheme and parsed.hostname == "github.com":
        return github_repo_spec_from_path(parsed.path)

    git_ssh_prefix = "git@github.com:"
    if url.startswith(git_ssh_prefix):
        return github_repo_spec_from_path(url[len(git_ssh_prefix) :])

    return None


def github_repo_spec_from_path(path: str) -> str | None:
    normalized = path.strip().lstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    parts = normalized.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return f"{parts[0]}/{parts[1]}"


def resolve_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return 2

    try:
        project = resolve_named_project(ctx, project_name, workspace)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    return 0


def test_command_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    try:
        if project_name:
            project = resolve_named_project(ctx, project_name, workspace)
        else:
            project = current_project()
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if manifest.test is None:
        ctx.log.error(
            "Project '%s' does not declare test.command or test.mise in '%s'.",
            project.name,
            project.manifest_path,
        )
        return 1

    command_config = test_command(manifest.test)
    print(_command_output(project.name, project.root, project.manifest_path, command_config))
    return 0


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
            return 1
        demo_script = resolve_demo_script_path(manifest)
    except (ProjectDiscoveryError, ManifestError, ArtifactError) as exc:
        ctx.log.error(str(exc))
        return 1

    print(_demo_output(project.name, project.root, project.manifest_path, demo_script, manifest.demo.runner))
    return 0


def activation_sources_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return 2

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
        sources = activation_source_paths(project, manifest.activate.source)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    for source in sources:
        print(source)
    return 0


def run_command_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    command_name: str | None,
    workspace: str | None,
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return 2
    if not command_name:
        ctx.log.error("Command name is required.")
        return 2

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
        command_config = project_command(manifest, command_name)
    except (ProjectDiscoveryError, ManifestError, ProjectCommandError) as exc:
        ctx.log.error(str(exc))
        return 1

    print(_command_output(project.name, project.root, project.manifest_path, command_config))
    return 0


def list_run_commands_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    try:
        if project_name:
            project = resolve_named_project(ctx, project_name, workspace)
        else:
            project = current_project()
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    commands = project_commands(manifest)
    if not commands:
        ctx.log.error("Project '%s' does not declare runnable commands in '%s'.", project.name, project.manifest_path)
        return 1

    for command_name, command_config in commands.items():
        print(_named_command_output(project.name, project.root, project.manifest_path, command_name, command_config))
    return 0


def current_project_command(ctx: base_cli.Context) -> int:
    try:
        project = current_project()
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    return 0


def current_project() -> Project:
    manifest_path = discover_manifest(Path.cwd())
    if manifest_path is None:
        raise ProjectDiscoveryError(f"No base_manifest.yaml found from '{Path.cwd()}' upward.")

    return read_project(manifest_path)


def test_command(test_config: TestConfig) -> CommandConfig:
    if test_config.command is not None:
        return CommandConfig(command=test_config.command, runner=test_config.runner)
    if test_config.mise is not None:
        return CommandConfig(command=shlex.join(["mise", "run", test_config.mise]), runner=test_config.runner)
    raise ValueError("TestConfig must have command or mise set.")


class ProjectCommandError(RuntimeError):
    pass


def project_commands(manifest: BaseManifest) -> dict[str, CommandConfig]:
    commands: dict[str, CommandConfig] = {}
    if manifest.test is not None:
        commands["test"] = test_command(manifest.test)
    commands.update(manifest.commands)
    return commands


def project_command(manifest: BaseManifest, command_name: str) -> CommandConfig:
    commands = project_commands(manifest)
    try:
        return commands[command_name]
    except KeyError as exc:
        if command_name == "test":
            raise ProjectCommandError(
                f"Project '{manifest.project_name}' does not declare test.command or test.mise in '{manifest.path}'."
            ) from exc
        raise ProjectCommandError(
            f"Project '{manifest.project_name}' does not declare command '{command_name}' in '{manifest.path}'."
        ) from exc


def _command_output(project_name: str, project_root: Path, manifest_path: Path, command: CommandConfig) -> str:
    fields = [project_name, str(project_root), str(manifest_path), command.command]
    if command.runner is not None:
        fields.append(command.runner)
    return "\t".join(fields)


def _named_command_output(
    project_name: str,
    project_root: Path,
    manifest_path: Path,
    command_name: str,
    command: CommandConfig,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), command_name, command.command]
    if command.runner is not None:
        fields.append(command.runner)
    return "\t".join(fields)


def _demo_output(
    project_name: str,
    project_root: Path,
    manifest_path: Path,
    demo_script: Path,
    runner: str | None,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), str(demo_script)]
    if runner is not None:
        fields.append(runner)
    return "\t".join(fields)


def activation_source_paths(project: Project, source_paths: tuple[str, ...]) -> tuple[Path, ...]:
    return tuple(
        resolve_activation_source_path(project, source_path, index)
        for index, source_path in enumerate(source_paths, start=1)
    )


def resolve_activation_source_path(project: Project, source_path: str, index: int) -> Path:
    field = f"activate.source[{index}]"
    project_root = project.root.resolve()
    declared_path = Path(source_path)
    if declared_path.is_absolute():
        raise ProjectDiscoveryError(
            f"{project.manifest_path}: {field} must be a relative path inside the project root."
        )

    candidate = (project_root / declared_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ProjectDiscoveryError(
            f"{project.manifest_path}: {field} resolves outside the project root: {source_path}."
        ) from exc

    if not candidate.exists():
        raise ProjectDiscoveryError(f"{project.manifest_path}: {field} script '{source_path}' does not exist.")
    if not candidate.is_file():
        raise ProjectDiscoveryError(f"{project.manifest_path}: {field} script '{source_path}' is not a file.")
    return candidate


def manifest_project_command(ctx: base_cli.Context, manifest: str | None) -> int:
    if not manifest:
        ctx.log.error("Manifest path is required.")
        return 2

    try:
        project = read_project(Path(manifest).expanduser().resolve())
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    return 0


def resolve_workspace_root(ctx: base_cli.Context, workspace: str | None) -> Path:
    if workspace:
        return Path(workspace).expanduser().resolve()
    try:
        workspace_root = read_user_config().workspace.root
    except (RuntimeError, ValueError) as exc:
        raise ProjectDiscoveryError(str(exc)) from exc
    if workspace_root is not None:
        return workspace_root
    if ctx.base_home is None:
        raise ProjectDiscoveryError("BASE_HOME is required to discover workspace projects.")
    return ctx.base_home.parent.resolve()


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


def discover_projects(workspace_root: Path) -> tuple[Project, ...]:
    entries = workspace_manifest_entries(workspace_root)
    projects = tuple(read_project(entry.path) for entry in entries)
    return validate_unique_project_names(tuple(sorted(projects)))


def discover_projects_cached(ctx: base_cli.Context, workspace_root: Path) -> tuple[Project, ...]:
    start = time.perf_counter()
    entries = workspace_manifest_entries(workspace_root)
    cached_projects = read_project_cache(workspace_root, entries)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if cached_projects is not None:
        ctx.log.debug(
            "Project discovery cache hit for '%s': %d project(s) in %.1fms.",
            workspace_root,
            len(cached_projects),
            elapsed_ms,
        )
        return cached_projects

    projects = validate_unique_project_names(tuple(sorted(read_project(entry.path) for entry in entries)))
    write_project_cache(workspace_root, entries, projects, ctx)
    elapsed_ms = (time.perf_counter() - start) * 1000
    ctx.log.debug(
        "Project discovery scanned '%s': %d project(s) in %.1fms.",
        workspace_root,
        len(projects),
        elapsed_ms,
    )
    return projects


def find_project(workspace_root: Path, project_name: str) -> Project:
    projects = discover_projects(workspace_root)
    return find_project_in_projects(projects, workspace_root, project_name)


def find_project_in_projects(projects: tuple[Project, ...], workspace_root: Path, project_name: str) -> Project:
    for project in projects:
        if project.name == project_name:
            return project
    raise ProjectDiscoveryError(f"Project '{project_name}' was not found in workspace '{workspace_root}'.")


def resolve_active_project(project_name: str) -> Project | None:
    if os.environ.get("BASE_PROJECT") != project_name:
        return None

    manifest = os.environ.get("BASE_PROJECT_MANIFEST")
    if not manifest:
        return None

    project = read_project(Path(manifest).expanduser().resolve())
    if project.name != project_name:
        raise ProjectDiscoveryError(
            f"BASE_PROJECT is '{project_name}' but BASE_PROJECT_MANIFEST points to project '{project.name}'."
        )
    return project


def project_cache_path(workspace_root: Path) -> Path:
    workspace_key = hashlib.sha256(str(workspace_root).encode("utf-8")).hexdigest()[:24]
    return base_cache_root() / "projects" / f"{workspace_key}.json"


def read_project_cache(workspace_root: Path, entries: tuple[ManifestEntry, ...]) -> tuple[Project, ...] | None:
    cache_path = project_cache_path(workspace_root)
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if data.get("version") != 1 or data.get("workspace") != str(workspace_root):
        return None
    if data.get("manifests") != [manifest_entry_to_json(entry) for entry in entries]:
        return None

    try:
        projects = tuple(
            Project(
                name=project["name"],
                root=Path(project["root"]),
                manifest_path=Path(project["manifest_path"]),
            )
            for project in data["projects"]
        )
    except (KeyError, TypeError):
        return None
    return validate_unique_project_names(tuple(sorted(projects)))


def write_project_cache(
    workspace_root: Path,
    entries: tuple[ManifestEntry, ...],
    projects: tuple[Project, ...],
    ctx: base_cli.Context,
) -> None:
    cache_path = project_cache_path(workspace_root)
    data = {
        "version": 1,
        "workspace": str(workspace_root),
        "manifests": [manifest_entry_to_json(entry) for entry in entries],
        "projects": [project_to_json(project) for project in projects],
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    except OSError as exc:
        ctx.log.debug("Unable to write project discovery cache '%s': %s", cache_path, exc)


def manifest_entry_to_json(entry: ManifestEntry) -> dict[str, Any]:
    return {
        "path": str(entry.path),
        "mtime_ns": entry.mtime_ns,
        "size": entry.size,
    }


def project_to_json(project: Project) -> dict[str, str]:
    return {
        "name": project.name,
        "root": str(project.root),
        "manifest_path": str(project.manifest_path),
    }


def read_project(manifest_path: Path) -> Project:
    try:
        manifest = read_manifest(manifest_path)
    except ManifestError as exc:
        raise ProjectDiscoveryError(str(exc)) from exc
    return Project(
        name=manifest.project_name,
        root=manifest_path.parent.resolve(),
        manifest_path=manifest_path.resolve(),
    )


def validate_unique_project_names(projects: tuple[Project, ...]) -> tuple[Project, ...]:
    seen: dict[str, Project] = {}
    duplicates = []
    for project in projects:
        existing = seen.get(project.name)
        if existing is not None:
            duplicates.append((project, existing))
        else:
            seen[project.name] = project

    if duplicates:
        details = "; ".join(
            f"{project.name}: {existing.root} and {project.root}" for project, existing in duplicates
        )
        raise ProjectDiscoveryError(f"Duplicate project names found: {details}.")

    return projects
