from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import base_cli
from base_setup.process import redact_command_argv
from base_setup.process import redact_command_output


SCHEMA_VERSION = 1
MATRIX_CELLS: dict[str, dict[str, str]] = {
    "source-bash": {"account": "base-source-bash", "route": "source", "shell": "bash"},
    "source-zsh": {"account": "base-source-zsh", "route": "source", "shell": "zsh"},
    "brew-bash": {"account": "base-brew-bash", "route": "homebrew", "shell": "bash"},
    "brew-zsh": {"account": "base-brew-zsh", "route": "homebrew", "shell": "zsh"},
}
ALL_CELLS = tuple(MATRIX_CELLS)


class MatrixUsageError(ValueError):
    """Raised when a scenario or runner argument is invalid."""


@dataclass(frozen=True)
class Step:
    step_id: str
    command: tuple[str, ...]
    expected_exit: int
    stdout_contains: tuple[str, ...]
    stderr_contains: tuple[str, ...]
    stdout_not_contains: tuple[str, ...]
    stderr_not_contains: tuple[str, ...]
    finding_ids: tuple[str, ...]
    timeout_seconds: float
    cwd: str | None


@dataclass(frozen=True)
class Scenario:
    name: str
    version: str
    description: str
    preconditions: tuple[Step, ...]
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class RunContext:
    base_ref: str
    base_commit: str
    run_id: str
    repo_root: Path
    output_dir: Path


@dataclass(frozen=True)
class StepOutcome:
    command: Sequence[str]
    log_path: str
    result: subprocess.CompletedProcess[str] | None
    duration_ms: int
    status: str
    extra_findings: Sequence[str] = ()
    error: str = ""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_string_list(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise MatrixUsageError(f"{field} must be an array of strings")
    return tuple(value)


def _parse_step(value: object, location: str) -> Step:
    if not isinstance(value, dict):
        raise MatrixUsageError(f"{location} must be an object")
    step_id = value.get("id")
    command = value.get("command")
    expected_exit = value.get("expected_exit", 0)
    timeout_seconds = value.get("timeout_seconds", 300)
    cwd = value.get("cwd")
    if not isinstance(step_id, str) or not step_id:
        raise MatrixUsageError(f"{location}.id must be a non-empty string")
    if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
        raise MatrixUsageError(f"{location}.command must be a non-empty array of non-empty strings")
    if not isinstance(expected_exit, int) or expected_exit < 0 or expected_exit > 255:
        raise MatrixUsageError(f"{location}.expected_exit must be an integer from 0 to 255")
    if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise MatrixUsageError(f"{location}.timeout_seconds must be greater than zero")
    if cwd is not None and (not isinstance(cwd, str) or not cwd):
        raise MatrixUsageError(f"{location}.cwd must be a non-empty string when provided")
    return Step(
        step_id=step_id,
        command=tuple(command),
        expected_exit=expected_exit,
        stdout_contains=_as_string_list(value.get("stdout_contains"), f"{location}.stdout_contains"),
        stderr_contains=_as_string_list(value.get("stderr_contains"), f"{location}.stderr_contains"),
        stdout_not_contains=_as_string_list(value.get("stdout_not_contains"), f"{location}.stdout_not_contains"),
        stderr_not_contains=_as_string_list(value.get("stderr_not_contains"), f"{location}.stderr_not_contains"),
        finding_ids=_as_string_list(value.get("finding_ids"), f"{location}.finding_ids"),
        timeout_seconds=float(timeout_seconds),
        cwd=cwd,
    )


def load_scenario(path: Path) -> Scenario:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MatrixUsageError(f"Unable to read scenario '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MatrixUsageError(f"Scenario '{path}' is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise MatrixUsageError("Scenario root must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise MatrixUsageError(f"Scenario schema_version must be {SCHEMA_VERSION}")
    name = payload.get("name")
    version = payload.get("version")
    if not isinstance(name, str) or not name:
        raise MatrixUsageError("Scenario name must be a non-empty string")
    if not isinstance(version, str) or not version:
        raise MatrixUsageError("Scenario version must be a non-empty string")
    preconditions = payload.get("preconditions", [])
    steps = payload.get("steps")
    if not isinstance(preconditions, list):
        raise MatrixUsageError("Scenario preconditions must be an array")
    if not isinstance(steps, list) or not steps:
        raise MatrixUsageError("Scenario steps must be a non-empty array")
    parsed_preconditions = tuple(
        _parse_step(item, f"preconditions[{index}]") for index, item in enumerate(preconditions)
    )
    parsed_steps = tuple(_parse_step(item, f"steps[{index}]") for index, item in enumerate(steps))
    ids = [step.step_id for step in (*parsed_preconditions, *parsed_steps)]
    if len(ids) != len(set(ids)):
        raise MatrixUsageError("Scenario step ids must be unique across preconditions and steps")
    return Scenario(
        name=name,
        version=version,
        description=str(payload.get("description", "")),
        preconditions=parsed_preconditions,
        steps=parsed_steps,
    )


def _git_value(repo_root: Path, ref: str) -> tuple[str, str]:
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", f"{ref}^{{commit}}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise MatrixUsageError(f"Unable to resolve Base ref '{ref}': {exc}") from exc
    if commit.returncode != 0 or not commit.stdout.strip():
        raise MatrixUsageError(f"Unable to resolve Base ref '{ref}': {commit.stderr.strip()}")
    return ref, commit.stdout.strip()


def _repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=False, capture_output=True, text=True
        )
    except OSError as exc:
        raise MatrixUsageError(f"Unable to find the Base checkout: {exc}") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise MatrixUsageError("The matrix runner must run inside a Base Git checkout")
    return Path(result.stdout.strip()).resolve()


def _redacted_command(command: Sequence[str]) -> list[str]:
    return redact_command_argv([str(item) for item in command])


def _log_step(
    log_path: Path,
    command: Sequence[str],
    result: subprocess.CompletedProcess[str] | None,
    error: str = "",
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"Command: {shlex.join(_redacted_command(command))}"]
    if result is not None:
        lines.extend(
            [
                f"Exit code: {result.returncode}",
                "--- stdout ---",
                redact_command_output(result.stdout or ""),
                "--- stderr ---",
                redact_command_output(result.stderr or ""),
            ]
        )
    if error:
        lines.extend(["--- runner error ---", redact_command_output(error)])
    log_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    os.chmod(log_path, 0o600)


def _step_result(
    step: Step,
    outcome: StepOutcome,
) -> dict[str, Any]:
    actual_exit = outcome.result.returncode if outcome.result is not None else None
    finding_ids = list(dict.fromkeys((*step.finding_ids, *outcome.extra_findings)))
    return {
        "id": step.step_id,
        "command": _redacted_command(outcome.command),
        "expected_exit": step.expected_exit,
        "actual_exit": actual_exit,
        "status": outcome.status,
        "duration_ms": outcome.duration_ms,
        "finding_ids": finding_ids,
        "log_path": outcome.log_path,
        **({"error": redact_command_output(outcome.error)} if outcome.error else {}),
    }


def _assert_step(step: Step, result: subprocess.CompletedProcess[str]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != step.expected_exit:
        failures.append(f"exit-{result.returncode}")
    failures.extend(
        f"stdout-missing-{index}" for index, expected in enumerate(step.stdout_contains) if expected not in stdout
    )
    failures.extend(
        f"stderr-missing-{index}" for index, expected in enumerate(step.stderr_contains) if expected not in stderr
    )
    failures.extend(
        f"stdout-forbidden-{index}"
        for index, forbidden in enumerate(step.stdout_not_contains)
        if forbidden in stdout
    )
    failures.extend(
        f"stderr-forbidden-{index}"
        for index, forbidden in enumerate(step.stderr_not_contains)
        if forbidden in stderr
    )
    return not failures, failures


def _run_step(
    step: Step,
    user: str,
    repo_root: Path,
    output_dir: Path,
    log_name: str,
) -> tuple[dict[str, Any], bool]:
    command = ["sudo", "-n", "-u", user, "-i", "--", *step.command]
    cwd = repo_root if step.cwd is None else (repo_root / step.cwd).resolve()
    try:
        cwd.relative_to(repo_root)
    except ValueError as exc:
        raise MatrixUsageError(f"Step '{step.step_id}' cwd must remain inside the Base checkout") from exc
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=step.timeout_seconds,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        passed, assertion_failures = _assert_step(step, result)
        status = "passed" if passed else "failed"
        log_path = output_dir / log_name
        _log_step(log_path, command, result)
        return (
            _step_result(
                step,
                StepOutcome(
                    command,
                    str(log_path.relative_to(output_dir)),
                    result,
                    duration_ms,
                    status,
                    [f"matrix.{step.step_id}.{failure}" for failure in assertion_failures],
                ),
            ),
            passed,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - started) * 1000)
        log_path = output_dir / log_name
        error = f"step timed out after {step.timeout_seconds:g} seconds"
        _log_step(log_path, command, None, error)
        return (
            _step_result(
                step,
                StepOutcome(
                    command,
                    str(log_path.relative_to(output_dir)),
                    None,
                    duration_ms,
                    "failed",
                    [f"matrix.{step.step_id}.timeout"],
                    error,
                ),
            ),
            False,
        )
    except OSError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        log_path = output_dir / log_name
        error = str(exc)
        _log_step(log_path, command, None, error)
        return (
            _step_result(
                step,
                StepOutcome(
                    command,
                    str(log_path.relative_to(output_dir)),
                    None,
                    duration_ms,
                    "failed",
                    [f"matrix.{step.step_id}.runner-error"],
                    error,
                ),
            ),
            False,
        )


def _runas_preflight(user: str, output_dir: Path) -> tuple[dict[str, Any], bool]:
    step = Step("runas", ("/usr/bin/true",), 0, (), (), (), (), (), 30.0, None)
    command = ["sudo", "-n", "-u", user, "-i", "--", *step.command]
    started = time.monotonic()
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=step.timeout_seconds)
        duration_ms = int((time.monotonic() - started) * 1000)
        passed = result.returncode == 0
        log_path = output_dir / "logs" / "00-runas.log"
        _log_step(log_path, command, result)
        error = "" if passed else "passwordless sudo runas is unavailable for this matrix account"
        return (
            _step_result(
                step,
                StepOutcome(
                    command,
                    str(log_path.relative_to(output_dir)),
                    result,
                    duration_ms,
                    "passed" if passed else "blocked",
                    () if passed else ("matrix.runas.unavailable",),
                    error,
                ),
            ),
            passed,
        )
    except (OSError, subprocess.TimeoutExpired):
        duration_ms = int((time.monotonic() - started) * 1000)
        log_path = output_dir / "logs" / "00-runas.log"
        error = "passwordless sudo runas is unavailable for this matrix account"
        _log_step(log_path, command, None, error)
        return (
            _step_result(
                step,
                StepOutcome(
                    command,
                    str(log_path.relative_to(output_dir)),
                    None,
                    duration_ms,
                    "blocked",
                    ("matrix.runas.unavailable",),
                    error,
                ),
            ),
            False,
        )


def _run_cell(scenario: Scenario, cell: str, context: RunContext) -> tuple[dict[str, Any], bool]:
    cell_info = MATRIX_CELLS[cell]
    account = cell_info["account"]
    started_at = _utc_now()
    cell_dir = context.output_dir / cell
    cell_dir.mkdir(parents=True, exist_ok=True)
    precondition_results: list[dict[str, Any]] = []
    step_results: list[dict[str, Any]] = []
    runas_result, runas_ok = _runas_preflight(account, cell_dir)
    precondition_results.append(runas_result)
    status = "passed"
    if not runas_ok:
        status = "blocked"
    else:
        for index, step in enumerate(scenario.preconditions, start=1):
            log_name = f"logs/{index:02d}-precondition-{step.step_id}.log"
            result, passed = _run_step(step, account, context.repo_root, cell_dir, log_name)
            precondition_results.append(result)
            if not passed:
                status = "failed"
                break
        if status == "passed":
            for index, step in enumerate(scenario.steps, start=1):
                log_name = f"logs/{index + len(scenario.preconditions):02d}-{step.step_id}.log"
                result, passed = _run_step(step, account, context.repo_root, cell_dir, log_name)
                step_results.append(result)
                if not passed:
                    status = "failed"
                    break
    failed_steps = [item["id"] for item in (*precondition_results, *step_results) if item["status"] != "passed"]
    result_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": context.run_id,
        "scenario": {"name": scenario.name, "version": scenario.version},
        "base": {"ref": context.base_ref, "commit": context.base_commit},
        "platform": {
            "os": platform.system(),
            "os_version": platform.mac_ver()[0] or platform.release(),
            "architecture": platform.machine(),
        },
        "cell": cell,
        "account": account,
        "route": cell_info["route"],
        "shell": cell_info["shell"],
        "started_at": started_at,
        "completed_at": _utc_now(),
        "status": status,
        "preconditions": precondition_results,
        "steps": step_results,
        "summary": {
            "status": status,
            "failed_steps": failed_steps,
            "message": "passed" if status == "passed" else "one or more matrix steps did not pass",
        },
    }
    result_path = context.output_dir / f"{cell}.json"
    result_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(result_path, 0o600)
    return result_payload, status == "passed"


def _write_summary(results: Sequence[dict[str, Any]], output_dir: Path) -> None:
    summary = {
        "schema_version": SCHEMA_VERSION,
        "run_id": results[0]["run_id"] if results else "",
        "results": [
            {"cell": result["cell"], "status": result["status"], "path": f"{result['cell']}.json"}
            for result in results
        ],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(summary_path, 0o600)


def _parse_cells(value: str) -> tuple[str, ...]:
    cells = ALL_CELLS if value == "all" else tuple(part.strip() for part in value.split(",") if part.strip())
    if not cells:
        raise MatrixUsageError("At least one matrix cell is required")
    unknown = [cell for cell in cells if cell not in MATRIX_CELLS]
    if unknown:
        raise MatrixUsageError(f"Unknown matrix cell(s): {', '.join(unknown)}")
    if len(set(cells)) != len(cells):
        raise MatrixUsageError("Matrix cells must be unique")
    return cells


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="base-matrix", description="Run Base's local macOS install-matrix scenarios.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="Validate a scenario file without running it.")
    validate.add_argument("--scenario", required=True, type=Path)
    run = subparsers.add_parser("run", help="Run a scenario through the named matrix accounts.")
    run.add_argument("--scenario", required=True, type=Path)
    run.add_argument("--cells", default="all", help="Comma-separated cells or 'all'.")
    run.add_argument("--user", help="Explicit matrix account; must match the selected single cell.")
    run.add_argument("--output-dir", type=Path, default=Path("artifacts/macos-matrix"))
    run.add_argument("--base-ref", default="HEAD", help="Git ref recorded in results; defaults to HEAD.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario.resolve())
        if args.command == "validate":
            print(f"Scenario valid: {scenario.name} v{scenario.version}")
            return base_cli.ExitCode.SUCCESS
        cells = _parse_cells(args.cells)
        if args.user is not None:
            if len(cells) != 1:
                raise MatrixUsageError("--user requires exactly one selected cell")
            expected_user = MATRIX_CELLS[cells[0]]["account"]
            if args.user != expected_user or args.user not in {info["account"] for info in MATRIX_CELLS.values()}:
                raise MatrixUsageError(f"Refusing non-matrix account '{args.user}' for cell '{cells[0]}'")
        repo_root = _repo_root()
        base_ref, base_commit = _git_value(repo_root, args.base_ref)
        run_id = f"matrix-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        output_dir = args.output_dir.resolve() / run_id
        output_dir.mkdir(parents=True, exist_ok=False)
        context = RunContext(base_ref, base_commit, run_id, repo_root, output_dir)
        results: list[dict[str, Any]] = []
        all_passed = True
        for cell in cells:
            result, passed = _run_cell(scenario, cell, context)
            results.append(result)
            all_passed = all_passed and passed
            print(f"{cell}: {result['status']} ({output_dir / f'{cell}.json'})")
        _write_summary(results, output_dir)
        print(f"Matrix run {run_id}: {'passed' if all_passed else 'failed'}")
        return base_cli.ExitCode.SUCCESS if all_passed else base_cli.ExitCode.FAILURE
    except MatrixUsageError as exc:
        parser.error(str(exc))
    return base_cli.ExitCode.USAGE_ERROR
