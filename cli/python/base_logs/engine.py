from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import base_cli
from base_cli.history import HISTORY_PATH
from base_cli.history import compact_path
from base_cli.history import display_command
from base_cli.history import optional_int
from base_cli.history import optional_string
from base_cli.history import parse_finished_history_record_line
from base_cli.history import parse_positive_int
from base_cli.history import redact_history_argv
from base_cli.history import redact_history_text
from base_cli.paths import base_cache_root
from base_cli.redaction import REDACTED
from base_cli.redaction import redact_text_value


RUN_ID_RE = re.compile(r"^(?P<stamp>\d{8}T\d{6})_[A-Za-z0-9]+$")
LOG_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>\b[A-Za-z_][A-Za-z0-9_.-]*)=(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
SECRET_KEY_RE = re.compile(r"token|password|secret|api[-_]?key|authorization", re.IGNORECASE)

app = base_cli.App(name="base_logs", log_to_file=False)


@dataclass(frozen=True)
class LogEntry:
    command: str
    raw_command: str
    run_id: str
    path: Path
    timestamp: datetime
    status: str
    exit_code: int | None = None


@dataclass(frozen=True)
class LogCommandOptions:
    command_filter: str | None
    limit: int
    path_only: bool
    tail: bool
    open_file: bool
    lines: int
    output_format: str


@dataclass(frozen=True)
class LastFailureRecord:
    payload: dict[str, Any]
    run_id: str
    command: str
    raw_command: str | None
    project: str | None
    status: str
    exit_code: int | None
    ended_at: str
    sort_time: datetime
    log_path: str | None

    @property
    def log_file(self) -> Path | None:
        if not self.log_path:
            return None
        return Path(self.log_path).expanduser()

    @property
    def log_exists(self) -> bool:
        log_file = self.log_file
        return log_file is not None and log_file.is_file()


@dataclass(frozen=True)
class LogTail:
    lines: list[str]
    requested_lines: int
    truncated: bool
    available: bool


@dataclass(frozen=True)
class HistoryLogStatus:
    status: str
    exit_code: int | None
    command: str | None


@dataclass(frozen=True)
class HistoryLogStatusIndex:
    by_run_id: dict[str, HistoryLogStatus]
    by_log_path: dict[str, HistoryLogStatus]


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--command", "command_filter", help="Filter by basectl command or Python CLI name.")
@base_cli.option("--limit", default="10", help="Maximum log entries to list.")
@base_cli.option("--path", "path_only", is_flag=True, help="Print the most recent matching log path only.")
@base_cli.option("--tail", is_flag=True, help="Tail and follow the most recent matching log.")
@base_cli.option("--open", "open_file", is_flag=True, help="Open the most recent matching log in PAGER or EDITOR.")
@base_cli.option("--lines", default="40", help="Line count to show before following.")
@base_cli.option("--format", "output_format", default="text", help="Output format for logs last: text or json.")
@base_cli.argument("action", required=False)
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    action: str | None,
    command_filter: str | None,
    limit: str,
    path_only: bool,
    tail: bool,
    open_file: bool,
    lines: str,
    output_format: str,
) -> int:
    try:
        limit_value = parse_positive_int("--limit", limit)
        line_count = parse_positive_int("--lines", lines)
        normalized_format = normalize_logs_format(output_format)
    except ValueError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    options = LogCommandOptions(
        command_filter=command_filter,
        limit=limit_value,
        path_only=path_only,
        tail=tail,
        open_file=open_file,
        lines=line_count,
        output_format=normalized_format,
    )
    selected_actions = sum(1 for selected in (path_only, tail, open_file) if selected)
    validation_error = logs_command_validation_error(action, normalized_format, selected_actions)
    if validation_error is not None:
        ctx.log.error(validation_error)
        return base_cli.ExitCode.USAGE_ERROR

    cache_root = base_cache_root()
    if action == "last":
        return run_last_failure(ctx, cache_root, options)

    return run_recent_logs(ctx, cache_root, options)


def logs_command_validation_error(action: str | None, output_format: str, selected_actions: int) -> str | None:
    if action is not None and action != "last":
        return f"Unknown logs command '{action}'. Supported commands: last."
    if action == "last" and selected_actions > 0:
        return "`basectl logs last` does not accept --path, --tail, or --open."
    if action is None and output_format != "text":
        return "Option '--format' is only supported with `basectl logs last`."
    if action is None and selected_actions > 1:
        return "Choose only one of --path, --tail, or --open."
    return None


def run_recent_logs(ctx: base_cli.Context, cache_root: Path, options: LogCommandOptions) -> int:
    ctx.log.debug("Scanning Base cache root '%s'.", cache_root)
    entries = recent_logs(cache_root, command_filter=options.command_filter)
    if not entries:
        return report_no_logs(ctx, cache_root, options)
    return run_with_entries(entries, options)


def normalize_logs_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"text", "json"}:
        raise ValueError(f"Unsupported output format '{value}'. Expected one of: text, json.")
    return normalized


def report_no_logs(ctx: base_cli.Context, cache_root: Path, options: LogCommandOptions) -> int:
    if options.path_only or options.tail or options.open_file:
        ctx.log.error("No Base CLI logs found.")
        return base_cli.ExitCode.FAILURE
    print(f"No Base CLI logs found under {cache_root / 'cli'}.")
    return base_cli.ExitCode.SUCCESS


def run_with_entries(entries: list[LogEntry], options: LogCommandOptions) -> int:
    newest = entries[0]
    if options.path_only:
        print(newest.path)
        return base_cli.ExitCode.SUCCESS
    if options.tail:
        return tail_log(newest.path, options.lines)
    if options.open_file:
        return open_log(newest.path)

    print_log_table(entries[: options.limit])
    return base_cli.ExitCode.SUCCESS


def run_last_failure(ctx: base_cli.Context, cache_root: Path, options: LogCommandOptions) -> int:
    record = latest_failed_history_record(cache_root, command_filter=options.command_filter, logger=ctx.log)
    history_path = cache_root / HISTORY_PATH
    if record is None:
        if options.output_format == "json":
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "found": False,
                        "history_path": redact_history_text(str(history_path)),
                        "message": "No failed Base command history found.",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"No failed Base command history found under {history_path}.")
        return base_cli.ExitCode.SUCCESS

    tail = last_failure_tail(record, options.lines)
    if options.output_format == "json":
        print(json.dumps(last_failure_to_json(record, tail), indent=2, sort_keys=True))
    else:
        print_last_failure_text(record, tail)
    return base_cli.ExitCode.SUCCESS


def latest_failed_history_record(
    cache_root: Path,
    command_filter: str | None = None,
    logger: Any | None = None,
) -> LastFailureRecord | None:
    records = read_failed_history_records(cache_root, logger=logger)
    if command_filter:
        normalized = normalize_command_filter(command_filter)
        records = [
            record
            for record in records
            if normalize_command_filter(record.command) == normalized
            or (
                record.raw_command is not None
                and normalize_command_filter(record.raw_command) == normalized
            )
        ]
    if not records:
        return None
    return sorted(records, key=lambda record: (record.sort_time, record.run_id), reverse=True)[0]


def read_failed_history_records(cache_root: Path, logger: Any | None = None) -> list[LastFailureRecord]:
    path = cache_root / HISTORY_PATH
    if not path.is_file():
        return []

    records: list[LastFailureRecord] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = parse_last_failure_history_line(line)
            if record is None:
                if logger is not None:
                    logger.debug("Ignoring malformed or non-failing history line %s in '%s'.", line_number, path)
                continue
            records.append(record)
    return records


def parse_last_failure_history_line(line: str) -> LastFailureRecord | None:
    payload = parse_finished_history_record_line(line)
    if payload is None:
        return None

    run_id = optional_string(payload.get("run_id"))
    command = optional_string(payload.get("command"))
    status = optional_string(payload.get("status"))
    if not run_id or not command or not status:
        return None

    exit_code = optional_int(payload.get("exit_code"))
    if not history_payload_failed(status, exit_code):
        return None

    ended_at = optional_string(payload.get("ended_at")) or optional_string(payload.get("started_at")) or ""
    return LastFailureRecord(
        payload=payload,
        run_id=run_id,
        command=command,
        raw_command=optional_string(payload.get("raw_command")),
        project=optional_string(payload.get("project")),
        status=status,
        exit_code=exit_code,
        ended_at=ended_at,
        sort_time=parse_history_timestamp(ended_at),
        log_path=optional_string(payload.get("log_path")),
    )


def history_payload_failed(status: str, exit_code: int | None) -> bool:
    return status == "error" or (exit_code is not None and exit_code != 0)


def parse_history_timestamp(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def last_failure_tail(record: LastFailureRecord, line_count: int) -> LogTail:
    log_file = record.log_file
    if log_file is None or not log_file.is_file():
        return LogTail(lines=[], requested_lines=line_count, truncated=False, available=False)
    return read_redacted_tail(log_file, line_count)


def read_redacted_tail(path: Path, line_count: int) -> LogTail:
    buffered: deque[str] = deque(maxlen=line_count + 1)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            buffered.append(redact_log_line(line.rstrip("\n")))
    truncated = len(buffered) > line_count
    lines = list(buffered)
    if truncated:
        lines = lines[1:]
    return LogTail(lines=lines, requested_lines=line_count, truncated=truncated, available=True)


def redact_log_line(value: str) -> str:
    text = redact_text_value(value)
    return LOG_SECRET_ASSIGNMENT_RE.sub(redact_log_secret_assignment, text)


def redact_log_secret_assignment(match: re.Match[str]) -> str:
    key = match.group("key")
    if SECRET_KEY_RE.search(key):
        return f"{key}={REDACTED}"
    return match.group(0)


def print_last_failure_text(record: LastFailureRecord, tail: LogTail) -> None:
    print("Latest failed Base command")
    print(f"Time: {display_last_value(record.ended_at)}")
    print(f"Command: {redact_history_text(record.command)}")
    print(f"Project: {redact_history_text(record.project) if record.project else '-'}")
    print(f"Status: {redact_history_text(record.status)}")
    print(f"Exit: {record.exit_code if record.exit_code is not None else '-'}")
    print(f"Run ID: {redact_history_text(record.run_id)}")
    print(f"Log: {display_last_log_path(record)}")
    argv = redacted_last_argv(record)
    if argv:
        print(f"Argv: {' '.join(argv)}")

    if record.log_path is None:
        print()
        print("No log path was recorded for this failed run. Use `basectl history --status error` for metadata.")
        return
    if not tail.available:
        print()
        print("The recorded log file is missing or was cleaned. Use `basectl history --status error` for metadata.")
        return

    print()
    suffix = " (truncated)" if tail.truncated else ""
    print(f"Log tail (last {tail.requested_lines} lines{suffix}):")
    for line in tail.lines:
        print(line)


def display_last_value(value: str) -> str:
    return redact_history_text(value) if value else "-"


def display_last_log_path(record: LastFailureRecord) -> str:
    if not record.log_path:
        return "-"
    suffix = "" if record.log_exists else " (missing)"
    return f"{redact_history_text(record.log_path)}{suffix}"


def redacted_last_argv(record: LastFailureRecord) -> list[str]:
    value = record.payload.get("argv")
    if not isinstance(value, list):
        return []
    return redact_history_argv([str(arg) for arg in value], sensitive_options=set())


def last_failure_to_json(record: LastFailureRecord, tail: LogTail) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "found": True,
        "run": {
            "run_id": redact_history_text(record.run_id),
            "command": redact_history_text(record.command),
            "raw_command": redact_history_text(record.raw_command) if record.raw_command else None,
            "project": redact_history_text(record.project) if record.project else None,
            "status": redact_history_text(record.status),
            "exit_code": record.exit_code,
            "ended_at": redact_history_text(record.ended_at),
            "log_path": redact_history_text(record.log_path) if record.log_path else None,
            "log_exists": record.log_exists,
            "argv": redacted_last_argv(record),
        },
        "tail": {
            "available": tail.available,
            "requested_lines": tail.requested_lines,
            "truncated": tail.truncated,
            "lines": tail.lines,
        },
    }


def recent_logs(cache_root: Path, command_filter: str | None = None) -> list[LogEntry]:
    entries = list(discover_log_entries(cache_root))
    if command_filter:
        normalized = normalize_command_filter(command_filter)
        entries = [
            entry
            for entry in entries
            if normalize_command_filter(entry.command) == normalized
            or normalize_command_filter(entry.raw_command) == normalized
        ]
    return sorted(entries, key=lambda entry: (entry.timestamp, entry.path.name), reverse=True)


def discover_log_entries(cache_root: Path) -> list[LogEntry]:
    cli_root = cache_root / "cli"
    if not cli_root.is_dir():
        return []

    history_statuses = read_history_log_statuses(cache_root)
    entries: list[LogEntry] = []
    for logs_dir in sorted(cli_root.glob("*/logs"), key=str):
        if not logs_dir.is_dir():
            continue
        raw_command = logs_dir.parent.name
        for path in sorted(logs_dir.glob("*.log"), key=lambda item: item.name):
            if not path.is_file():
                continue
            history_status = history_status_for_log(history_statuses, run_id=path.stem, path=path)
            entries.append(
                LogEntry(
                    command=history_status.command
                    if history_status is not None and history_status.command is not None
                    else infer_display_command(raw_command, path),
                    raw_command=raw_command,
                    run_id=path.stem,
                    path=path,
                    timestamp=entry_timestamp(path),
                    status=history_status.status if history_status is not None else infer_status(path),
                    exit_code=history_status.exit_code if history_status is not None else None,
                )
            )
    return entries


def read_history_log_statuses(cache_root: Path) -> HistoryLogStatusIndex:
    path = cache_root / HISTORY_PATH
    index = HistoryLogStatusIndex(by_run_id={}, by_log_path={})
    if not path.is_file():
        return index

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = parse_history_log_status_line(line)
            if record is None:
                continue
            run_id, log_path, history_status = record
            index.by_run_id[run_id] = history_status
            if log_path is not None:
                index.by_log_path[normalize_history_log_path(log_path)] = history_status
    return index


def parse_history_log_status_line(line: str) -> tuple[str, str | None, HistoryLogStatus] | None:
    payload = parse_finished_history_record_line(line)
    if payload is None:
        return None

    run_id = optional_string(payload.get("run_id"))
    status = optional_string(payload.get("status"))
    if run_id is None or status is None:
        return None

    return (
        run_id,
        optional_string(payload.get("log_path")),
        HistoryLogStatus(
            status=status,
            exit_code=optional_int(payload.get("exit_code")),
            command=optional_string(payload.get("command")),
        ),
    )


def history_status_for_log(index: HistoryLogStatusIndex, run_id: str, path: Path) -> HistoryLogStatus | None:
    return index.by_run_id.get(run_id) or index.by_log_path.get(normalize_history_log_path(str(path)))


def normalize_history_log_path(value: str) -> str:
    return str(Path(value).expanduser().resolve(strict=False))


def infer_display_command(raw_command: str, path: Path) -> str:
    if raw_command == "base_setup":
        action = infer_base_setup_action(path)
        return action or display_command(raw_command, [])
    return display_command(raw_command, [])


def infer_base_setup_action(path: Path) -> str | None:
    try:
        for line in first_lines(path, limit=20):
            for action in ("setup", "bootstrap", "check", "doctor"):
                if f"'--action', '{action}'" in line or f'"--action", "{action}"' in line:
                    return action
                if f"--action {action}" in line:
                    return action
    except OSError:
        return None
    return None


def first_lines(path: Path, limit: int) -> list[str]:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for _index, line in zip(range(limit), handle):
            lines.append(line.rstrip("\n"))
    return lines


def entry_timestamp(path: Path) -> datetime:
    match = RUN_ID_RE.match(path.stem)
    if match is not None:
        try:
            return datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%S")
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def infer_status(path: Path) -> str:
    try:
        line = last_nonempty_line(path)
    except OSError:
        return "?"
    if line is None:
        return "?"
    if " FATAL " in line or " ERROR " in line:
        return "error"
    if " WARN " in line:
        return "warn"
    return "ok"


def last_nonempty_line(path: Path) -> str | None:
    last_line = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.rstrip("\n")
            if stripped:
                last_line = stripped
    return last_line


def normalize_command_filter(value: str) -> str:
    normalized = value.removeprefix("base_")
    return normalized.replace("_", "-")


def print_log_table(entries: list[LogEntry]) -> None:
    print(f"{'TIME':<19}  {'COMMAND':<12}  {'RUN ID':<24}  {'STATUS':<6}  PATH")
    for entry in entries:
        print(
            f"{entry.timestamp:%Y-%m-%d %H:%M:%S}  "
            f"{entry.command:<12}  "
            f"{entry.run_id:<24}  "
            f"{entry.status:<6}  "
            f"{compact_path(entry.path)}"
        )


def tail_log(path: Path, lines: int) -> int:
    tail = shutil.which("tail")
    if tail is None:
        print(f"ERROR: tail was not found on PATH. Log path: {path}", file=sys.stderr)
        return base_cli.ExitCode.FAILURE
    os.execv(tail, [tail, "-n", str(lines), "-f", str(path)])
    return base_cli.ExitCode.FAILURE


def open_log(path: Path) -> int:
    command = os.environ.get("PAGER") or os.environ.get("EDITOR")
    if not command:
        print(path)
        return base_cli.ExitCode.SUCCESS

    args = shlex.split(command)
    if not args:
        print(path)
        return base_cli.ExitCode.SUCCESS
    if shutil.which(args[0]) is None:
        print(f"ERROR: {args[0]} was not found on PATH. Log path: {path}", file=sys.stderr)
        return base_cli.ExitCode.FAILURE
    # Interactive pager/editor path: intentionally block until the user exits.
    return subprocess.call([*args, str(path)])
