from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, replace
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
WorkspaceUpdatePreflightIssue = Literal[
    "dirty",
    "linked_worktree",
    "detached_head",
    "non_default_branch",
    "missing_upstream",
    "unknown_default_branch",
    "not_git_checkout",
    "preflight_failed",
]
WORKSPACE_UPDATE_TIMEOUT_SECONDS = 1800
WORKSPACE_UPDATE_PREFLIGHT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class WorkspaceUpdateTarget:
    name: str
    root: Path
    action: WorkspaceUpdateAction
    reason: str | None = None
    required: bool = True
    fatal: bool = False
    default_branch: str | None = None


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
    preflight: tuple[WorkspaceUpdatePreflightIssue, ...] = ()


@dataclass(frozen=True)
class WorkspaceUpdatePreflightState:
    dirty: bool
    branch: str | None
    upstream: str | None
    default_branch: str | None
    issues: tuple[WorkspaceUpdatePreflightIssue, ...]


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
        else:
            preflight_result = preflight_workspace_update_target(target)
            if preflight_result is not None:
                target = replace(target, action="skip", fatal=target.required)
                result = preflight_result
            elif dry_run:
                result = WorkspaceUpdateResult("planned")
            else:
                result = execute_workspace_update_target(ctx, target)
            counts = update_workspace_update_counts(counts, result, fatal=target.fatal)

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
    if result.preflight:
        payload["preflight"] = list(result.preflight)
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
        default_branch=repo.default_branch,
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
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
            cwd=target.root,
            env=workspace_update_git_environment(),
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


def preflight_workspace_update_target(target: WorkspaceUpdateTarget) -> WorkspaceUpdateResult | None:
    """Return a safe, actionable result when a manifest checkout is not pullable."""
    git_directories = workspace_update_git_directories(target)
    if isinstance(git_directories, WorkspaceUpdateResult):
        return git_directories

    git_directory, common_directory = git_directories
    if git_directory != common_directory:
        return workspace_update_preflight_result(
            ("linked_worktree",),
            "\n".join(
                (
                    f"repository '{target.name}' at '{target.root}' is a linked Git worktree.",
                    "Workspace update only updates manifest repository roots; it will not pull this PR worktree.",
                    "Point the manifest at the primary checkout or rerun from that checkout; "
                    "Base will not switch or modify this worktree.",
                )
            ),
        )

    checkout_status = workspace_update_git_status(target)
    if isinstance(checkout_status, WorkspaceUpdateResult):
        return checkout_status

    state = workspace_update_preflight_state(target, checkout_status)
    if not state.issues:
        return None
    return workspace_update_preflight_result(state.issues, workspace_update_preflight_detail(target, state))


def workspace_update_git_directories(
    target: WorkspaceUpdateTarget,
) -> tuple[Path, Path] | WorkspaceUpdateResult:
    try:
        metadata = run_workspace_git_probe(target.root, "rev-parse", "--git-dir", "--git-common-dir")
    except subprocess.TimeoutExpired:
        return workspace_update_preflight_result(
            ("preflight_failed",),
            f"Git preflight for repository '{target.name}' at '{target.root}' timed out after "
            f"{WORKSPACE_UPDATE_PREFLIGHT_TIMEOUT_SECONDS} seconds.",
        )
    except OSError as exc:
        return workspace_update_preflight_result(
            ("preflight_failed",),
            f"Git preflight for repository '{target.name}' at '{target.root}' could not run: {exc}",
        )

    if metadata.returncode != 0:
        detail = git_pull_detail(metadata.stdout, metadata.stderr)
        return workspace_update_preflight_result(
            ("not_git_checkout",),
            f"repository '{target.name}' at '{target.root}' is not a Git checkout: {detail}",
        )

    git_directories = [line.strip() for line in metadata.stdout.splitlines() if line.strip()]
    if len(git_directories) != 2:
        return workspace_update_preflight_result(
            ("preflight_failed",),
            f"repository '{target.name}' at '{target.root}' returned incomplete Git worktree metadata.",
        )

    return (
        resolve_workspace_git_directory(target.root, git_directories[0]),
        resolve_workspace_git_directory(target.root, git_directories[1]),
    )


def workspace_update_git_status(
    target: WorkspaceUpdateTarget,
) -> tuple[bool, str | None, str | None] | WorkspaceUpdateResult:
    try:
        status = run_workspace_git_probe(
            target.root,
            "status",
            "--porcelain=v1",
            "--branch",
            "--untracked-files=all",
        )
    except subprocess.TimeoutExpired:
        return workspace_update_preflight_result(
            ("preflight_failed",),
            f"Git status for repository '{target.name}' at '{target.root}' timed out after "
            f"{WORKSPACE_UPDATE_PREFLIGHT_TIMEOUT_SECONDS} seconds.",
        )
    except OSError as exc:
        return workspace_update_preflight_result(
            ("preflight_failed",),
            f"Git status for repository '{target.name}' at '{target.root}' could not run: {exc}",
        )
    if status.returncode != 0:
        detail = git_pull_detail(status.stdout, status.stderr)
        return workspace_update_preflight_result(
            ("preflight_failed",),
            f"could not inspect Git checkout '{target.root}': {detail}",
        )

    return parse_workspace_git_status(status.stdout)


def workspace_update_preflight_state(
    target: WorkspaceUpdateTarget,
    checkout_status: tuple[bool, str | None, str | None],
) -> WorkspaceUpdatePreflightState:
    dirty, branch, upstream = checkout_status
    default_branch = target.default_branch
    issues: list[WorkspaceUpdatePreflightIssue] = []
    if dirty:
        issues.append("dirty")

    if branch is None:
        issues.append("detached_head")

    if default_branch is None:
        default_branch = workspace_update_remote_default_branch(target, upstream)
        if default_branch is None:
            issues.append("unknown_default_branch")

    if branch is not None and default_branch is not None and branch != default_branch:
        issues.append("non_default_branch")
    if upstream is None:
        issues.append("missing_upstream")

    return WorkspaceUpdatePreflightState(
        dirty=dirty,
        branch=branch,
        upstream=upstream,
        default_branch=default_branch,
        issues=tuple(issues),
    )


def workspace_update_remote_default_branch(target: WorkspaceUpdateTarget, upstream: str | None) -> str | None:
    remote = upstream.split("/", 1)[0] if upstream and "/" in upstream else "origin"
    try:
        remote_head = run_workspace_git_probe(
            target.root,
            "ls-remote",
            "--symref",
            remote,
            "HEAD",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if remote_head.returncode != 0:
        return None
    return parse_workspace_remote_default_branch(remote_head.stdout)


def workspace_update_preflight_detail(
    target: WorkspaceUpdateTarget,
    state: WorkspaceUpdatePreflightState,
) -> str:
    dirty = state.dirty
    branch = state.branch
    upstream = state.upstream
    default_branch = state.default_branch
    issues = state.issues
    detail_lines = [f"repository '{target.name}' at '{target.root}' is not safe to update:"]
    if dirty:
        detail_lines.append(
            f"working tree is dirty on branch '{branch or 'detached HEAD'}'"
            f"{f' (tracking {upstream})' if upstream else ''}."
        )
        detail_lines.append(
            "Preserve the local changes by committing, stashing, or moving the work to a dedicated worktree; "
            "Base will not stash or reset this checkout."
        )
    if "detached_head" in issues:
        detail_lines.append("the checkout is detached from a branch.")
    if "non_default_branch" in issues:
        detail_lines.append(
            f"current branch '{branch}' is not the expected default branch '{default_branch}'."
        )
        detail_lines.append(
            f"After preserving any branch work, check out '{default_branch}' in '{target.root}' "
            "or keep the review branch in a separate worktree; Base will not switch it."
        )
    if "missing_upstream" in issues:
        detail_lines.append(
            f"branch '{branch or 'detached HEAD'}' has no upstream tracking branch."
        )
        detail_lines.append(
            "Configure tracking for the intended default branch, then rerun workspace update; "
            "Base will not infer or assign an upstream."
        )
    if "unknown_default_branch" in issues:
        detail_lines.append(
            "the default branch could not be determined. Set repos[].default_branch in the workspace manifest "
            "or configure the remote's HEAD, then rerun workspace update."
        )
    return "\n".join(detail_lines)


def resolve_workspace_git_directory(root: Path, value: str) -> Path:
    path = Path(value)
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def parse_workspace_remote_default_branch(output: str) -> str | None:
    for line in output.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            branch = line.removeprefix("ref: refs/heads/").removesuffix("\tHEAD")
            return branch or None
    return None


def workspace_update_preflight_result(
    issues: tuple[WorkspaceUpdatePreflightIssue, ...],
    detail: str,
) -> WorkspaceUpdateResult:
    return WorkspaceUpdateResult("skipped", detail=detail, preflight=issues)


def run_workspace_git_probe(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
        text=True,
        cwd=root,
        env=workspace_update_git_environment(),
        timeout=WORKSPACE_UPDATE_PREFLIGHT_TIMEOUT_SECONDS,
    )


def workspace_update_git_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["LC_ALL"] = "C"
    return env


def parse_workspace_git_status(output: str) -> tuple[bool, str | None, str | None]:
    lines = output.splitlines()
    dirty = any(not line.startswith("## ") for line in lines)
    branch_line = next((line[3:] for line in lines if line.startswith("## ")), "")
    if branch_line.startswith("HEAD (no branch)"):
        return dirty, None, None
    if "..." in branch_line:
        branch, upstream = branch_line.split("...", 1)
        return dirty, branch.strip(), upstream.split(" [", 1)[0].strip() or None
    return dirty, branch_line.split(" [", 1)[0].strip() or None, None


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
