from __future__ import annotations

from pathlib import Path

import base_cli
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import read_workspace_manifest
from base_projects.workspace_errors import ProjectDiscoveryError


class WorkspacePathOutsideRootError(ValueError):
    """Raised when a manifest repository resolves outside its workspace."""


def resolve_workspace_root(ctx: base_cli.Context, workspace: str | None) -> Path:
    if workspace:
        return Path(workspace).expanduser().resolve()
    if ctx.workspace_root is not None:
        return ctx.workspace_root
    if ctx.application_home is None:
        raise ProjectDiscoveryError("BASE_HOME is required to discover workspace projects.")
    return ctx.application_home.parent.resolve()


def resolve_workspace_repo_root(workspace_root: Path, repo_name: str) -> Path:
    """Resolve a manifest repository path while enforcing the workspace boundary."""
    resolved_workspace_root = workspace_root.expanduser().resolve(strict=False)
    resolved_repo_root = (resolved_workspace_root / repo_name).resolve(strict=False)
    try:
        resolved_repo_root.relative_to(resolved_workspace_root)
    except ValueError as exc:
        raise WorkspacePathOutsideRootError(
            f"Repository '{repo_name}' resolves outside workspace root '{resolved_workspace_root}'"
        ) from exc
    return resolved_repo_root


def effective_workspace_manifest(ctx: base_cli.Context, workspace_manifest: str | None) -> str | None:
    if workspace_manifest is not None:
        return workspace_manifest
    configured_manifest = ctx.user_config.workspace.manifest
    if configured_manifest is None:
        return None
    return str(configured_manifest)


def resolve_workspace_manifest(workspace_manifest: str | None) -> WorkspaceManifest | None:
    if workspace_manifest is None:
        return None
    return read_workspace_manifest(Path(workspace_manifest))
