from __future__ import annotations

from pathlib import Path
from typing import Protocol

import base_cli
from base_projects.command_helpers import ProjectUsageError
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_pull import pull_workspace_manifest


class WorkspacePullOptions(Protocol):
    output_format: str
    workspace_manifest: str | None
    workspace_manifest_source: str | None
    dry_run: bool


def workspace_pull_command(ctx: base_cli.Context, options: WorkspacePullOptions) -> int:
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
        return base_cli.ExitCode.FAILURE

    print("Workspace manifest pull")
    print(f"Source: {result.source}")
    print(f"Target: {result.target}")
    print(f"Manifest: {result.manifest.name} ({len(result.manifest.repos)} repositories)")
    print(f"Status: {result.status}")

    if options.dry_run:
        print("[DRY-RUN] No files changed.")
        return base_cli.ExitCode.SUCCESS

    if not result.changed:
        print("Workspace manifest already up to date.")
        return base_cli.ExitCode.SUCCESS

    print(f"Updated workspace manifest: {result.target}")
    return base_cli.ExitCode.SUCCESS


def effective_workspace_manifest_path(ctx: base_cli.Context, workspace_manifest: str | None) -> Path | None:
    if workspace_manifest is not None:
        return Path(workspace_manifest).expanduser().resolve(strict=False)
    configured_manifest = ctx.user_config.workspace.manifest
    if configured_manifest is None:
        return None
    return configured_manifest


def effective_workspace_manifest_source(ctx: base_cli.Context, workspace_manifest_source: str | None) -> str | None:
    if workspace_manifest_source is not None:
        return workspace_manifest_source
    return ctx.user_config.workspace.manifest_source
