from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import base_cli
from base_cli.config import load_user_config
from base_cli.config import user_config_path
from base_projects.command_helpers import ProjectCommandError as ProjectRunnerError
from base_projects.command_helpers import ProjectUsageError
from base_projects.command_helpers import github_repo_spec
from base_projects.command_helpers import run_project_command
from base_projects.command_helpers import write_project_command_output
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_scanner import ProjectDiscoveryError


class WorkspaceInitOptions(Protocol):
    workspace: str | None
    output_format: str
    workspace_manifest: str | None
    workspace_config_path: str | None
    workspace_owner: str | None
    include_optional: bool
    dry_run: bool


@dataclass(frozen=True)
class WorkspaceInitSource:
    display: str
    repo_spec: str | None = None
    repo_name: str | None = None
    local_path: Path | None = None


def workspace_init_command(
    ctx: base_cli.Context,
    workspace_source: str,
    options: WorkspaceInitOptions,
    *,
    workspace_clone_command: Callable[[base_cli.Context, Any], int],
) -> int:
    if options.output_format != "text":
        raise ProjectUsageError(f"Unsupported output format '{options.output_format}'. Expected: text.")

    try:
        source = resolve_workspace_init_source(ctx, workspace_source, options.workspace_owner)
        config_repo = resolve_workspace_config_repo_path(ctx, source, options)
        workspace_root = resolve_workspace_init_root(ctx, options.workspace, config_repo)
    except ProjectDiscoveryError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print("Workspace init")
    print(f"Workspace source: {source.display}")
    print(f"Workspace config repo: {config_repo}")
    print(f"Workspace root: {workspace_root}")

    try:
        if source.repo_spec is not None:
            clone_workspace_config_repo(ctx, source.repo_spec, config_repo, dry_run=options.dry_run)
        manifest_path = resolve_workspace_init_manifest_path(config_repo, options.workspace_manifest)
        if options.dry_run and source.repo_spec is not None and not manifest_path.is_file():
            print(f"[DRY-RUN] Would read workspace manifest: {manifest_path}")
            print("[DRY-RUN] Would update user config:")
            print(f"  workspace.root: {workspace_root}")
            print(f"  workspace.manifest: {manifest_path}")
            print("[DRY-RUN] Skipping member repository plan because the workspace config repo is not present.")
            return base_cli.ExitCode.SUCCESS
        manifest = resolve_workspace_manifest(str(manifest_path))
        if manifest is None:
            raise WorkspaceManifestError(f"{manifest_path}: workspace manifest is required.")
    except WorkspaceManifestError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    print(f"Workspace manifest: {manifest.path} ({manifest.name})")

    if options.dry_run:
        print("[DRY-RUN] Would update user config:")
        print(f"  workspace.root: {workspace_root}")
        print(f"  workspace.manifest: {manifest.path}")
    else:
        write_workspace_init_user_config(workspace_root, manifest.path)
        print(f"Updated user config: {user_config_path()}")

    clone_options = replace(
        options,
        workspace=str(workspace_root),
        output_format="text",
        workspace_manifest=str(manifest.path),
        include_optional=options.include_optional,
        dry_run=options.dry_run,
    )
    return workspace_clone_command(ctx, clone_options)


def resolve_workspace_init_source(
    ctx: base_cli.Context,
    workspace_source: str,
    owner: str | None,
) -> WorkspaceInitSource:
    source_path = Path(workspace_source).expanduser()
    if workspace_source.startswith("file://"):
        parsed = urlparse(workspace_source)
        return WorkspaceInitSource(
            display=workspace_source,
            local_path=Path(parsed.path).expanduser().resolve(strict=False),
        )
    if is_workspace_init_path_source(workspace_source) or source_path.exists():
        return WorkspaceInitSource(
            display=workspace_source,
            local_path=source_path.resolve(strict=False),
        )

    repo_spec = workspace_init_github_repo_spec(workspace_source)
    if repo_spec is not None:
        return WorkspaceInitSource(
            display=repo_spec,
            repo_spec=repo_spec,
            repo_name=repo_spec.split("/", 1)[1],
        )

    if "/" in workspace_source:
        raise ProjectUsageError(
            "Workspace source must be a local path, GitHub URL, "
            "'<owner>/<repo>', or short repo name."
        )

    effective_owner = owner or ctx.user_config.github.default_owner
    if effective_owner is None:
        raise ProjectUsageError(
            "Workspace source owner is required for short repo names. "
            "Pass --owner <owner> or set github.default_owner in ~/.base.d/config.yaml."
        )
    repo_spec = f"{effective_owner}/{workspace_source}"
    return WorkspaceInitSource(display=repo_spec, repo_spec=repo_spec, repo_name=workspace_source)


def is_workspace_init_path_source(workspace_source: str) -> bool:
    return workspace_source.startswith(("/", "./", "../", "~"))


def workspace_init_github_repo_spec(workspace_source: str) -> str | None:
    return github_repo_spec(workspace_source, allow_path=True)


def resolve_workspace_config_repo_path(
    ctx: base_cli.Context,
    source: WorkspaceInitSource,
    options: WorkspaceInitOptions,
) -> Path:
    if options.workspace_config_path is not None:
        return Path(options.workspace_config_path).expanduser().resolve(strict=False)
    if source.local_path is not None:
        return source.local_path
    workspace_root = resolve_workspace_init_root(ctx, options.workspace, None)
    if source.repo_name is None:
        raise ValueError("Workspace init source must include repo_name when resolving a repo path.")
    return (workspace_root / source.repo_name).resolve(strict=False)


def resolve_workspace_init_manifest_path(config_repo: Path, workspace_manifest: str | None) -> Path:
    if workspace_manifest is None:
        return (config_repo / "workspace.yaml").resolve(strict=False)
    manifest_path = Path(workspace_manifest).expanduser()
    if manifest_path.is_absolute():
        return manifest_path.resolve(strict=False)
    return (config_repo / manifest_path).resolve(strict=False)


def resolve_workspace_init_root(ctx: base_cli.Context, workspace: str | None, config_repo: Path | None) -> Path:
    if workspace is not None:
        return Path(workspace).expanduser().resolve(strict=False)
    if ctx.workspace_root is not None:
        return ctx.workspace_root
    if config_repo is None:
        if ctx.base_home is None:
            raise ProjectDiscoveryError("BASE_HOME is required to resolve the default workspace root.")
        return ctx.base_home.parent.resolve(strict=False)
    return config_repo.parent.resolve(strict=False)


def clone_workspace_config_repo(ctx: base_cli.Context, repo_spec: str, target: Path, *, dry_run: bool) -> None:
    if ctx.base_home is None:
        raise WorkspaceManifestError("BASE_HOME is required to clone the workspace configuration repository.")
    basectl = ctx.base_home / "bin" / "basectl"
    command = [str(basectl), "repo", "clone", repo_spec, "--path", str(target)]
    if dry_run:
        command.append("--dry-run")
    try:
        result = run_project_command(
            command,
            error_context=f"basectl repo clone for workspace source '{repo_spec}'",
        )
    except ProjectRunnerError as exc:
        raise WorkspaceManifestError(str(exc)) from exc
    write_project_command_output(result)
    if result.returncode != 0:
        raise WorkspaceManifestError(f"Workspace source clone failed for '{repo_spec}'.")


def write_workspace_init_user_config(workspace_root: Path, manifest_path: Path) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise WorkspaceManifestError(
            "PyYAML is required to update ~/.base.d/config.yaml. "
            "Run 'basectl setup' to install Base Python bootstrap dependencies."
        ) from exc

    config_path = user_config_path()
    raw_config = load_user_config()
    workspace_config = dict(raw_config.get("workspace") or {})
    workspace_config["root"] = str(workspace_root)
    workspace_config["manifest"] = str(manifest_path)
    raw_config["workspace"] = workspace_config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(raw_config, sort_keys=False), encoding="utf-8")
