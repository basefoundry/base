from __future__ import annotations

from pathlib import Path
from typing import Protocol

import base_cli
from base_projects.command_helpers import ProjectCommandError as ProjectRunnerError
from base_projects.command_helpers import ProjectUsageError
from base_projects.command_helpers import github_repo_spec
from base_projects.command_helpers import run_project_command
from base_projects.command_helpers import write_project_command_output
from base_projects.workspace_context import effective_workspace_manifest
from base_projects.workspace_context import resolve_workspace_root
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_reports import resolve_workspace_manifest
from base_projects.workspace_scanner import ProjectDiscoveryError


class WorkspaceCloneOptions(Protocol):
    workspace: str | None
    output_format: str
    workspace_manifest: str | None
    include_optional: bool
    dry_run: bool


def workspace_clone_command(ctx: base_cli.Context, options: WorkspaceCloneOptions) -> int:
    if options.output_format != "text":
        raise ProjectUsageError(f"Unsupported output format '{options.output_format}'. Expected: text.")

    try:
        workspace_root = resolve_workspace_root(ctx, options.workspace)
        manifest = require_workspace_clone_manifest(ctx, options.workspace_manifest)
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if ctx.base_home is None:
        ctx.log.error("BASE_HOME is required to clone workspace repositories.")
        return base_cli.ExitCode.FAILURE

    basectl = ctx.base_home / "bin" / "basectl"
    print(f"Workspace clone: {workspace_root} ({len(manifest.repos)} repositories)")
    print(f"Workspace manifest: {manifest.path} ({manifest.name})")

    errors = 0
    for repo in manifest.repos:
        target = (workspace_root / repo.name).resolve()
        required_label = "required" if repo.required else "optional"
        if should_skip_optional_clone(repo, target, options.include_optional):
            print_optional_clone_skip(repo, target)
            continue

        verb = "CHECK" if target.exists() else "CLONE"
        preposition = "at" if target.exists() else "into"
        print(f"{verb} {required_label} repository '{repo.name}' {preposition} '{target}'.")
        errors += clone_workspace_repo(ctx, basectl, repo, target, dry_run=options.dry_run)

    if errors:
        print(f"Workspace clone completed with {errors} error(s).")
        return base_cli.ExitCode.FAILURE

    print("Workspace clone completed.")
    return base_cli.ExitCode.SUCCESS


def require_workspace_clone_manifest(ctx: base_cli.Context, workspace_manifest: str | None) -> WorkspaceManifest:
    effective_manifest = effective_workspace_manifest(ctx, workspace_manifest)
    if effective_manifest is None:
        raise ProjectUsageError("workspace clone requires --manifest <path>.")
    manifest = resolve_workspace_manifest(effective_manifest)
    if manifest is None:
        raise ProjectUsageError("workspace clone requires --manifest <path>.")
    return manifest


def should_skip_optional_clone(repo: WorkspaceManifestRepo, target: Path, include_optional: bool) -> bool:
    return not repo.required and not include_optional and not target.exists()


def print_optional_clone_skip(repo: WorkspaceManifestRepo, target: Path) -> None:
    print(
        f"SKIP optional repository '{repo.name}' is missing at '{target}'. "
        "Pass --include-optional to clone it."
    )


def clone_workspace_repo(
    ctx: base_cli.Context,
    basectl: Path,
    repo: WorkspaceManifestRepo,
    target: Path,
    *,
    dry_run: bool,
) -> int:
    repo_spec = workspace_clone_repo_spec(repo)
    if repo_spec is None:
        ctx.log.error(
            "Repository '%s' has unsupported clone URL '%s'. Only github.com repository URLs are supported.",
            repo.name,
            repo.url,
        )
        return base_cli.ExitCode.FAILURE

    command = [str(basectl), "repo", "clone", repo_spec, "--path", str(target)]
    if dry_run:
        command.append("--dry-run")

    try:
        result = run_project_command(
            command,
            error_context=f"basectl repo clone for repository '{repo.name}'",
        )
    except ProjectRunnerError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    write_project_command_output(result)
    if result.returncode == 0:
        return base_cli.ExitCode.SUCCESS

    ctx.log.error("Clone failed for repository '%s'.", repo.name)
    return base_cli.ExitCode.FAILURE


def workspace_clone_repo_spec(repo: WorkspaceManifestRepo) -> str | None:
    if repo.url is None:
        return repo.name

    return github_repo_spec(repo.url)
