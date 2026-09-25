from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import base_cli
from base_projects.command_helpers import ProjectCommandError as ProjectRunnerError
from base_projects.command_helpers import ProjectUsageError
from base_projects.command_helpers import github_repo_spec
from base_projects.command_helpers import run_project_command
from base_projects.workspace_context import effective_workspace_manifest
from base_projects.workspace_context import WorkspacePathOutsideRootError
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_context import resolve_workspace_repo_root
from base_projects.workspace_context import resolve_workspace_root
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_repository_url import redact_repository_url
from base_projects.workspace_report_common import repository_name_width
from base_projects.workspace_scanner import ProjectDiscoveryError


class WorkspaceCloneOptions(Protocol):
    workspace: str | None
    output_format: str
    workspace_manifest: str | None
    include_optional: bool
    dry_run: bool


WorkspaceCloneAction = Literal["check", "clone", "skip"]
WorkspaceCloneStatus = Literal["planned", "present", "cloned", "skipped", "failed"]


@dataclass(frozen=True)
class WorkspaceCloneTarget:
    name: str
    root: Path
    action: WorkspaceCloneAction


@dataclass(frozen=True)
class WorkspaceCloneResult:
    status: WorkspaceCloneStatus
    detail: str | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class WorkspaceCloneCounts:
    planned: int = 0
    present: int = 0
    cloned: int = 0
    skipped: int = 0
    failed: int = 0


BASE_LOG_RECORD_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}"
    r"(?:\s+(?:[+-]\d{4}|UTC))?\s+"
    r"(?:TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\s+"
)


def workspace_clone_command(ctx: base_cli.Context, options: WorkspaceCloneOptions) -> int:
    if options.output_format != "text":
        raise ProjectUsageError(f"Unsupported output format '{options.output_format}'. Expected: text.")

    try:
        workspace_root = resolve_workspace_root(ctx, options.workspace)
        manifest = require_workspace_clone_manifest(ctx, options.workspace_manifest)
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    workspace_root = workspace_root.resolve(strict=False)

    if ctx.application_home is None:
        ctx.log.error("BASE_HOME is required to clone workspace repositories.")
        return base_cli.ExitCode.FAILURE

    basectl = ctx.application_home / "bin" / "basectl"
    name_width = repository_name_width(repo.name for repo in manifest.repos)
    print(f"Workspace clone: {workspace_root} ({len(manifest.repos)} manifest repos)")
    print(f"Workspace manifest: {manifest.path} ({manifest.name})")
    print()
    print_workspace_clone_header(name_width)

    counts = WorkspaceCloneCounts()
    for repo in manifest.repos:
        try:
            target = resolve_workspace_clone_target(workspace_root, repo.name)
        except ProjectUsageError as exc:
            target = WorkspaceCloneTarget(repo.name, workspace_root / repo.name, "clone")
            result = WorkspaceCloneResult("failed", str(exc))
            counts = update_workspace_clone_counts(counts, result)
            print_workspace_clone_result(target, result, name_width)
            continue

        if should_skip_optional_clone(repo, target, options.include_optional):
            result = WorkspaceCloneResult(
                "skipped",
                f"optional repository is missing at '{target}'; pass --include-optional to clone it",
            )
            counts = update_workspace_clone_counts(counts, result)
            print_workspace_clone_result(
                WorkspaceCloneTarget(repo.name, target, "skip"),
                result,
                name_width,
            )
            continue

        target_spec = WorkspaceCloneTarget(
            repo.name,
            target,
            "check" if target.exists() else "clone",
        )
        result = clone_workspace_repo(
            ctx,
            basectl,
            repo,
            target,
            dry_run=options.dry_run,
        )
        counts = update_workspace_clone_counts(counts, result)
        print_workspace_clone_result(target_spec, result, name_width)

    if options.dry_run:
        print(
            "Workspace clone plan complete: "
            f"planned={counts.planned} skipped={counts.skipped} failed={counts.failed}."
        )
        print("[DRY-RUN] No repositories were modified.")
    else:
        print(
            "Workspace clone completed: "
            f"present={counts.present} cloned={counts.cloned} "
            f"skipped={counts.skipped} failed={counts.failed}."
        )

    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def resolve_workspace_clone_target(workspace_root: Path, repo_name: str) -> Path:
    try:
        return resolve_workspace_repo_root(workspace_root, repo_name)
    except WorkspacePathOutsideRootError as exc:
        raise ProjectUsageError(str(exc)) from exc


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


def print_workspace_clone_header(name_width: int) -> None:
    print(f"{'REPOSITORY':<{name_width}}  {'ACTION':<6}  RESULT")


def print_optional_clone_skip(repo: WorkspaceManifestRepo, target: Path) -> None:
    """Retain the former helper for callers outside the command renderer."""
    print(
        f"SKIP optional repository '{repo.name}' is missing at '{target}'. "
        "Pass --include-optional to clone it."
    )


def print_workspace_clone_result(
    target: WorkspaceCloneTarget,
    result: WorkspaceCloneResult,
    name_width: int,
) -> None:
    outcome = result.status
    if result.exit_code is not None:
        outcome = f"{outcome} (exit {result.exit_code})"
    print(f"{target.name:<{name_width}}  {target.action.upper():<6}  {outcome}")
    if result.detail:
        for line in result.detail.splitlines():
            print(f"{'':<{name_width}}  {'':<6}  {line}")


def update_workspace_clone_counts(
    counts: WorkspaceCloneCounts,
    result: WorkspaceCloneResult,
) -> WorkspaceCloneCounts:
    return WorkspaceCloneCounts(
        planned=counts.planned + (result.status == "planned"),
        present=counts.present + (result.status == "present"),
        cloned=counts.cloned + (result.status == "cloned"),
        skipped=counts.skipped + (result.status == "skipped"),
        failed=counts.failed + (result.status == "failed"),
    )


def clone_workspace_repo(
    ctx: base_cli.Context,
    basectl: Path,
    repo: WorkspaceManifestRepo,
    target: Path,
    *,
    dry_run: bool,
) -> WorkspaceCloneResult:
    already_exists = target.exists()
    repo_spec = workspace_clone_repo_spec(repo)
    if repo_spec is None:
        return WorkspaceCloneResult(
            "failed",
            ""
            f"Repository '{repo.name}' has unsupported clone URL "
            f"'{redact_repository_url(repo.url) if repo.url is not None else None}'. "
            "Only github.com repository URLs are supported.",
        )

    command = [str(basectl), "repo", "clone", repo_spec, "--path", str(target)]
    if dry_run:
        command.append("--dry-run")

    try:
        result = run_project_command(
            command,
            error_context=f"basectl repo clone for repository '{repo.name}'",
        )
    except ProjectRunnerError as exc:
        return WorkspaceCloneResult("failed", str(exc))

    ctx.log.debug(
        "Clone command for repository '%s' exited with %s; stdout=%r stderr=%r",
        repo.name,
        result.returncode,
        result.stdout,
        result.stderr,
    )
    if result.returncode != 0:
        return WorkspaceCloneResult(
            "failed",
            detail=clone_detail(result.stdout, result.stderr),
            exit_code=result.returncode,
        )

    if dry_run:
        return WorkspaceCloneResult("planned")
    return WorkspaceCloneResult("present" if already_exists else "cloned")


def clone_detail(stdout: str, stderr: str) -> str:
    details = [
        line.strip()
        for stream in (stderr, stdout)
        for line in stream.splitlines()
        if line.strip() and not BASE_LOG_RECORD_RE.match(line.strip())
    ]
    return "\n".join(details) or "clone failed without diagnostic output"


def workspace_clone_repo_spec(repo: WorkspaceManifestRepo) -> str | None:
    if repo.url is None:
        return repo.name

    return github_repo_spec(repo.url)
