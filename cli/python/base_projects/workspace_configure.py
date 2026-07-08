from __future__ import annotations

import configparser
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base_cli
from base_projects import workspace_context
from base_projects.command_helpers import github_repo_spec
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_projects.workspace_scanner import workspace_manifest_entries

GIT_CONFIG_TIMEOUT_SECONDS = 10
WORKSPACE_CONFIGURE_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class WorkspaceConfigureTarget:
    name: str
    root: Path
    repo_spec: str | None
    skip_reason: str | None = None


@dataclass(frozen=True)
class WorkspaceConfigureCounts:
    configured: int = 0
    skipped: int = 0
    failed: int = 0


def workspace_configure_from_options(
    ctx: base_cli.Context,
    options: Any,
) -> int:
    if options.output_format != "text":
        ctx.log.error("Unsupported output format '%s'. Expected: text.", options.output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = workspace_context.resolve_workspace_root(ctx, options.workspace)
        manifest = resolve_workspace_manifest(
            workspace_context.effective_workspace_manifest(ctx, options.workspace_manifest)
        )
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    return workspace_configure_command(ctx, workspace_root, manifest, dry_run=options.dry_run)


def workspace_configure_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest | None,
    *,
    dry_run: bool,
) -> int:
    if ctx.base_home is None:
        ctx.log.error("BASE_HOME is required to configure workspace repositories.")
        return base_cli.ExitCode.FAILURE

    basectl = ctx.base_home / "bin" / "basectl"
    targets = workspace_configure_targets(workspace_root, workspace_manifest)
    print_workspace_configure_header(workspace_root, workspace_manifest, len(targets))

    counts = WorkspaceConfigureCounts()
    for target in targets:
        counts = configure_workspace_target(ctx, basectl, target, counts, dry_run=dry_run)

    if dry_run:
        print("[DRY-RUN] No repositories were modified.")

    print(
        "Workspace configure completed: "
        f"configured={counts.configured} skipped={counts.skipped} failed={counts.failed}."
    )
    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def workspace_configure_targets(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest | None,
) -> tuple[WorkspaceConfigureTarget, ...]:
    if workspace_manifest is not None:
        return tuple(workspace_configure_manifest_target(workspace_root, repo) for repo in workspace_manifest.repos)

    targets: list[WorkspaceConfigureTarget] = []
    for entry in workspace_manifest_entries(workspace_root):
        root = entry.path.parent.resolve()
        targets.append(
            WorkspaceConfigureTarget(
                name=root.name,
                root=root,
                repo_spec=github_origin_repo_spec(root),
            )
        )
    return tuple(targets)


def workspace_configure_manifest_target(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
) -> WorkspaceConfigureTarget:
    root = (workspace_root / repo.name).resolve()
    if not root.exists():
        return WorkspaceConfigureTarget(
            name=repo.name,
            root=root,
            repo_spec=None,
            skip_reason=f"repository '{repo.name}' is missing at '{root}'",
        )
    if not (root / "base_manifest.yaml").is_file():
        return WorkspaceConfigureTarget(
            name=repo.name,
            root=root,
            repo_spec=None,
            skip_reason=f"repository '{repo.name}' does not contain base_manifest.yaml",
        )

    return WorkspaceConfigureTarget(
        name=repo.name,
        root=root,
        repo_spec=workspace_manifest_repo_spec(repo) or github_origin_repo_spec(root),
    )


def configure_workspace_target(
    ctx: base_cli.Context,
    basectl: Path,
    target: WorkspaceConfigureTarget,
    counts: WorkspaceConfigureCounts,
    *,
    dry_run: bool,
) -> WorkspaceConfigureCounts:
    if target.skip_reason is not None:
        print(f"SKIP {target.skip_reason}.")
        return WorkspaceConfigureCounts(counts.configured, counts.skipped + 1, counts.failed)
    if target.repo_spec is None:
        print(f"SKIP repository '{target.name}' has no supported GitHub origin remote.")
        return WorkspaceConfigureCounts(counts.configured, counts.skipped + 1, counts.failed)

    print(f"CONFIGURE repository '{target.name}' at '{target.root}' for '{target.repo_spec}'.")
    status = configure_workspace_repo(ctx, basectl, target, dry_run=dry_run)
    if status == base_cli.ExitCode.SUCCESS:
        return WorkspaceConfigureCounts(counts.configured + 1, counts.skipped, counts.failed)
    return WorkspaceConfigureCounts(counts.configured, counts.skipped, counts.failed + 1)


def configure_workspace_repo(
    ctx: base_cli.Context,
    basectl: Path,
    target: WorkspaceConfigureTarget,
    *,
    dry_run: bool,
) -> int:
    command = [str(basectl), "repo", "configure", str(target.root), "--repo", str(target.repo_spec)]
    if dry_run:
        command.append("--dry-run")

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=WORKSPACE_CONFIGURE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        timeout = exc.timeout if exc.timeout is not None else WORKSPACE_CONFIGURE_TIMEOUT_SECONDS
        ctx.log.error(
            "Timed out running basectl repo configure for repository '%s' after %s seconds.",
            target.name,
            timeout,
        )
        return base_cli.ExitCode.FAILURE
    except OSError as exc:
        ctx.log.error("Could not run basectl repo configure for repository '%s': %s", target.name, exc)
        return base_cli.ExitCode.FAILURE

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0:
        return base_cli.ExitCode.SUCCESS

    ctx.log.error("Configure failed for repository '%s'.", target.name)
    return base_cli.ExitCode.FAILURE


def print_workspace_configure_header(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest | None,
    target_count: int,
) -> None:
    if workspace_manifest is None:
        print(f"Workspace configure: {workspace_root} ({target_count} discovered project(s))")
        return

    print(f"Workspace configure: {workspace_root} ({target_count} manifest repos)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")


def workspace_manifest_repo_spec(repo: WorkspaceManifestRepo) -> str | None:
    if repo.url is None:
        return None
    return github_repo_spec(repo.url)


def github_origin_repo_spec(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            check=False,
            capture_output=True,
            text=True,
            timeout=GIT_CONFIG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        origin_url = git_config_origin_url(root)
        return github_repo_spec(origin_url) if origin_url else None
    if result.returncode != 0:
        origin_url = git_config_origin_url(root)
        return github_repo_spec(origin_url) if origin_url else None
    return github_repo_spec(result.stdout.strip())


def git_config_origin_url(root: Path) -> str | None:
    config_path = root / ".git" / "config"
    if not config_path.is_file():
        return None
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error:
        return None
    section = 'remote "origin"'
    if not parser.has_option(section, "url"):
        return None
    return parser.get(section, "url").strip()
