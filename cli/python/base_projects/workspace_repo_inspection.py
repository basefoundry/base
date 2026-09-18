from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import BaseManifest

from . import workspace_context
from .workspace_context import WorkspacePathOutsideRootError
from .workspace_manifest import WorkspaceManifestRepo


WorkspaceRepoInspectionState = Literal[
    "outside_workspace",
    "missing_repository",
    "missing_manifest",
    "invalid_manifest",
    "inspected",
]


@dataclass(frozen=True)
class WorkspaceRepoInspection:
    name: str
    root: Path
    manifest_path: Path | None
    project_name: str | None
    manifest: BaseManifest | None
    state: WorkspaceRepoInspectionState
    reason: str | None
    required: bool
    fatal: bool


def inspect_workspace_repo(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
) -> WorkspaceRepoInspection:
    try:
        root = workspace_context.resolve_workspace_repo_root(workspace_root, repo.name)
    except WorkspacePathOutsideRootError as exc:
        return WorkspaceRepoInspection(
            name=repo.name,
            root=workspace_root / repo.name,
            manifest_path=None,
            project_name=None,
            manifest=None,
            state="outside_workspace",
            reason=str(exc),
            required=repo.required,
            fatal=True,
        )

    if not root.is_dir():
        return WorkspaceRepoInspection(
            name=repo.name,
            root=root,
            manifest_path=None,
            project_name=None,
            manifest=None,
            state="missing_repository",
            reason=f"repository is missing at '{root}'",
            required=repo.required,
            fatal=repo.required,
        )

    manifest_path = root / "base_manifest.yaml"
    if not manifest_path.is_file():
        return WorkspaceRepoInspection(
            name=repo.name,
            root=root,
            manifest_path=None,
            project_name=None,
            manifest=None,
            state="missing_manifest",
            reason="repository does not contain base_manifest.yaml",
            required=repo.required,
            fatal=False,
        )

    try:
        manifest = read_manifest(manifest_path)
    except ManifestError as exc:
        return WorkspaceRepoInspection(
            name=repo.name,
            root=root,
            manifest_path=manifest_path.resolve(),
            project_name=None,
            manifest=None,
            state="invalid_manifest",
            reason=f"base_manifest.yaml is invalid: {exc}",
            required=repo.required,
            fatal=repo.required,
        )

    return WorkspaceRepoInspection(
        name=repo.name,
        root=root,
        manifest_path=manifest_path.resolve(),
        project_name=manifest.project_name,
        manifest=manifest,
        state="inspected",
        reason=None,
        required=repo.required,
        fatal=False,
    )
