from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import base_cli
from base_projects import workspace_context
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_repo_inspection import inspect_workspace_repo
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_projects.workspace_process import run_workspace_subprocess
from base_projects.project_commands import test_command as project_test_command
from base_projects.test_preflight import project_test_trust_status
from base_setup.process import decode_subprocess_output
from base_setup.process import redact_command_output
from base_setup.manifest_model import BaseManifest
from base_setup.manifest_trust import ManifestCommandTrustStore


WorkspaceTestAction = Literal["test", "skip"]
WorkspaceTestStatus = Literal["passed", "failed", "blocked", "not_run", "skipped"]
WORKSPACE_TEST_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class WorkspaceTestTarget:
    name: str
    root: Path
    manifest_path: Path | None
    project_name: str | None
    action: WorkspaceTestAction
    manifest: BaseManifest | None = None
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
    command: str | None = None
    trust_status: Literal["allowed", "blocked"] | None = None
    executed: bool = False
    duration_seconds: float | None = None


@dataclass(frozen=True)
class WorkspaceTestPreflight:
    status: Literal["allowed", "blocked", "failed", "skipped"]
    command: str | None = None
    trust_status: Literal["allowed", "blocked"] | None = None
    detail: str | None = None


@dataclass(frozen=True)
class WorkspaceTestCounts:
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    not_run: int = 0
    skipped: int = 0


class WorkspaceTestSelectionError(ValueError):
    """Raised when --projects does not identify a valid manifest selection."""


def workspace_test_from_options(ctx: base_cli.Context, options: Any) -> int:
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
        dry_run=bool(getattr(options, "dry_run", False)),
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
    inspection = inspect_workspace_repo(workspace_root, repo)
    if inspection.state == "outside_workspace":
        return WorkspaceTestTarget(
            name=repo.name,
            root=inspection.root,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason=inspection.reason,
            required=repo.required,
            fatal=True,
        )

    if inspection.state == "missing_repository":
        return WorkspaceTestTarget(
            name=repo.name,
            root=inspection.root,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason=inspection.reason,
            required=repo.required,
            fatal=inspection.fatal,
        )
    if inspection.state != "inspected":
        return WorkspaceTestTarget(
            name=repo.name,
            root=inspection.root,
            manifest_path=inspection.manifest_path,
            project_name=None,
            action="skip",
            reason=inspection.reason,
            required=repo.required,
            fatal=inspection.fatal,
        )

    manifest = inspection.manifest
    if manifest is None:
        return WorkspaceTestTarget(
            name=repo.name,
            root=inspection.root,
            manifest_path=inspection.manifest_path,
            project_name=None,
            action="skip",
            reason="workspace repository inspection did not return a parsed manifest",
            required=repo.required,
            fatal=True,
        )

    if manifest.test is None:
        return WorkspaceTestTarget(
            name=repo.name,
            root=inspection.root,
            manifest_path=inspection.manifest_path,
            project_name=manifest.project_name,
            action="skip",
            reason="project does not declare a test command",
            required=repo.required,
        )

    return WorkspaceTestTarget(
        name=repo.name,
        root=inspection.root,
        manifest_path=inspection.manifest_path,
        manifest=manifest,
        project_name=manifest.project_name,
        action="test",
        required=repo.required,
    )


def select_workspace_test_targets(
    targets: tuple[WorkspaceTestTarget, ...],
    project_selector: str | None,
) -> tuple[WorkspaceTestTarget, ...]:
    if project_selector is None:
        return validate_distinct_test_manifests(targets)

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

    selected = {resolve_selected_target(targets, name).name for name in requested_names}
    return validate_distinct_test_manifests(tuple(target for target in targets if target.name in selected))


def resolve_selected_target(targets: tuple[WorkspaceTestTarget, ...], name: str) -> WorkspaceTestTarget:
    repositories = [target for target in targets if target.name == name]
    matches = repositories or [target for target in targets if target.project_name == name]
    if len(matches) != 1:
        raise WorkspaceTestSelectionError(
            f"Project name '{name}' is ambiguous; select its workspace repository name instead."
        )
    return matches[0]


def validate_distinct_test_manifests(targets: tuple[WorkspaceTestTarget, ...]) -> tuple[WorkspaceTestTarget, ...]:
    seen: dict[Path, str] = {}
    for target in targets:
        if target.action != "test" or target.manifest_path is None:
            continue
        manifest = target.manifest_path.resolve()
        if manifest in seen:
            raise WorkspaceTestSelectionError(
                f"Selected repositories '{seen[manifest]}' and '{target.name}' resolve to the same manifest "
                f"'{manifest}'. Select only one repository alias."
            )
        seen[manifest] = target.name
    return targets


# pylint: disable=too-many-arguments,too-many-branches
def workspace_test_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceTestTarget, ...],
    *,
    fail_fast: bool,
    output_format: str,
    dry_run: bool,
) -> int:
    if ctx.application_home is None and not dry_run:
        ctx.log.error("BASE_HOME is required to execute workspace tests.")
        return base_cli.ExitCode.FAILURE

    basectl = ctx.application_home / "bin" / "basectl" if ctx.application_home else None
    if not dry_run and (basectl is None or not basectl.is_file() or not os.access(basectl, os.X_OK)):
        ctx.log.error("Base CLI '%s' is missing or is not executable.", basectl)
        return base_cli.ExitCode.FAILURE

    preflights = workspace_test_preflight(targets)
    preflight_blocked = any(item.status == "blocked" for item in preflights.values())
    preflight_failed = any(item.status == "failed" for item in preflights.values())
    if output_format == "text":
        print_workspace_test_header(workspace_root, workspace_manifest, targets, dry_run=dry_run)
        print_workspace_test_preflight(targets, preflights)

    if dry_run or preflight_blocked or preflight_failed:
        return render_workspace_test_plan(
            workspace_root,
            workspace_manifest,
            targets,
            preflights,
            fail_fast=fail_fast,
            output_format=output_format,
            dry_run=dry_run,
            preflight_blocked=preflight_blocked,
            preflight_failed=preflight_failed,
        )

    counts = WorkspaceTestCounts()
    results: list[tuple[WorkspaceTestTarget, WorkspaceTestResult]] = []
    stopped = False
    execution_started = False
    for index, target in enumerate(targets, start=1):
        if stopped:
            result = WorkspaceTestResult("not_run", "not run because execution was stopped")
        elif target.action == "skip":
            status: WorkspaceTestStatus = "failed" if target.fatal else "skipped"
            result = WorkspaceTestResult(status, target.reason)
        else:
            preflight = preflights[target.name]
            if output_format == "text":
                print_workspace_test_start(index, len(targets), target, preflight)
            execution_started = True
            result = execute_workspace_test_target(ctx, basectl, workspace_root, target, preflight)

        results.append((target, result))
        counts = update_workspace_test_counts(counts, result)
        if output_format == "text":
            print_workspace_test_result(target, result)
        if result.status == "blocked" or (result.status == "failed" and fail_fast):
            stopped = True

    if output_format == "json":
        render_workspace_test_json(
            workspace_root,
            workspace_manifest,
            targets,
            results,
            counts,
            fail_fast=fail_fast,
            preflight_status="passed",
            execution_started=execution_started,
            dry_run=False,
        )
    else:
        print_workspace_test_summary(counts, execution_started=execution_started)
    return base_cli.ExitCode.FAILURE if counts.failed or counts.blocked else base_cli.ExitCode.SUCCESS


# pylint: disable=too-many-arguments
def render_workspace_test_plan(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceTestTarget, ...],
    preflights: dict[str, WorkspaceTestPreflight],
    *,
    fail_fast: bool,
    output_format: str,
    dry_run: bool,
    preflight_blocked: bool,
    preflight_failed: bool,
) -> int:
    results = (
        blocked_workspace_test_results(targets, preflights)
        if (preflight_blocked or preflight_failed)
        else dry_run_workspace_test_results(targets, preflights)
    )
    counts = WorkspaceTestCounts()
    for _, result in results:
        counts = update_workspace_test_counts(counts, result)
    if output_format == "text":
        if preflight_blocked or preflight_failed:
            print_workspace_test_blocked_summary(targets, preflight_blocked, preflight_failed)
        elif counts.failed or counts.blocked:
            print("Workspace test plan failed: a required project selection cannot run.")
        else:
            print("Workspace test plan complete: no project test commands were executed.")
        for target, result in results:
            print_workspace_test_result(target, result, show_output=False)
        print_workspace_test_summary(counts, execution_started=False)
    else:
        render_workspace_test_json(
            workspace_root,
            workspace_manifest,
            targets,
            results,
            counts,
            fail_fast=fail_fast,
            preflight_status="blocked" if (preflight_blocked or preflight_failed) else "passed",
            execution_started=False,
            dry_run=dry_run,
        )
    return base_cli.ExitCode.FAILURE if counts.failed or counts.blocked else base_cli.ExitCode.SUCCESS


def workspace_test_preflight(
    targets: tuple[WorkspaceTestTarget, ...],
) -> dict[str, WorkspaceTestPreflight]:
    preflights: dict[str, WorkspaceTestPreflight] = {}
    trust_store = ManifestCommandTrustStore()
    for target in targets:
        if target.action != "test":
            preflights[target.name] = WorkspaceTestPreflight("skipped", detail=target.reason)
            continue
        if target.manifest_path is None:
            preflights[target.name] = WorkspaceTestPreflight(
                "failed", detail="test target is missing its manifest path"
            )
            continue
        if target.manifest is None:
            preflights[target.name] = WorkspaceTestPreflight(
                "failed", detail="test target is missing its parsed manifest"
            )
            continue
        command_config = project_test_command(target.manifest.test)
        trust_status = project_test_trust_status(target.manifest, trust_store=trust_store)

        command = workspace_test_command_text(command_config.command, command_config.runner)
        if trust_status.is_allowed:
            preflights[target.name] = WorkspaceTestPreflight(
                "allowed", command=command, trust_status="allowed"
            )
        else:
            preflights[target.name] = WorkspaceTestPreflight(
                "blocked",
                command=command,
                trust_status="blocked",
                detail=(
                    "manifest command trust is blocked "
                    f"({trust_status.reason})"
                ),
            )
    return preflights


def workspace_test_command_text(command: str, runner: str | None) -> str:
    if runner is None:
        return command
    return f"{runner}: {command}"


def blocked_workspace_test_results(
    targets: tuple[WorkspaceTestTarget, ...],
    preflights: dict[str, WorkspaceTestPreflight],
) -> list[tuple[WorkspaceTestTarget, WorkspaceTestResult]]:
    results: list[tuple[WorkspaceTestTarget, WorkspaceTestResult]] = []
    for target in targets:
        preflight = preflights[target.name]
        if target.action == "skip":
            status: WorkspaceTestStatus = "failed" if target.fatal else "skipped"
            result = WorkspaceTestResult(status, target.reason)
        elif preflight.status == "blocked":
            result = WorkspaceTestResult(
                "blocked",
                preflight.detail,
                command=preflight.command,
                trust_status="blocked",
            )
        elif preflight.status == "allowed":
            result = WorkspaceTestResult(
                "not_run",
                "not run because another selected project's trust preflight blocked execution",
                command=preflight.command,
                trust_status="allowed",
            )
        else:
            result = WorkspaceTestResult("failed", preflight.detail)
        results.append((target, result))
    return results


def dry_run_workspace_test_results(
    targets: tuple[WorkspaceTestTarget, ...],
    preflights: dict[str, WorkspaceTestPreflight],
) -> list[tuple[WorkspaceTestTarget, WorkspaceTestResult]]:
    results: list[tuple[WorkspaceTestTarget, WorkspaceTestResult]] = []
    for target in targets:
        preflight = preflights[target.name]
        if target.action == "skip":
            status: WorkspaceTestStatus = "failed" if target.fatal else "skipped"
            result = WorkspaceTestResult(status, target.reason)
        else:
            result = WorkspaceTestResult(
                "not_run",
                "not run because --dry-run only plans execution",
                command=preflight.command,
                trust_status=preflight.trust_status,
            )
        results.append((target, result))
    return results


def execute_workspace_test_target(
    ctx: base_cli.Context,
    basectl: Path,
    workspace_root: Path,
    target: WorkspaceTestTarget,
    preflight: WorkspaceTestPreflight,
) -> WorkspaceTestResult:
    if target.project_name is None:
        return WorkspaceTestResult("failed", "test target is missing project routing metadata")

    # Resolve the current project from the already selected checkout. A named
    # lookup would rescan unrelated siblings and can redirect duplicate names.
    command = [
        str(basectl),
        "test",
        "--workspace",
        str(workspace_root),
    ]
    env = os.environ.copy()
    env["BASE_HOME"] = str(ctx.application_home)
    for variable in ("BASE_PROJECT", "BASE_PROJECT_ROOT", "BASE_PROJECT_MANIFEST", "BASE_PROJECT_VENV_DIR"):
        env.pop(variable, None)

    started_at = time.monotonic()
    try:
        result = run_workspace_subprocess(
            command,
            cwd=target.root,
            env=env,
            timeout=WORKSPACE_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return WorkspaceTestResult(
            "failed",
            f"timed out after {WORKSPACE_TEST_TIMEOUT_SECONDS} seconds",
            command=preflight.command,
            trust_status=preflight.trust_status,
            executed=True,
            duration_seconds=round(time.monotonic() - started_at, 3),
        )
    except OSError as exc:
        return WorkspaceTestResult(
            "failed",
            f"could not run test command: {exc}",
            command=preflight.command,
            trust_status=preflight.trust_status,
            executed=True,
            duration_seconds=round(time.monotonic() - started_at, 3),
        )

    stdout = redact_command_output(decode_subprocess_output(result.stdout))
    stderr = redact_command_output(decode_subprocess_output(result.stderr))
    duration_seconds = round(time.monotonic() - started_at, 3)
    if result.returncode == 0:
        return WorkspaceTestResult(
            "passed",
            stdout=stdout,
            stderr=stderr,
            command=preflight.command,
            trust_status=preflight.trust_status,
            executed=True,
            duration_seconds=duration_seconds,
        )
    if "Manifest command trust is blocked" in stderr or "Manifest-declared commands are not allowed" in stderr:
        return WorkspaceTestResult(
            "blocked",
            "manifest command trust became blocked before the project test command ran",
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            command=preflight.command,
            trust_status="blocked",
            duration_seconds=duration_seconds,
        )
    return WorkspaceTestResult(
        "failed",
        f"test command exited with status {result.returncode}",
        exit_code=result.returncode,
        stdout=stdout,
        stderr=stderr,
        command=preflight.command,
        trust_status=preflight.trust_status,
        executed=True,
        duration_seconds=duration_seconds,
    )


def update_workspace_test_counts(
    counts: WorkspaceTestCounts,
    result: WorkspaceTestResult,
) -> WorkspaceTestCounts:
    if result.status == "passed":
        return WorkspaceTestCounts(counts.passed + 1, counts.failed, counts.blocked, counts.not_run, counts.skipped)
    if result.status == "failed":
        return WorkspaceTestCounts(counts.passed, counts.failed + 1, counts.blocked, counts.not_run, counts.skipped)
    if result.status == "blocked":
        return WorkspaceTestCounts(counts.passed, counts.failed, counts.blocked + 1, counts.not_run, counts.skipped)
    if result.status == "not_run":
        return WorkspaceTestCounts(counts.passed, counts.failed, counts.blocked, counts.not_run + 1, counts.skipped)
    return WorkspaceTestCounts(counts.passed, counts.failed, counts.blocked, counts.not_run, counts.skipped + 1)


def print_workspace_test_header(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    targets: tuple[WorkspaceTestTarget, ...],
    *,
    dry_run: bool,
) -> None:
    print(f"Workspace test: {workspace_root} ({len(targets)} projects)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print("Execution policy: trust preflight must pass for every selected project before any test starts.")
    if dry_run:
        print("Mode: dry-run (planning only; no project test commands will execute).")


def print_workspace_test_preflight(
    targets: tuple[WorkspaceTestTarget, ...],
    preflights: dict[str, WorkspaceTestPreflight],
) -> None:
    print(f"Workspace test preflight: {len(targets)} selected projects.")
    for index, target in enumerate(targets, start=1):
        project = target.project_name or target.name
        preflight = preflights[target.name]
        if preflight.status == "allowed":
            print(f"  [{index}/{len(targets)}] ALLOW project '{project}' (trust=allowed)")
            print(f"      command: {preflight.command}")
        elif preflight.status == "blocked":
            print(f"  [{index}/{len(targets)}] BLOCK project '{project}' (trust=blocked)")
            print(f"      command: {preflight.command}")
            print(f"      reason: {preflight.detail}")
        elif preflight.status == "failed":
            print(f"  [{index}/{len(targets)}] ERROR project '{project}' (preflight failed)")
            print(f"      reason: {preflight.detail}")
        else:
            print(f"  [{index}/{len(targets)}] SKIP project '{project}': {preflight.detail}")


def print_workspace_test_start(
    index: int,
    total: int,
    target: WorkspaceTestTarget,
    preflight: WorkspaceTestPreflight,
) -> None:
    project = target.project_name or target.name
    print(f"[{index}/{total}] START project '{project}' (trust={preflight.trust_status})", flush=True)
    print(f"      command: {preflight.command}", flush=True)


def print_workspace_test_result(
    target: WorkspaceTestTarget,
    result: WorkspaceTestResult,
    *,
    show_output: bool = True,
) -> None:
    project = target.project_name or target.name
    if result.status == "passed":
        print(f"PASS project '{project}' at '{target.root}' ({result.duration_seconds or 0:.3f}s).")
    elif result.status == "failed":
        print(f"FAIL project '{project}' at '{target.root}': {result.detail}.")
    elif result.status == "blocked":
        print(f"BLOCKED project '{project}' at '{target.root}': {result.detail}.")
        print("  No project test command was executed.")
    elif result.status == "not_run":
        print(f"NOT RUN project '{project}' at '{target.root}': {result.detail}.")
    else:
        print(f"SKIP project '{project}' at '{target.root}': {result.detail}.")
    if show_output and result.stdout:
        print(result.stdout, end="")
    if show_output and result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def print_workspace_test_blocked_summary(
    targets: tuple[WorkspaceTestTarget, ...],
    preflight_blocked: bool,
    preflight_failed: bool,
) -> None:
    test_count = sum(target.action == "test" for target in targets)
    reason = "trust is blocked" if preflight_blocked else "trust preflight failed"
    print("EXECUTION BLOCKED: No project test command was executed.")
    print(f"Workspace test execution blocked: {reason}; 0/{test_count} project test commands started.")
    if preflight_failed:
        print("Review the preflight errors before retrying.")


def print_workspace_test_summary(counts: WorkspaceTestCounts, *, execution_started: bool) -> None:
    label = "Workspace test completed" if execution_started else "Workspace test not executed"
    print(
        f"{label}: "
        f"passed={counts.passed} failed={counts.failed} blocked={counts.blocked} "
        f"not_run={counts.not_run} skipped={counts.skipped}; "
        f"execution_started={'yes' if execution_started else 'no'}."
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
    preflight_status: Literal["passed", "blocked"],
    execution_started: bool,
    dry_run: bool,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": 2,
        "workspace": str(workspace_root),
        "workspace_manifest": {
            "path": str(workspace_manifest.path),
            "name": workspace_manifest.name,
            "schema_version": workspace_manifest.schema_version,
        },
        "fail_fast": fail_fast,
        "preflight": preflight_status,
        "execution_started": execution_started,
        "dry_run": dry_run,
        "selected_projects": [target.project_name or target.name for target in targets],
        "project_count": len(targets),
        "projects": [workspace_test_project_to_json(target, result) for target, result in results],
        "counts": {
            "passed": counts.passed,
            "failed": counts.failed,
            "blocked": counts.blocked,
            "not_run": counts.not_run,
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
    if result.command is not None:
        payload["command"] = result.command
    if result.trust_status is not None:
        payload["trust_status"] = result.trust_status
    payload["executed"] = result.executed
    if result.duration_seconds is not None:
        payload["duration_seconds"] = result.duration_seconds
    return payload
