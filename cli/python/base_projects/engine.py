from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.paths import discover_manifest
from base_setup.manifest import ManifestError, read_manifest


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
def run(ctx: base_cli.Context, command: str | None, project: str | None, workspace: str | None) -> int:
    if command in (None, "list"):
        return list_projects_command(ctx, workspace)
    if command == "current":
        return current_project_command(ctx)
    if command == "resolve":
        return resolve_project_command(ctx, project, workspace)

    ctx.log.error("Unknown projects command '%s'. Supported commands: list, current, resolve.", command)
    return 2


def list_projects_command(ctx: base_cli.Context, workspace: str | None) -> int:
    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        projects = discover_projects(workspace_root)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    for project in projects:
        print(f"{project.name}\t{project.root}")
    return 0


def resolve_project_command(ctx: base_cli.Context, project_name: str | None, workspace: str | None) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, workspace)
        project = find_project(workspace_root, project_name)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return 1

    print(f"{project.name}\t{project.root}\t{project.manifest_path}")
    return 0


def current_project_command(ctx: base_cli.Context) -> int:
    manifest_path = discover_manifest(Path.cwd())
    if manifest_path is None:
        ctx.log.error("No base_manifest.yaml found from '%s' upward.", Path.cwd())
        return 1

    try:
        project = read_project(manifest_path)
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
