from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.paths import discover_manifest
from base_setup.manifest import ManifestError, TestConfig, read_manifest


app = base_cli.App(name="base_projects")


@dataclass(frozen=True, order=True)
class Project:
    name: str
    root: Path
    manifest_path: Path


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("command", required=False)
@base_cli.argument("project", required=False)
@base_cli.option("--workspace", help="Workspace directory to scan. Defaults to BASE_HOME's parent.")
@base_cli.option("--format", "output_format", default="text", help="Output format for list: text or json.")
def run(
    ctx: base_cli.Context,
    command: str | None,
    project: str | None,
    workspace: str | None,
    output_format: str,
) -> int:
    if command in (None, "list"):
        return list_projects_command(ctx, workspace, output_format)
    if command == "current":
        return current_project_command(ctx)
    if command == "manifest":
        return manifest_project_command(ctx, project)
    if command == "resolve":
        return resolve_project_command(ctx, project, workspace)
    if command == "test-command":
        return test_command_project_command(ctx, project, workspace)

    ctx.log.error(
        "Unknown projects command '%s'. Supported commands: list, current, manifest, resolve, test-command.",
        command,
    )
    return 2


def list_projects_command(ctx: base_cli.Context, workspace: str | None, output_format: str = "text") -> int:
    if output_format not in ("text", "json"):
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        projects = discover_projects(workspace_root)
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
    if ctx.base_home is None:
        raise ProjectDiscoveryError("BASE_HOME is required to discover workspace projects.")
    return ctx.base_home.parent.resolve()


def resolve_named_project(ctx: base_cli.Context, project_name: str, workspace: str | None) -> Project:
    if workspace is None and project_name == "base" and ctx.base_home is not None:
        return read_project(ctx.base_home / "base_manifest.yaml")

    workspace_root = resolve_workspace_root(ctx, workspace)
    return find_project(workspace_root, project_name)


def discover_projects(workspace_root: Path) -> tuple[Project, ...]:
    if not workspace_root.is_dir():
        raise ProjectDiscoveryError(f"Workspace '{workspace_root}' is not a directory.")

    projects = []
    for candidate in sorted(workspace_root.iterdir(), key=lambda path: path.name):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "base_manifest.yaml"
        if not manifest_path.is_file():
            continue
        projects.append(read_project(manifest_path))

    return validate_unique_project_names(tuple(sorted(projects)))


def find_project(workspace_root: Path, project_name: str) -> Project:
    projects = discover_projects(workspace_root)
    for project in projects:
        if project.name == project_name:
            return project
    raise ProjectDiscoveryError(f"Project '{project_name}' was not found in workspace '{workspace_root}'.")


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
