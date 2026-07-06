from __future__ import annotations

from pathlib import Path

import base_cli
from base_projects.workspace_scanner import ProjectDiscoveryError


def resolve_workspace_root(ctx: base_cli.Context, workspace: str | None) -> Path:
    if workspace:
        return Path(workspace).expanduser().resolve()
    if ctx.workspace_root is not None:
        return ctx.workspace_root
    if ctx.base_home is None:
        raise ProjectDiscoveryError("BASE_HOME is required to discover workspace projects.")
    return ctx.base_home.parent.resolve()


def effective_workspace_manifest(ctx: base_cli.Context, workspace_manifest: str | None) -> str | None:
    if workspace_manifest is not None:
        return workspace_manifest
    configured_manifest = ctx.user_config.workspace.manifest
    if configured_manifest is None:
        return None
    return str(configured_manifest)
