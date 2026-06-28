from __future__ import annotations

# pylint: disable=too-many-lines

import json
import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import base_cli
from base_cli.config import load_user_config
from base_cli.config import user_config_path
from base_projects.build_targets import build_targets_project_from_args
from base_projects.build_targets import list_build_targets_from_args
from base_projects.command_helpers import ProjectCommandError as ProjectRunnerError
from base_projects.command_helpers import ProjectUsageError
from base_projects.command_helpers import github_repo_spec
from base_projects.command_helpers import run_project_command
from base_projects.command_helpers import write_project_command_output
from base_projects.project_discovery import Project
from base_projects.project_discovery import discover_projects_cached
from base_projects.project_discovery import find_project_in_projects
from base_projects.project_discovery import current_project
from base_projects.project_discovery import read_project
from base_projects.project_discovery import resolve_active_project
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_configure import workspace_configure_from_options
from base_projects.workspace_pull import pull_workspace_manifest
from base_projects.workspace_reports import ProjectDiscoveryError
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
from base_setup.demo import resolve_demo_script_path
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest, CommandConfig, ManifestError, TestConfig, read_manifest
from base_setup.project_routing import route_for_manifest


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


@dataclass(frozen=True)
class WorkspaceInitSource:
    display: str
    repo_spec: str | None = None
    repo_name: str | None = None
    local_path: Path | None = None


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
        "pull": lambda: require_no_args_and_run(
            "pull",
            command_arguments,
            lambda: workspace_pull_command(ctx, options),
        ),
        "init": lambda: workspace_init_from_args(ctx, command_arguments, options),
        "configure": lambda: require_no_args_and_run(
            "configure", command_arguments, lambda: workspace_configure_from_options(ctx, options)
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
        "status, check, doctor, clone, configure, init, test-command, demo-script, activation-sources, run-command, "
        "run-commands, build-targets, build-target-list, pull.",
        command,
    )
    return 2


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


def workspace_init_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    options: WorkspaceCommandOptions,
) -> int:
    require_argument_count("init", arguments, 1, 1)
    return workspace_init_command(ctx, arguments[0], options)


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
        effective_manifest = effective_workspace_manifest(ctx, workspace_manifest)
        log_workspace_status_discovery(ctx, workspace, workspace_root, workspace_manifest, effective_manifest)
        manifest = resolve_workspace_manifest(effective_manifest)
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
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
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
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, workspace_manifest))
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
        manifest = require_workspace_clone_manifest(ctx, options.workspace_manifest)
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


def workspace_pull_command(ctx: base_cli.Context, options: WorkspaceCommandOptions) -> int:
    if options.output_format != "text":
        raise ProjectUsageError(f"Unsupported output format '{options.output_format}'. Expected: text.")

    source = effective_workspace_manifest_source(ctx, options.workspace_manifest_source)
    if source is None:
        raise ProjectUsageError("workspace pull requires --source <url-or-path> or workspace.manifest_source.")

    target = effective_workspace_manifest_path(ctx, options.workspace_manifest)
    if target is None:
        raise ProjectUsageError("workspace pull requires --manifest <path> or workspace.manifest.")

    try:
        result = pull_workspace_manifest(source, target, dry_run=options.dry_run)
    except WorkspaceManifestError as exc:
        ctx.log.error(str(exc))
        return 1

    print("Workspace manifest pull")
    print(f"Source: {result.source}")
    print(f"Target: {result.target}")
    print(f"Manifest: {result.manifest.name} ({len(result.manifest.repos)} repositories)")
    print(f"Status: {result.status}")

    if options.dry_run:
        print("[DRY-RUN] No files changed.")
        return 0

    if not result.changed:
        print("Workspace manifest already up to date.")
        return 0

    print(f"Updated workspace manifest: {result.target}")
    return 0


def workspace_init_command(ctx: base_cli.Context, workspace_source: str, options: WorkspaceCommandOptions) -> int:
    if options.output_format != "text":
        raise ProjectUsageError(f"Unsupported output format '{options.output_format}'. Expected: text.")

    try:
        source = resolve_workspace_init_source(ctx, workspace_source, options.workspace_owner)
        config_repo = resolve_workspace_config_repo_path(ctx, source, options)
        workspace_root = resolve_workspace_init_root(ctx, options.workspace, config_repo)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    print("Workspace init")
    print(f"Workspace source: {source.display}")
    print(f"Workspace config repo: {config_repo}")
    print(f"Workspace root: {workspace_root}")

    try:
        if source.repo_spec is not None:
            clone_workspace_config_repo(ctx, source.repo_spec, config_repo, dry_run=options.dry_run)
        manifest_path = resolve_workspace_init_manifest_path(config_repo, options.workspace_manifest)
        if options.dry_run and source.repo_spec is not None and not manifest_path.is_file():
            print(f"[DRY-RUN] Would read workspace manifest: {manifest_path}")
            print("[DRY-RUN] Would update user config:")
            print(f"  workspace.root: {workspace_root}")
            print(f"  workspace.manifest: {manifest_path}")
            print("[DRY-RUN] Skipping member repository plan because the workspace config repo is not present.")
            return 0
        manifest = resolve_workspace_manifest(str(manifest_path))
        if manifest is None:
            raise WorkspaceManifestError(f"{manifest_path}: workspace manifest is required.")
    except WorkspaceManifestError as exc:
        ctx.log.error(str(exc))
        return 1

    print(f"Workspace manifest: {manifest.path} ({manifest.name})")

    if options.dry_run:
        print("[DRY-RUN] Would update user config:")
        print(f"  workspace.root: {workspace_root}")
        print(f"  workspace.manifest: {manifest.path}")
    else:
        write_workspace_init_user_config(workspace_root, manifest.path)
        print(f"Updated user config: {user_config_path()}")

    clone_options = WorkspaceCommandOptions(
        workspace=str(workspace_root),
        output_format="text",
        workspace_manifest=str(manifest.path),
        include_optional=options.include_optional,
        dry_run=options.dry_run,
    )
    return workspace_clone_command(ctx, clone_options)


def resolve_workspace_init_source(
    ctx: base_cli.Context,
    workspace_source: str,
    owner: str | None,
) -> WorkspaceInitSource:
    source_path = Path(workspace_source).expanduser()
    if workspace_source.startswith("file://"):
        parsed = urlparse(workspace_source)
        return WorkspaceInitSource(
            display=workspace_source,
            local_path=Path(parsed.path).expanduser().resolve(strict=False),
        )
    if is_workspace_init_path_source(workspace_source) or source_path.exists():
        return WorkspaceInitSource(
            display=workspace_source,
            local_path=source_path.resolve(strict=False),
        )

    repo_spec = workspace_init_github_repo_spec(workspace_source)
    if repo_spec is not None:
        return WorkspaceInitSource(
            display=repo_spec,
            repo_spec=repo_spec,
            repo_name=repo_spec.split("/", 1)[1],
        )

    if "/" in workspace_source:
        raise ProjectUsageError(
            "Workspace source must be a local path, GitHub URL, "
            "'<owner>/<repo>', or short repo name."
        )

    effective_owner = owner or ctx.user_config.github.default_owner
    if effective_owner is None:
        raise ProjectUsageError(
            "Workspace source owner is required for short repo names. "
            "Pass --owner <owner> or set github.default_owner in ~/.base.d/config.yaml."
        )
    repo_spec = f"{effective_owner}/{workspace_source}"
    return WorkspaceInitSource(display=repo_spec, repo_spec=repo_spec, repo_name=workspace_source)


def is_workspace_init_path_source(workspace_source: str) -> bool:
    return workspace_source.startswith(("/", "./", "../", "~"))


def workspace_init_github_repo_spec(workspace_source: str) -> str | None:
    return github_repo_spec(workspace_source, allow_path=True)


def resolve_workspace_config_repo_path(
    ctx: base_cli.Context,
    source: WorkspaceInitSource,
    options: WorkspaceCommandOptions,
) -> Path:
    if options.workspace_config_path is not None:
        return Path(options.workspace_config_path).expanduser().resolve(strict=False)
    if source.local_path is not None:
        return source.local_path
    workspace_root = resolve_workspace_init_root(ctx, options.workspace, None)
    assert source.repo_name is not None
    return (workspace_root / source.repo_name).resolve(strict=False)


def resolve_workspace_init_manifest_path(config_repo: Path, workspace_manifest: str | None) -> Path:
    if workspace_manifest is None:
        return (config_repo / "workspace.yaml").resolve(strict=False)
    manifest_path = Path(workspace_manifest).expanduser()
    if manifest_path.is_absolute():
        return manifest_path.resolve(strict=False)
    return (config_repo / manifest_path).resolve(strict=False)


def resolve_workspace_init_root(ctx: base_cli.Context, workspace: str | None, config_repo: Path | None) -> Path:
    if workspace is not None:
        return Path(workspace).expanduser().resolve(strict=False)
    if ctx.workspace_root is not None:
        return ctx.workspace_root
    if config_repo is None:
        if ctx.base_home is None:
            raise ProjectDiscoveryError("BASE_HOME is required to resolve the default workspace root.")
        return ctx.base_home.parent.resolve(strict=False)
    return config_repo.parent.resolve(strict=False)


def clone_workspace_config_repo(ctx: base_cli.Context, repo_spec: str, target: Path, *, dry_run: bool) -> None:
    if ctx.base_home is None:
        raise WorkspaceManifestError("BASE_HOME is required to clone the workspace configuration repository.")
    basectl = ctx.base_home / "bin" / "basectl"
    command = [str(basectl), "repo", "clone", repo_spec, "--path", str(target)]
    if dry_run:
        command.append("--dry-run")
    try:
        result = run_project_command(
            command,
            error_context=f"basectl repo clone for workspace source '{repo_spec}'",
        )
    except ProjectRunnerError as exc:
        raise WorkspaceManifestError(str(exc)) from exc
    write_project_command_output(result)
    if result.returncode != 0:
        raise WorkspaceManifestError(f"Workspace source clone failed for '{repo_spec}'.")


def write_workspace_init_user_config(workspace_root: Path, manifest_path: Path) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise WorkspaceManifestError(
            "PyYAML is required to update ~/.base.d/config.yaml. "
            "Run 'basectl setup' to install Base Python bootstrap dependencies."
        ) from exc

    config_path = user_config_path()
    raw_config = load_user_config()
    workspace_config = dict(raw_config.get("workspace") or {})
    workspace_config["root"] = str(workspace_root)
    workspace_config["manifest"] = str(manifest_path)
    raw_config["workspace"] = workspace_config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(raw_config, sort_keys=False), encoding="utf-8")


def effective_workspace_manifest(ctx: base_cli.Context, workspace_manifest: str | None) -> str | None:
    if workspace_manifest is not None:
        return workspace_manifest
    configured_manifest = ctx.user_config.workspace.manifest
    if configured_manifest is None:
        return None
    return str(configured_manifest)


def effective_workspace_manifest_path(ctx: base_cli.Context, workspace_manifest: str | None) -> Path | None:
    if workspace_manifest is not None:
        return Path(workspace_manifest).expanduser().resolve(strict=False)
    configured_manifest = ctx.user_config.workspace.manifest
    if configured_manifest is None:
        return None
    return configured_manifest


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


def effective_workspace_manifest_source(ctx: base_cli.Context, workspace_manifest_source: str | None) -> str | None:
    if workspace_manifest_source is not None:
        return workspace_manifest_source
    return ctx.user_config.workspace.manifest_source


def require_workspace_clone_manifest(ctx: base_cli.Context, workspace_manifest: str | None) -> WorkspaceManifest:
    effective_manifest = effective_workspace_manifest(ctx, workspace_manifest)
    if effective_manifest is None:
        raise ProjectUsageError("workspace clone requires --manifest <path>.")
    manifest = resolve_workspace_manifest(effective_manifest)
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
        result = run_project_command(
            command,
            error_context=f"basectl repo clone for repository '{repo.name}'",
        )
    except ProjectRunnerError as exc:
        ctx.log.error(str(exc))
        return 1

    write_project_command_output(result)
    if result.returncode == 0:
        return 0

    ctx.log.error("Clone failed for repository '%s'.", repo.name)
    return 1


def workspace_clone_repo_spec(repo: WorkspaceManifestRepo) -> str | None:
    if repo.url is None:
        return repo.name

    return github_repo_spec(repo.url)


def resolve_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return 2

    try:
        project = resolve_named_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    print(_project_output(project.name, project.root, project.manifest_path, manifest))
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
    print(_command_output(project.name, project.root, project.manifest_path, command_config, manifest))
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

    print(_demo_output(project.name, project.root, project.manifest_path, demo_script, manifest))
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

    print(_command_output(project.name, project.root, project.manifest_path, command_config, manifest))
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


def _route_metadata_fields(manifest: BaseManifest) -> list[str]:
    route = route_for_manifest(manifest)
    uses_uv = "true" if route.uses_uv_manager else "false"
    return [
        f"__base_project_venv_dir={route.project_venv_dir}",
        f"__base_uses_uv_manager={uses_uv}",
    ]


def _project_output(project_name: str, project_root: Path, manifest_path: Path, manifest: BaseManifest) -> str:
    return "\t".join([project_name, str(project_root), str(manifest_path), *_route_metadata_fields(manifest)])


def _command_output(
    project_name: str,
    project_root: Path,
    manifest_path: Path,
    command: CommandConfig,
    manifest: BaseManifest,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), command.command]
    if command.runner is not None:
        fields.append(command.runner)
    fields.extend(_route_metadata_fields(manifest))
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
    manifest: BaseManifest,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), str(demo_script)]
    if manifest.demo.runner is not None:
        fields.append(manifest.demo.runner)
    fields.extend(_route_metadata_fields(manifest))
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
    if ctx.workspace_root is not None:
        return ctx.workspace_root
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
