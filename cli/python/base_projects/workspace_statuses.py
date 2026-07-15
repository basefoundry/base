from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path

from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_report_common import ProjectLastCheck
from base_projects.workspace_report_common import missing_repo_message
from base_projects.workspace_report_common import most_severe_status
from base_projects.workspace_report_common import project_last_check
from base_projects.workspace_report_common import project_venv_dir
from base_projects.workspace_report_common import project_venv_ready
from base_projects.workspace_scanner import ManifestEntry
from base_projects.workspace_scanner import workspace_manifest_entries
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.python_runtime import ProjectPythonRuntime
from base_setup.python_runtime import project_python_runtime


@dataclass(frozen=True)
class WorkspaceProjectStatus:
    name: str
    root: Path
    manifest_path: Path | None
    status: str
    venv: str
    manifest: str
    issues: tuple[str, ...]
    last_check: ProjectLastCheck | None = None
    expected: bool = False
    required: bool = False
    repo: str = "present"
    repository: str | None = None
    url: str | None = None
    default_branch: str | None = None
    python_runtime: ProjectPythonRuntime | None = None


def workspace_project_statuses(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest | None = None,
) -> tuple[WorkspaceProjectStatus, ...]:
    if workspace_manifest is None:
        return tuple(workspace_project_status(entry) for entry in workspace_manifest_entries(workspace_root))
    return workspace_manifest_project_statuses(workspace_root, workspace_manifest)


def workspace_manifest_project_statuses(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    *,
    probe_venv: bool = True,
) -> tuple[WorkspaceProjectStatus, ...]:
    entries_by_repo = {
        entry.path.parent.resolve().name: entry
        for entry in workspace_manifest_entries(workspace_root)
    }
    statuses: list[WorkspaceProjectStatus] = []

    for repo in workspace_manifest.repos:
        entry = entries_by_repo.pop(repo.name, None)
        statuses.append(workspace_expected_repo_status(workspace_root, repo, entry, probe_venv=probe_venv))

    for repo_name in sorted(entries_by_repo):
        statuses.append(workspace_extra_project_status(entries_by_repo[repo_name], probe_venv=probe_venv))

    return tuple(statuses)


def workspace_expected_repo_status(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
    entry: ManifestEntry | None,
    *,
    probe_venv: bool = True,
) -> WorkspaceProjectStatus:
    root = (workspace_root / repo.name).resolve()
    if entry is not None:
        status = workspace_project_status(entry, probe_venv=probe_venv)
        return attach_status_repo_metadata(status, repo)
    last_check = project_last_check(repo.name)
    if root.exists():
        return WorkspaceProjectStatus(
            name=repo.name,
            root=root,
            manifest_path=None,
            status="ok",
            venv="not_applicable",
            manifest="missing",
            issues=(),
            last_check=last_check,
            expected=True,
            required=repo.required,
            repo="present",
            repository=repo.name,
            url=repo.url,
            default_branch=repo.default_branch,
        )

    return WorkspaceProjectStatus(
        name=repo.name,
        root=root,
        manifest_path=None,
        status="error" if repo.required else "warn",
        venv="unknown",
        manifest="unknown",
        issues=(missing_repo_message(repo, root),),
        last_check=last_check,
        expected=True,
        required=repo.required,
        repo="missing",
        repository=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
    )


def attach_status_repo_metadata(
    status: WorkspaceProjectStatus,
    repo: WorkspaceManifestRepo,
) -> WorkspaceProjectStatus:
    return replace(
        status,
        expected=True,
        required=repo.required,
        repo="present",
        repository=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
    )


def workspace_extra_project_status(entry: ManifestEntry, *, probe_venv: bool = True) -> WorkspaceProjectStatus:
    status = workspace_project_status(entry, probe_venv=probe_venv)
    return replace(
        status,
        status=most_severe_status(status.status, "warn"),
        issues=status.issues + ("discovered Base-managed project is not listed in the workspace manifest",),
        expected=False,
        required=False,
        repo="present",
        repository=entry.path.parent.resolve().name,
    )


def workspace_project_status(entry: ManifestEntry, *, probe_venv: bool = True) -> WorkspaceProjectStatus:
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
            last_check=project_last_check(root.name),
        )

    last_check = project_last_check(manifest.project_name)
    venv_dir = project_venv_dir(manifest)
    if probe_venv:
        venv_ready = project_venv_ready(venv_dir)
        ready_label = "ready"
    else:
        venv_ready = executable_interpreter_present(venv_dir / "bin" / "python")
        ready_label = "present_unverified"
    if venv_ready:
        return WorkspaceProjectStatus(
            name=manifest.project_name,
            root=root,
            manifest_path=entry.path.resolve(),
            status="ok",
            venv=ready_label,
            manifest="valid",
            issues=(),
            last_check=last_check,
            python_runtime=project_python_runtime(manifest, venv_dir=venv_dir) if probe_venv else None,
        )

    return WorkspaceProjectStatus(
        name=manifest.project_name,
        root=root,
        manifest_path=entry.path.resolve(),
        status="warn",
        venv="missing",
        manifest="valid",
        issues=(f"project virtual environment missing at {venv_dir}",),
        last_check=last_check,
    )


def executable_interpreter_present(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False
