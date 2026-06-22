from __future__ import annotations

import configparser
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import base_cli
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_reports import ProjectDiscoveryError
from base_projects.workspace_reports import resolve_workspace_manifest
from base_projects.workspace_reports import workspace_manifest_entries


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
        return 2

    try:
        workspace_root = resolve_workspace_root(ctx, options.workspace)
        manifest = resolve_workspace_manifest(effective_workspace_manifest(ctx, options.workspace_manifest))
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return 1

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
        return 1

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
    return 1 if counts.failed else 0


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
    if status == 0:
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
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        ctx.log.error("Could not run basectl repo configure for repository '%s': %s", target.name, exc)
        return 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0:
        return 0

    ctx.log.error("Configure failed for repository '%s'.", target.name)
    return 1


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
        )
    except OSError:
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


def github_repo_spec(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme and parsed.hostname == "github.com":
        return github_repo_spec_from_path(parsed.path)

    git_ssh_prefix = "git@github.com:"
    if url.startswith(git_ssh_prefix):
        return github_repo_spec_from_path(url[len(git_ssh_prefix) :])

    return None


def github_repo_spec_from_path(path: str) -> str | None:
    normalized = path.strip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    parts = normalized.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return f"{parts[0]}/{parts[1]}"
