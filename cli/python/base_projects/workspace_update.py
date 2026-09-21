from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import base_cli
from base_projects import workspace_context
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_context import WorkspacePathOutsideRootError
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_scanner import ProjectDiscoveryError


WorkspaceUpdateAction = Literal["pull", "skip"]
WorkspaceUpdateStatus = Literal["planned", "updated", "unchanged", "skipped", "failed"]
WORKSPACE_UPDATE_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class WorkspaceUpdateTarget:
    name: str
    root: Path
    action: WorkspaceUpdateAction
    reason: str | None = None
    required: bool = True
    fatal: bool = False


@dataclass(frozen=True)
class WorkspaceUpdateCounts:
    planned: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass(frozen=True)
class WorkspaceUpdateResult:
    status: WorkspaceUpdateStatus
    detail: str | None = None
    exit_code: int | None = None


class WorkspaceUpdateSelectionError(ValueError):
    """Raised when --repos does not identify a valid manifest selection."""


def workspace_update_from_options(
    ctx: base_cli.Context,
    options: Any,
) -> int:
    output_format = str(getattr(options, "output_format", "text") or "text").lower()
    if output_format not in {"text", "json"}:
        ctx.log.error("Unsupported output format '%s'. Expected: text or json.", options.output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = workspace_context.resolve_workspace_root(ctx, options.workspace)
        manifest = resolve_workspace_manifest(
            workspace_context.effective_workspace_manifest(ctx, options.workspace_manifest)
        )
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if manifest is None:
        ctx.log.error(
            "Workspace update requires a configured or explicit workspace manifest. "
            "Pass --manifest <path> or configure workspace.manifest."
        )
        return base_cli.ExitCode.FAILURE

    try:
        selected_repositories = select_workspace_update_repositories(
            manifest,
            getattr(options, "workspace_repos", None),
        )
    except WorkspaceUpdateSelectionError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    return workspace_update_command(
        ctx,
        workspace_root,
        manifest,
        dry_run=options.dry_run,
        repositories=selected_repositories,
        output_format=output_format,
    )


# pylint: disable=too-many-arguments
def workspace_update_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    *,
    dry_run: bool,
    repositories: tuple[WorkspaceManifestRepo, ...] | None = None,
    output_format: str = "text",
) -> int:
    targets = workspace_update_targets(workspace_root, workspace_manifest, repositories=repositories)
    name_width = max(len("REPOSITORY"), *(len(target.name) for target in targets))
    if output_format == "text":
        print_workspace_update_header(workspace_root, workspace_manifest, len(targets), name_width)

    counts = WorkspaceUpdateCounts()
    results: list[tuple[WorkspaceUpdateTarget, WorkspaceUpdateResult]] = []
    for target in targets:
        if target.action == "skip":
            result = WorkspaceUpdateResult("skipped", target.reason)
            counts = update_workspace_update_counts(counts, result, fatal=target.fatal)
        elif dry_run:
            result = WorkspaceUpdateResult("planned")
            counts = update_workspace_update_counts(counts, result)
        else:
            result = execute_workspace_update_target(ctx, target)
            counts = update_workspace_update_counts(counts, result)

        results.append((target, result))
        if output_format == "text":
            print_workspace_update_result(target, result, name_width)

    if output_format == "json":
        return render_workspace_update_json(
            workspace_root,
            workspace_manifest,
            targets,
            results,
            counts,
            dry_run=dry_run,
        )

    if dry_run:
        print(
            "Workspace update plan complete: "
            f"planned={counts.planned} skipped={counts.skipped} failed={counts.failed}."
        )
        print("[DRY-RUN] No repositories were modified.")
        return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS

    print(
        "Workspace update completed: "
        f"updated={counts.updated} unchanged={counts.unchanged} "
        f"skipped={counts.skipped} failed={counts.failed}."
    )
    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def select_workspace_update_repositories(
    workspace_manifest: WorkspaceManifest,
    repository_selector: str | None,
) -> tuple[WorkspaceManifestRepo, ...]:
    if repository_selector is None:
        return workspace_manifest.repos

    requested_names: list[str] = []
    for raw_name in repository_selector.split(","):
        name = raw_name.strip()
        if not name:
            raise WorkspaceUpdateSelectionError("--repos must not contain an empty repository name.")
        if name in requested_names:
            raise WorkspaceUpdateSelectionError(f"--repos contains duplicate repository '{name}'.")
        requested_names.append(name)

    manifest_names = {repo.name for repo in workspace_manifest.repos}
    unknown_names = [name for name in requested_names if name not in manifest_names]
    if unknown_names:
        available = ", ".join(repo.name for repo in workspace_manifest.repos)
        unknown = ", ".join(unknown_names)
        raise WorkspaceUpdateSelectionError(
            f"--repos contains unknown repository name(s): {unknown}. Available repositories: {available}."
        )

    requested = set(requested_names)
    return tuple(repo for repo in workspace_manifest.repos if repo.name in requested)


# pylint: disable=too-many-arguments
def render_workspace_update_json(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceUpdateTarget, ...],
    results: list[tuple[WorkspaceUpdateTarget, WorkspaceUpdateResult]],
    counts: WorkspaceUpdateCounts,
    *,
    dry_run: bool,
) -> int:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "workspace": str(workspace_root),
        "workspace_manifest": {
            "path": str(workspace_manifest.path),
            "name": workspace_manifest.name,
            "schema_version": workspace_manifest.schema_version,
        },
        "dry_run": dry_run,
        "selected_repositories": [target.name for target in targets],
        "repository_count": len(targets),
        "repositories": [workspace_update_repository_to_json(target, result) for target, result in results],
        "counts": {
            "planned": counts.planned,
            "updated": counts.updated,
            "unchanged": counts.unchanged,
            "skipped": counts.skipped,
            "failed": counts.failed,
        },
    }
    base_cli.render_document(payload, requested_format="json")
    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def workspace_update_repository_to_json(
    target: WorkspaceUpdateTarget,
    result: WorkspaceUpdateResult,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "repository": target.name,
        "path": str(target.root),
        "required": target.required,
        "action": target.action,
        "status": result.status,
        "fatal": target.fatal,
    }
    if result.detail is not None:
        payload["detail"] = result.detail
    if result.exit_code is not None:
        payload["exit_code"] = result.exit_code
    return payload


def workspace_update_targets(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    *,
    repositories: tuple[WorkspaceManifestRepo, ...] | None = None,
) -> tuple[WorkspaceUpdateTarget, ...]:
    selected_repositories = workspace_manifest.repos if repositories is None else repositories
    return tuple(
        workspace_update_manifest_target(
            workspace_root,
            repo,
        )
        for repo in selected_repositories
    )


def workspace_update_manifest_target(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
) -> WorkspaceUpdateTarget:
    try:
        root = workspace_context.resolve_workspace_repo_root(workspace_root, repo.name)
    except WorkspacePathOutsideRootError as exc:
        return WorkspaceUpdateTarget(
            name=repo.name,
            root=workspace_root / repo.name,
            action="skip",
            reason=str(exc),
            required=repo.required,
            fatal=True,
        )

    if not root.is_dir():
        return WorkspaceUpdateTarget(
            name=repo.name,
            root=root,
            action="skip",
            reason=f"repository is missing at '{root}'",
            required=repo.required,
            fatal=repo.required,
        )

    return WorkspaceUpdateTarget(
        name=repo.name,
        root=root,
        action="pull",
        required=repo.required,
    )


def print_workspace_update_header(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    target_count: int,
    name_width: int,
) -> None:
    print(f"Workspace update: {workspace_root} ({target_count} manifest repos)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print()
    print(f"{'REPOSITORY':<{name_width}}  {'ACTION':<6}  RESULT")


def print_workspace_update_result(
    target: WorkspaceUpdateTarget,
    result: WorkspaceUpdateResult,
    name_width: int,
) -> None:
    action = target.action.upper()
    outcome = result.status
    if result.exit_code is not None:
        outcome = f"{outcome} (exit {result.exit_code})"
    print(f"{target.name:<{name_width}}  {action:<6}  {outcome}")
    if result.detail:
        for line in result.detail.splitlines():
            print(f"{'':<{name_width}}  {'':<6}  {line}")


def update_workspace_update_counts(
    counts: WorkspaceUpdateCounts,
    result: WorkspaceUpdateResult,
    *,
    fatal: bool = False,
) -> WorkspaceUpdateCounts:
    return WorkspaceUpdateCounts(
        planned=counts.planned + (result.status == "planned"),
        updated=counts.updated + (result.status == "updated"),
        unchanged=counts.unchanged + (result.status == "unchanged"),
        skipped=counts.skipped + (result.status == "skipped"),
        failed=counts.failed + (result.status == "failed" or fatal),
    )


def execute_workspace_update_target(
    ctx: base_cli.Context,
    target: WorkspaceUpdateTarget,
) -> WorkspaceUpdateResult:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["LC_ALL"] = "C"

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
            cwd=target.root,
            env=env,
            timeout=WORKSPACE_UPDATE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return WorkspaceUpdateResult(
            "failed",
            detail=f"timed out after {WORKSPACE_UPDATE_TIMEOUT_SECONDS} seconds",
        )
    except OSError as exc:
        return WorkspaceUpdateResult(
            "failed",
            detail=f"could not run git pull: {exc}",
        )

    debug_output = format_git_pull_debug_output(result.stdout, result.stderr)
    ctx.log.debug(
        "Git pull for repository '%s' exited with %s%s",
        target.name,
        result.returncode,
        f"; {debug_output}" if debug_output else "",
    )
    if result.returncode != 0:
        return WorkspaceUpdateResult(
            "failed",
            detail=git_pull_detail(result.stdout, result.stderr),
            exit_code=result.returncode,
        )

    if git_pull_was_unchanged(result.stdout, result.stderr):
        return WorkspaceUpdateResult("unchanged")
    return WorkspaceUpdateResult("updated")


def format_git_pull_debug_output(stdout: str, stderr: str) -> str:
    fields: list[str] = []
    for name, output in (("stdout", stdout), ("stderr", stderr)):
        value = " ".join(line.strip() for line in output.splitlines() if line.strip())
        if value:
            fields.append(f"{name}={value}")
    return "; ".join(fields)


def git_pull_detail(stdout: str, stderr: str) -> str:
    details = [part.strip() for part in (stderr, stdout) if part.strip()]
    return "\n".join(details) or "git pull failed without diagnostic output"


def git_pull_was_unchanged(stdout: str, stderr: str) -> bool:
    output = f"{stdout}\n{stderr}".lower()
    return "already up to date" in output or "already up-to-date" in output
