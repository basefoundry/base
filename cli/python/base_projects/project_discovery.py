from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base_cli
from base_cli_adapters.paths import base_cache_root, discover_manifest
from base_projects.workspace_scanner import ManifestEntry
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_projects.workspace_scanner import ProjectNotFoundError
from base_projects.workspace_scanner import workspace_manifest_entries
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.manifest_schema import COMMAND_NAME_RE


@dataclass(frozen=True, order=True)
class Project:
    name: str
    root: Path
    manifest_path: Path


def current_project() -> Project:
    manifest_path = discover_manifest(Path.cwd())
    if manifest_path is None:
        raise ProjectDiscoveryError(f"No base_manifest.yaml found from '{Path.cwd()}' upward.")

    return read_project(manifest_path)


def discover_projects_cached(ctx: base_cli.Context, workspace_root: Path) -> tuple[Project, ...]:
    start = time.perf_counter()
    entries = workspace_manifest_entries(workspace_root, include_outside=False)
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
    if not ctx.dry_run:
        write_project_cache(workspace_root, entries, projects, ctx)
    elapsed_ms = (time.perf_counter() - start) * 1000
    ctx.log.debug(
        "Project discovery scanned '%s': %d project(s) in %.1fms.",
        workspace_root,
        len(projects),
        elapsed_ms,
    )
    return projects


def find_project_in_projects(projects: tuple[Project, ...], workspace_root: Path, project_name: str) -> Project:
    for project in projects:
        if project.name == project_name:
            return project
    raise ProjectNotFoundError(f"Project '{project_name}' was not found in workspace '{workspace_root}'.")


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
    return base_cache_root() / "base" / "cache" / "discovery" / f"{workspace_key}.json"


def read_project_cache(workspace_root: Path, entries: tuple[ManifestEntry, ...]) -> tuple[Project, ...] | None:
    cache_path = project_cache_path(workspace_root)
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("version"), int) or isinstance(data.get("version"), bool)
    ):
        return None
    if (
        data.get("version") != 1 or data.get("workspace") != str(workspace_root)
        or data.get("manifests") != [manifest_entry_to_json(entry) for entry in entries]
    ):
        return None

    records = data.get("projects")
    if not isinstance(records, list) or len(records) != len(entries):
        return None
    try:
        projects = tuple(project_from_cache_record(record) for record in records)
        expected_paths = {entry.path.resolve() for entry in entries}
        if {project.manifest_path for project in projects} != expected_paths:
            raise ValueError("Cached projects do not match discovered manifests.")
        return validate_unique_project_names(tuple(sorted(projects)))
    except (KeyError, TypeError, ValueError, ProjectDiscoveryError, OSError):
        return None


def project_from_cache_record(record: Any) -> Project:
    if not isinstance(record, dict):
        raise ValueError("Cached project must be an object.")
    name, root, manifest_path = (record.get(key) for key in ("name", "root", "manifest_path"))
    if not isinstance(name, str) or not COMMAND_NAME_RE.fullmatch(name):
        raise ValueError("Cached project name is invalid.")
    if not all(isinstance(value, str) and value and "\0" not in value for value in (root, manifest_path)):
        raise ValueError("Cached project paths are invalid.")
    root_path, manifest = Path(root), Path(manifest_path)
    if not root_path.is_absolute() or not manifest.is_absolute() or manifest.parent != root_path:
        raise ValueError("Cached project paths do not describe a project root and manifest.")
    return Project(name=name, root=root_path, manifest_path=manifest)


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
