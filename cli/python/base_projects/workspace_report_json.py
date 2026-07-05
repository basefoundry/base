from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from base_projects.workspace_manifest import WorkspaceManifest
from base_setup.checks import ArtifactCheck
from base_setup.checks import DIAGNOSTIC_JSON_SCHEMA_VERSION
from base_setup.checks import check_to_json
from base_setup.checks import checks_status


def workspace_status_to_json(
    workspace_root: Path,
    statuses: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workspace": str(workspace_root),
        "project_count": workspace_project_count(statuses, workspace_manifest),
        "projects": [workspace_status_item_to_json(status, workspace_manifest) for status in statuses],
    }
    add_workspace_manifest_json(payload, statuses, workspace_manifest)
    return payload


def workspace_status_item_to_json(
    status: Any,
    workspace_manifest: WorkspaceManifest | None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": status.name,
        "status": status.status,
        "path": str(status.root),
        "manifest_path": str(status.manifest_path) if status.manifest_path is not None else None,
        "venv": status.venv,
        "manifest": status.manifest,
        "last_check": last_check_to_json(status.last_check),
        "issues": list(status.issues),
    }
    if workspace_manifest is not None:
        item.update(workspace_manifest_item_metadata(status))
    if status.python_runtime is not None:
        item["python_runtime"] = status.python_runtime.to_json()
    return item


def workspace_check_to_json(
    workspace_root: Path,
    results: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    return workspace_checks_to_json(workspace_root, results, workspace_manifest=workspace_manifest)


def workspace_doctor_to_json(
    workspace_root: Path,
    results: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    return workspace_checks_to_json(workspace_root, results, workspace_manifest=workspace_manifest)


def workspace_checks_to_json(
    workspace_root: Path,
    results: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "workspace": str(workspace_root),
        "status": checks_status(tuple(check for result in results for check in result.checks)),
        "project_count": workspace_project_count(results, workspace_manifest),
        "projects": [workspace_check_result_to_json(result, workspace_manifest) for result in results],
    }
    add_workspace_manifest_json(payload, results, workspace_manifest)
    return payload


def workspace_check_result_to_json(
    result: Any,
    workspace_manifest: WorkspaceManifest | None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": result.name,
        "status": result.status,
        "path": str(result.root),
        "manifest_path": str(result.manifest_path) if result.manifest_path is not None else None,
        "manifest": result.manifest,
        "checks": [workspace_check_item_to_json(check) for check in result.checks],
    }
    if workspace_manifest is not None:
        item.update(workspace_manifest_item_metadata(result))
    return item


def workspace_manifest_item_metadata(item: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "repository": item.repository or item.root.name,
        "expected": item.expected,
        "required": item.required,
        "repo": item.repo,
    }
    if item.url is not None:
        metadata["url"] = item.url
    if item.default_branch is not None:
        metadata["default_branch"] = item.default_branch
    return metadata


def workspace_project_count(
    items: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None,
) -> int:
    if workspace_manifest is None:
        return len(items)
    return sum(1 for item in items if item.manifest in ("valid", "invalid"))


def add_workspace_manifest_json(
    payload: dict[str, Any],
    items: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None,
) -> None:
    if workspace_manifest is None:
        return
    payload["workspace_manifest"] = {
        "path": str(workspace_manifest.path),
        "name": workspace_manifest.name,
        "schema_version": workspace_manifest.schema_version,
    }
    payload["repository_count"] = len(items)


def workspace_check_item_to_json(check: ArtifactCheck) -> dict[str, Any]:
    return check_to_json(check)


def last_check_to_json(last_check: Any) -> dict[str, str] | None:
    if last_check is None:
        return None
    return {
        "checked_at": last_check.checked_at,
        "status": last_check.status,
    }


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2)
