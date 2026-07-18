"""Append a primary history record for a Bash-dispatched command."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import base_cli
from base_cli.history import HISTORY_PATH
from base_cli.history import optional_int
from base_cli.history import optional_string
from base_cli.history import parse_finished_history_record_line
from base_cli.history import utc_now
from base_cli.paths import base_cache_root
from base_cli.history import write_primary_record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--started-at")
    parser.add_argument("--project")
    parser.add_argument("--project-root")
    parser.add_argument("--manifest")
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)

    command_argv = list(options.argv)
    if command_argv and command_argv[0] == "--":
        command_argv = command_argv[1:]
    started_at = parse_timestamp(options.started_at) if options.started_at else utc_now()
    write_primary_record(
        command=options.command,
        argv=command_argv,
        started_at=started_at,
        exit_code=options.exit_code,
        run_id=options.run_id,
        project=options.project,
        project_root=options.project_root,
        manifest=options.manifest,
        log_path=child_log_path(options.run_id, options.exit_code),
    )
    return base_cli.ExitCode.SUCCESS


def parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise SystemExit(f"Invalid --started-at timestamp: {value}") from exc


def child_log_path(run_id: str, exit_code: int) -> str | None:
    history_path = base_cache_root() / HISTORY_PATH
    if not history_path.is_file():
        return None

    candidates: list[tuple[int, str, str]] = []
    try:
        with history_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                payload = parse_finished_history_record_line(line)
                if payload is None or payload.get("parent_run_id") != run_id:
                    continue
                log_path = optional_string(payload.get("log_path"))
                if log_path is None:
                    continue
                child_exit_code = optional_int(payload.get("exit_code"))
                failed = payload.get("status") == "error" or (child_exit_code is not None and child_exit_code != 0)
                candidates.append((int(failed), optional_string(payload.get("ended_at")) or "", log_path))
    except OSError:
        return None

    if not candidates:
        return None
    failed_candidates = [candidate for candidate in candidates if candidate[0]]
    selected = max(failed_candidates or candidates, key=lambda candidate: candidate[:2])
    if exit_code == 0 and selected[0]:
        selected = max(candidates, key=lambda candidate: candidate[1])
    return selected[2]


if __name__ == "__main__":
    raise SystemExit(main())
