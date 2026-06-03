from __future__ import annotations

import hashlib
import json
import os
import shlex
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base_cli
from base_cli.config import read_user_config
from base_cli.paths import base_cache_root, base_state_root
from base_cli.paths import discover_manifest
from base_setup.checks import ArtifactCheck
from base_setup.checks import check_to_doctor_json
from base_setup.checks import check_to_json
from base_setup.checks import doctor_status
from base_setup.checks import print_doctor_finding
from base_setup.demo import resolve_demo_script_path
from base_setup.engine import manifest_checks
from base_setup.engine import read_default_manifest
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest, ManifestError, TestConfig, read_manifest


app = base_cli.App(name="base_projects")


@dataclass(frozen=True, order=True)
class Project:
    name: str
    root: Path
    manifest_path: Path


@dataclass(frozen=True)
class ManifestEntry:
    path: Path
    mtime_ns: int
    size: int


@dataclass(frozen=True)
class WorkspaceProjectStatus:
    name: str
    root: Path
    manifest_path: Path
    status: str
    venv: str
    manifest: str
    issues: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceProjectCheckResult:
    name: str
    root: Path
    manifest_path: Path
    manifest: str
    status: str
    checks: tuple[ArtifactCheck, ...]


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
def run(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    output_format: str,
) -> int:
    try:
        return dispatch_projects_command(ctx, arguments, workspace, output_format)
    except ProjectUsageError as exc:
        ctx.log.error(str(exc))
        return 2


def dispatch_projects_command(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    output_format: str,
) -> int:
    command = arguments[0] if arguments else "list"
    command_arguments = arguments[1:] if arguments else ()
    handlers = {
        "list": lambda: list_projects_from_args(ctx, command_arguments, workspace, output_format),
        "status": lambda: workspace_status_from_args(ctx, command_arguments, workspace, output_format),
        "check": lambda: require_no_args_and_run(
            "check", command_arguments, lambda: workspace_check_command(ctx, workspace, output_format)
        ),
        "doctor": lambda: require_no_args_and_run(
            "doctor", command_arguments, lambda: workspace_doctor_command(ctx, workspace, output_format)
        ),
        "current": lambda: current_project_from_args(ctx, command_arguments),
        "manifest": lambda: manifest_project_from_args(ctx, command_arguments),
        "resolve": lambda: resolve_project_from_args(ctx, command_arguments, workspace),
        "test-command": lambda: test_command_project_from_args(ctx, command_arguments, workspace),
        "demo-script": lambda: demo_script_project_from_args(ctx, command_arguments, workspace),
        "activation-sources": lambda: activation_sources_project_from_args(ctx, command_arguments, workspace),
        "run-command": lambda: run_command_project_from_args(ctx, command_arguments, workspace),
        "run-commands": lambda: list_run_commands_from_args(ctx, command_arguments, workspace),
    }
    handler = handlers.get(command)
    if handler is not None:
        return handler()

    ctx.log.error(
        "Unknown projects command '%s'. Supported commands: list, current, manifest, resolve, "
        "status, check, doctor, test-command, demo-script, activation-sources, run-command, run-commands.",
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
    workspace: str | None,
    output_format: str,
) -> int:
    require_argument_count("status", arguments, 0, 0)
    return workspace_status_command(ctx, workspace, output_format)


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


def workspace_status_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        statuses = workspace_project_statuses(workspace_root)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(json.dumps(workspace_status_to_json(workspace_root, statuses), separators=(",", ":")))
    else:
        print_workspace_status(workspace_root, statuses)

    return 1 if any(project.status == "error" for project in statuses) else 0


def workspace_check_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        results = workspace_project_check_results(ctx, workspace_root)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(json.dumps(workspace_check_to_json(workspace_root, results), separators=(",", ":")))
    else:
        print_workspace_check(workspace_root, results)

    return 1 if any(result.status == "error" for result in results) else 0


def workspace_doctor_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        results = workspace_project_check_results(ctx, workspace_root)
    except (ProjectDiscoveryError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

    if output_format == "json":
        print(json.dumps(workspace_doctor_to_json(workspace_root, results), separators=(",", ":")))
    else:
        print_workspace_doctor(workspace_root, results)

    return min(workspace_error_count(results), 125)


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

    print(f"{project.name}\t{project.root}\t{project.manifest_path}\t{test_command(manifest.test)}")
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

    print(f"{project.name}\t{project.root}\t{project.manifest_path}\t{demo_script}")
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
        command_text = project_command(manifest, command_name)
    except (ProjectDiscoveryError, ManifestError, ProjectCommandError) as exc:
        ctx.log.error(str(exc))
        return 1

    print(f"{project.name}\t{project.root}\t{project.manifest_path}\t{command_text}")
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

    for command_name, command_text in commands.items():
        print(f"{project.name}\t{project.root}\t{project.manifest_path}\t{command_name}\t{command_text}")
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


def test_command(test_config: TestConfig) -> str:
    if test_config.command is not None:
        return test_config.command
    if test_config.mise is not None:
        return shlex.join(["mise", "run", test_config.mise])
    raise ValueError("TestConfig must have command or mise set.")


class ProjectCommandError(RuntimeError):
    pass


def project_commands(manifest: BaseManifest) -> dict[str, str]:
    commands: dict[str, str] = {}
    if manifest.test is not None:
        commands["test"] = test_command(manifest.test)
    commands.update(manifest.commands)
    return commands


def project_command(manifest: BaseManifest, command_name: str) -> str:
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


class ProjectDiscoveryError(RuntimeError):
    pass


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


def workspace_project_statuses(workspace_root: Path) -> tuple[WorkspaceProjectStatus, ...]:
    return tuple(workspace_project_status(entry) for entry in workspace_manifest_entries(workspace_root))


def workspace_project_status(entry: ManifestEntry) -> WorkspaceProjectStatus:
    root = entry.path.parent.resolve()
    try:
        manifest = read_manifest(entry.path)
    except ManifestError as exc:
        return WorkspaceProjectStatus(
            name=root.name,
            root=root,
            manifest_path=entry.path.resolve(),
            status="error",
            venv="unknown",
            manifest="invalid",
            issues=(str(exc),),
        )

    venv_dir = project_venv_dir(manifest.project_name)
    if project_venv_ready(venv_dir):
        return WorkspaceProjectStatus(
            name=manifest.project_name,
            root=root,
            manifest_path=entry.path.resolve(),
            status="ok",
            venv="ready",
            manifest="valid",
            issues=(),
        )

    return WorkspaceProjectStatus(
        name=manifest.project_name,
        root=root,
        manifest_path=entry.path.resolve(),
        status="warn",
        venv="missing",
        manifest="valid",
        issues=(f"project virtual environment missing at {venv_dir}",),
    )


def project_venv_dir(project_name: str) -> Path:
    return base_state_root() / project_name / ".venv"


def project_venv_ready(venv_dir: Path) -> bool:
    return (venv_dir / "bin" / "python").is_file()


def workspace_project_check_results(
    ctx: base_cli.Context,
    workspace_root: Path,
) -> tuple[WorkspaceProjectCheckResult, ...]:
    default_manifest = read_default_manifest(ctx)
    return tuple(
        workspace_project_check_result(entry, default_manifest)
        for entry in workspace_manifest_entries(workspace_root)
    )


def workspace_project_check_result(
    entry: ManifestEntry,
    default_manifest: BaseManifest,
) -> WorkspaceProjectCheckResult:
    root = entry.path.parent.resolve()
    manifest_path = entry.path.resolve()
    try:
        manifest = read_manifest(entry.path)
    except ManifestError as exc:
        checks = (invalid_manifest_check(str(exc)),)
        return WorkspaceProjectCheckResult(
            name=root.name,
            root=root,
            manifest_path=manifest_path,
            manifest="invalid",
            status="error",
            checks=checks,
        )

    checks = (project_venv_check(manifest.project_name),)
    if checks[0].ok:
        checks += manifest_checks(default_manifest, manifest)

    return WorkspaceProjectCheckResult(
        name=manifest.project_name,
        root=root,
        manifest_path=manifest_path,
        manifest="valid",
        status=checks_status(checks),
        checks=checks,
    )


def invalid_manifest_check(message: str) -> ArtifactCheck:
    return ArtifactCheck(
        name="project_manifest",
        ok=False,
        message=message,
        fix="Fix base_manifest.yaml syntax and schema.",
        status="error",
        finding_id="BASE-P002",
    )


def project_venv_check(project_name: str) -> ArtifactCheck:
    venv_dir = project_venv_dir(project_name)
    if project_venv_ready(venv_dir):
        return ArtifactCheck(
            name="project_virtualenv",
            ok=True,
            message=f"Project virtual environment is ready at '{venv_dir}'.",
            fix="",
            finding_id="BASE-P050",
        )

    return ArtifactCheck(
        name="project_virtualenv",
        ok=False,
        message=f"Project virtual environment is missing or incomplete at '{venv_dir}'.",
        fix=f"Run 'basectl setup {project_name} --recreate-venv' to recreate the project virtual environment.",
        status="error",
        finding_id="BASE-P050",
    )


def checks_status(checks: tuple[ArtifactCheck, ...]) -> str:
    statuses = tuple(doctor_status(check) for check in checks)
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


def workspace_error_count(results: tuple[WorkspaceProjectCheckResult, ...]) -> int:
    return sum(1 for result in results for check in result.checks if doctor_status(check) == "error")


def workspace_status_to_json(workspace_root: Path, statuses: tuple[WorkspaceProjectStatus, ...]) -> dict[str, Any]:
    return {
        "workspace": str(workspace_root),
        "project_count": len(statuses),
        "projects": [
            {
                "name": status.name,
                "status": status.status,
                "path": str(status.root),
                "manifest_path": str(status.manifest_path),
                "venv": status.venv,
                "manifest": status.manifest,
                "issues": list(status.issues),
            }
            for status in statuses
        ],
    }


def workspace_check_to_json(workspace_root: Path, results: tuple[WorkspaceProjectCheckResult, ...]) -> dict[str, Any]:
    return workspace_checks_to_json(workspace_root, results, doctor=False)


def workspace_doctor_to_json(workspace_root: Path, results: tuple[WorkspaceProjectCheckResult, ...]) -> dict[str, Any]:
    return workspace_checks_to_json(workspace_root, results, doctor=True)


def workspace_checks_to_json(
    workspace_root: Path,
    results: tuple[WorkspaceProjectCheckResult, ...],
    doctor: bool,
) -> dict[str, Any]:
    return {
        "workspace": str(workspace_root),
        "status": checks_status(tuple(check for result in results for check in result.checks)),
        "project_count": len(results),
        "projects": [
            {
                "name": result.name,
                "status": result.status,
                "path": str(result.root),
                "manifest_path": str(result.manifest_path),
                "manifest": result.manifest,
                "checks": [workspace_check_item_to_json(check, doctor) for check in result.checks],
            }
            for result in results
        ],
    }


def workspace_check_item_to_json(check: ArtifactCheck, doctor: bool) -> dict[str, str | bool]:
    if doctor:
        return check_to_doctor_json(check)
    payload = check_to_json(check)
    payload["id"] = check.finding_id
    payload["status"] = doctor_status(check)
    return payload


def print_workspace_status(workspace_root: Path, statuses: tuple[WorkspaceProjectStatus, ...]) -> None:
    print(f"Workspace: {workspace_root} ({len(statuses)} projects)")
    print()
    if not statuses:
        print("No Base-managed projects discovered.")
        return

    print(f"{'PROJECT':<20} {'STATUS':<6} {'VENV':<8} {'MANIFEST':<8} {'LAST CHECK':<10} PATH")
    for status in statuses:
        print(
            f"{status.name:<20} "
            f"{status.status:<6} "
            f"{status.venv:<8} "
            f"{status.manifest:<8} "
            f"{'-':<10} "
            f"{status.root}"
        )

    attention_count = sum(1 for status in statuses if status.status != "ok")
    if attention_count:
        print(f"\n{attention_count} project(s) need attention. Run 'basectl doctor <project>' for details.")
    else:
        print("\nAll discovered projects look ok.")


def print_workspace_check(workspace_root: Path, results: tuple[WorkspaceProjectCheckResult, ...]) -> None:
    print(f"Workspace check: {workspace_root} ({len(results)} projects)")
    print_workspace_check_results(results)


def print_workspace_doctor(workspace_root: Path, results: tuple[WorkspaceProjectCheckResult, ...]) -> None:
    print(f"\nWorkspace doctor: {workspace_root} ({len(results)} projects)")
    print_workspace_check_results(results)


def print_workspace_check_results(results: tuple[WorkspaceProjectCheckResult, ...]) -> None:
    if not results:
        print("\nNo Base-managed projects discovered.")
        return

    for result in results:
        print(f"\nProject: {result.name} [{result.status}]")
        print(f"Path: {result.root}")
        for check in result.checks:
            print_doctor_finding(doctor_status(check), check.finding_id, check.name, check.message, check.fix)

    error_count = workspace_error_count(results)
    if error_count:
        print(f"\nWorkspace has {error_count} error finding(s).")
        return

    warn_count = sum(1 for result in results for check in result.checks if doctor_status(check) == "warn")
    if warn_count:
        print(f"\nWorkspace has {warn_count} warning finding(s).")
    else:
        print("\nAll discovered projects passed.")


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


def workspace_manifest_entries(workspace_root: Path) -> tuple[ManifestEntry, ...]:
    if not workspace_root.is_dir():
        raise ProjectDiscoveryError(f"Workspace '{workspace_root}' is not a directory.")

    entries: list[ManifestEntry] = []
    for candidate in sorted(workspace_root.iterdir(), key=lambda path: path.name):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "base_manifest.yaml"
        if not manifest_path.is_file():
            continue
        stat_result = manifest_path.stat()
        entries.append(
            ManifestEntry(
                path=manifest_path,
                mtime_ns=stat_result.st_mtime_ns,
                size=stat_result.st_size,
            )
        )

    return tuple(entries)


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
