from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import base_cli
from base_projects import workspace_context
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError


WorkspaceTestAction = Literal["test", "skip"]
WorkspaceTestStatus = Literal["passed", "failed", "skipped"]
WORKSPACE_TEST_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class WorkspaceTestTarget:
    name: str
    root: Path
    manifest_path: Path | None
    project_name: str | None
    action: WorkspaceTestAction
    reason: str | None = None
    required: bool = True
    fatal: bool = False


@dataclass(frozen=True)
class WorkspaceTestResult:
    status: WorkspaceTestStatus
    detail: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class WorkspaceTestCounts:
    passed: int = 0
    failed: int = 0
    skipped: int = 0


class WorkspaceTestSelectionError(ValueError):
    """Raised when --projects does not identify a valid manifest selection."""


def workspace_test_from_options(ctx: base_cli.Context, options: Any) -> int:
    output_format = str(getattr(options, "output_format", "text") or "text").lower()
    if output_format not in {"text", "json"}:
        ctx.log.error("Unsupported output format '%s'. Expected: text or json.", options.output_format)
        return base_cli.ExitCode.USAGE_ERROR
    if getattr(options, "dry_run", False):
        ctx.log.error("Workspace test does not support --dry-run.")
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
            "Workspace test requires a configured or explicit workspace manifest. "
            "Pass --manifest <path> or configure workspace.manifest."
        )
        return base_cli.ExitCode.FAILURE

    targets = workspace_test_targets(workspace_root, manifest)
    try:
        targets = select_workspace_test_targets(targets, getattr(options, "workspace_projects", None))
    except WorkspaceTestSelectionError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    return workspace_test_command(
        ctx,
        workspace_root,
        manifest,
        targets,
        fail_fast=bool(getattr(options, "fail_fast", False)),
        output_format=output_format,
    )


def workspace_test_targets(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
) -> tuple[WorkspaceTestTarget, ...]:
    return tuple(
        workspace_test_manifest_target(workspace_root, repo)
        for repo in workspace_manifest.repos
    )


def workspace_test_manifest_target(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
) -> WorkspaceTestTarget:
    try:
        root = workspace_context.resolve_workspace_repo_root(workspace_root, repo.name)
    except workspace_context.WorkspacePathOutsideRootError as exc:
        return WorkspaceTestTarget(
            name=repo.name,
            root=workspace_root / repo.name,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason=str(exc),
            required=repo.required,
            fatal=True,
        )

    manifest_path = root / "base_manifest.yaml"
    if not root.is_dir():
        return WorkspaceTestTarget(
            name=repo.name,
            root=root,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason=f"repository is missing at '{root}'",
            required=repo.required,
            fatal=repo.required,
        )
    if not manifest_path.is_file():
        return WorkspaceTestTarget(
            name=repo.name,
            root=root,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason="repository does not contain base_manifest.yaml",
            required=repo.required,
        )

    try:
        manifest = read_manifest(manifest_path)
    except ManifestError as exc:
        return WorkspaceTestTarget(
            name=repo.name,
            root=root,
            manifest_path=manifest_path.resolve(),
            project_name=None,
            action="skip",
            reason=f"base_manifest.yaml is invalid: {exc}",
            required=repo.required,
            fatal=repo.required,
        )

    if manifest.test is None:
        return WorkspaceTestTarget(
            name=repo.name,
            root=root,
            manifest_path=manifest_path.resolve(),
            project_name=manifest.project_name,
            action="skip",
            reason="project does not declare a test command",
            required=repo.required,
        )

    return WorkspaceTestTarget(
        name=repo.name,
        root=root,
        manifest_path=manifest_path.resolve(),
        project_name=manifest.project_name,
        action="test",
        required=repo.required,
    )


def select_workspace_test_targets(
    targets: tuple[WorkspaceTestTarget, ...],
    project_selector: str | None,
) -> tuple[WorkspaceTestTarget, ...]:
    if project_selector is None:
        return targets

    requested_names: list[str] = []
    for raw_name in project_selector.split(","):
        name = raw_name.strip()
        if not name:
            raise WorkspaceTestSelectionError("--projects must not contain an empty project name.")
        if name in requested_names:
            raise WorkspaceTestSelectionError(f"--projects contains duplicate project '{name}'.")
        requested_names.append(name)

    available_names = {
        name
        for target in targets
        for name in (target.name, target.project_name)
        if name is not None
    }
    unknown_names = [name for name in requested_names if name not in available_names]
    if unknown_names:
        available = ", ".join(
            target.project_name or target.name
            for target in targets
        )
        unknown = ", ".join(unknown_names)
        raise WorkspaceTestSelectionError(
            f"--projects contains unknown project name(s): {unknown}. Available projects: {available}."
        )

    requested = set(requested_names)
    return tuple(
        target
        for target in targets
        if target.name in requested or target.project_name in requested
    )


# pylint: disable=too-many-arguments
def workspace_test_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceTestTarget, ...],
    *,
    fail_fast: bool,
    output_format: str,
) -> int:
    if ctx.application_home is None:
        ctx.log.error("BASE_HOME is required to execute workspace tests.")
        return base_cli.ExitCode.FAILURE

    basectl = ctx.application_home / "bin" / "basectl"
    if not basectl.is_file() or not os.access(basectl, os.X_OK):
        ctx.log.error("Base CLI '%s' is missing or is not executable.", basectl)
        return base_cli.ExitCode.FAILURE

    if output_format == "text":
        print_workspace_test_header(workspace_root, workspace_manifest, targets)

    counts = WorkspaceTestCounts()
    results: list[tuple[WorkspaceTestTarget, WorkspaceTestResult]] = []
    stopped = False
    for target in targets:
        if stopped:
            result = WorkspaceTestResult("skipped", "not run because --fail-fast stopped after a failure")
        elif target.action == "skip":
            status: WorkspaceTestStatus = "failed" if target.fatal else "skipped"
            result = WorkspaceTestResult(status, target.reason)
        else:
            result = execute_workspace_test_target(ctx, basectl, workspace_root, target)

        results.append((target, result))
        counts = update_workspace_test_counts(counts, result)
        if output_format == "text":
            print_workspace_test_result(target, result)
        if result.status == "failed" and fail_fast:
            stopped = True

    if output_format == "json":
        render_workspace_test_json(
            workspace_root,
            workspace_manifest,
            targets,
            results,
            counts,
            fail_fast=fail_fast,
        )
    else:
        print_workspace_test_summary(counts)
    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def execute_workspace_test_target(
    ctx: base_cli.Context,
    basectl: Path,
    workspace_root: Path,
    target: WorkspaceTestTarget,
) -> WorkspaceTestResult:
    if target.project_name is None:
        return WorkspaceTestResult("failed", "test target is missing project routing metadata")

    command = [
        str(basectl),
        "test",
        "--workspace",
        str(workspace_root),
        "--project",
        target.project_name,
    ]
    env = os.environ.copy()
    env["BASE_HOME"] = str(ctx.application_home)
    for variable in ("BASE_PROJECT", "BASE_PROJECT_ROOT", "BASE_PROJECT_MANIFEST", "BASE_PROJECT_VENV_DIR"):
        env.pop(variable, None)

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=target.root,
            env=env,
            timeout=WORKSPACE_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return WorkspaceTestResult(
            "failed",
            f"timed out after {WORKSPACE_TEST_TIMEOUT_SECONDS} seconds",
        )
    except OSError as exc:
        return WorkspaceTestResult("failed", f"could not run test command: {exc}")

    if result.returncode == 0:
        return WorkspaceTestResult("passed", stdout=result.stdout or "", stderr=result.stderr or "")
    return WorkspaceTestResult(
        "failed",
        f"test command exited with status {result.returncode}",
        exit_code=result.returncode,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
    )


def update_workspace_test_counts(
    counts: WorkspaceTestCounts,
    result: WorkspaceTestResult,
) -> WorkspaceTestCounts:
    if result.status == "passed":
        return WorkspaceTestCounts(counts.passed + 1, counts.failed, counts.skipped)
    if result.status == "failed":
        return WorkspaceTestCounts(counts.passed, counts.failed + 1, counts.skipped)
    return WorkspaceTestCounts(counts.passed, counts.failed, counts.skipped + 1)


def print_workspace_test_header(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceTestTarget, ...],
) -> None:
    print(f"Workspace test: {workspace_root} ({len(targets)} projects)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")


def print_workspace_test_result(target: WorkspaceTestTarget, result: WorkspaceTestResult) -> None:
    project = target.project_name or target.name
    if result.status == "passed":
        print(f"PASS project '{project}' at '{target.root}'.")
    elif result.status == "failed":
        print(f"FAIL project '{project}' at '{target.root}': {result.detail}.")
    else:
        print(f"SKIP project '{project}' at '{target.root}': {result.detail}.")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def print_workspace_test_summary(counts: WorkspaceTestCounts) -> None:
    print(
        "Workspace test completed: "
        f"passed={counts.passed} failed={counts.failed} skipped={counts.skipped}."
    )


# pylint: disable=too-many-arguments
def render_workspace_test_json(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceTestTarget, ...],
    results: list[tuple[WorkspaceTestTarget, WorkspaceTestResult]],
    counts: WorkspaceTestCounts,
    *,
    fail_fast: bool,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "workspace": str(workspace_root),
        "workspace_manifest": {
            "path": str(workspace_manifest.path),
            "name": workspace_manifest.name,
            "schema_version": workspace_manifest.schema_version,
        },
        "fail_fast": fail_fast,
        "selected_projects": [target.project_name or target.name for target in targets],
        "project_count": len(targets),
        "projects": [workspace_test_project_to_json(target, result) for target, result in results],
        "counts": {
            "passed": counts.passed,
            "failed": counts.failed,
            "skipped": counts.skipped,
        },
    }
    base_cli.render_document(payload, requested_format="json")


def workspace_test_project_to_json(
    target: WorkspaceTestTarget,
    result: WorkspaceTestResult,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project": target.project_name,
        "repository": target.name,
        "path": str(target.root),
        "required": target.required,
        "status": result.status,
    }
    if result.detail is not None:
        payload["detail"] = result.detail
    if result.exit_code is not None:
        payload["exit_code"] = result.exit_code
    if result.stdout:
        payload["stdout"] = result.stdout
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload
