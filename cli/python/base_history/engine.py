from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import base_cli
from base_cli.history import HISTORY_PATH
from base_cli.history import optional_int
from base_cli.history import optional_string
from base_cli.history import parse_finished_history_record_line
from base_cli.history import parse_positive_int
from base_cli.paths import base_cache_root


app = base_cli.App(name="base_history", log_to_file=False)


@dataclass(frozen=True)
class HistoryRecord:
    payload: dict[str, Any]
    run_id: str
    command: str
    project: str
    status: str
    exit_code: int | None
    ended_at: str
    sort_time: datetime
    log_path: str | None

    @property
    def log_exists(self) -> bool:
        if not self.log_path:
            return False
        return Path(self.log_path).expanduser().is_file()

    def to_json(self) -> dict[str, Any]:
        payload = dict(self.payload)
        payload["log_exists"] = self.log_exists
        return payload


@dataclass(frozen=True)
class HistoryOptions:
    project: str | None
    command: str | None
    status: str | None
    limit: int
    output_format: str


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--project", "project_filter", help="Filter by Base project name.")
@base_cli.option("--command", "command_filter", help="Filter by basectl command name.")
@base_cli.option("--status", "status_filter", help="Filter by status: ok, warn, or error.")
@base_cli.option("--limit", default="10", help="Maximum history records to list.")
@base_cli.option("--format", "output_format", default="text", help="Output format: text or json.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    project_filter: str | None,
    command_filter: str | None,
    status_filter: str | None,
    limit: str,
    output_format: str,
) -> int:
    try:
        options = HistoryOptions(
            project=project_filter,
            command=command_filter,
            status=normalize_optional_filter(status_filter),
            limit=parse_positive_int("--limit", limit),
            output_format=normalize_format(output_format),
        )
    except ValueError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    records = recent_history(base_cache_root(), options=options, logger=ctx.log)
    if options.output_format == "json":
        print(json.dumps([record.to_json() for record in records], indent=2))
        return base_cli.ExitCode.SUCCESS
    if not records:
        print(f"No Base command history found under {base_cache_root() / HISTORY_PATH}.")
        return base_cli.ExitCode.SUCCESS
    print_history_table(records)
    return base_cli.ExitCode.SUCCESS


def normalize_optional_filter(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()


def normalize_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"text", "json"}:
        raise ValueError(f"Unsupported output format '{value}'. Expected one of: text, json.")
    return normalized


def recent_history(
    cache_root: Path,
    options: HistoryOptions | None = None,
    logger: Any | None = None,
) -> list[HistoryRecord]:
    records = list(read_history_records(cache_root, logger=logger))
    if options is not None:
        records = filter_history(records, options)
    sorted_records = sorted(records, key=lambda record: (record.sort_time, record.run_id), reverse=True)
    if options is None:
        return sorted_records
    return sorted_records[: options.limit]


def read_history_records(cache_root: Path, logger: Any | None = None) -> list[HistoryRecord]:
    path = cache_root / HISTORY_PATH
    if not path.is_file():
        return []

    records: list[HistoryRecord] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = parse_history_line(line)
            if record is None:
                if logger is not None:
                    logger.debug("Ignoring malformed history line %s in '%s'.", line_number, path)
                continue
            records.append(record)
    return records


def parse_history_line(line: str) -> HistoryRecord | None:
    payload = parse_finished_history_record_line(line)
    if payload is None:
        return None

    run_id = optional_string(payload.get("run_id"))
    command = optional_string(payload.get("command"))
    status = optional_string(payload.get("status"))
    if not run_id or not command or not status:
        return None

    ended_at = optional_string(payload.get("ended_at")) or optional_string(payload.get("started_at")) or ""
    return HistoryRecord(
        payload=payload,
        run_id=run_id,
        command=command,
        project=optional_string(payload.get("project")) or "",
        status=status,
        exit_code=optional_int(payload.get("exit_code")),
        ended_at=ended_at,
        sort_time=parse_timestamp(ended_at),
        log_path=optional_string(payload.get("log_path")),
    )


def parse_timestamp(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def filter_history(records: list[HistoryRecord], options: HistoryOptions) -> list[HistoryRecord]:
    filtered = records
    if options.project:
        filtered = [record for record in filtered if record.project == options.project]
    if options.command:
        filtered = [record for record in filtered if record.command == options.command]
    if options.status:
        filtered = [record for record in filtered if record.status == options.status]
    return filtered


def print_history_table(records: list[HistoryRecord]) -> None:
    print(f"{'TIME':<19}  {'COMMAND':<12}  {'PROJECT':<12}  {'STATUS':<6}  {'EXIT':<4}  LOG")
    for record in records:
        print(
            f"{display_time(record):<19}  "
            f"{record.command:<12}  "
            f"{display_project(record):<12}  "
            f"{record.status:<6}  "
            f"{display_exit_code(record):<4}  "
            f"{display_log_path(record)}"
        )


def display_time(record: HistoryRecord) -> str:
    if record.sort_time == datetime.min.replace(tzinfo=timezone.utc):
        return "?"
    return f"{record.sort_time:%Y-%m-%d %H:%M:%S}"


def display_project(record: HistoryRecord) -> str:
    return record.project or "-"


def display_exit_code(record: HistoryRecord) -> str:
    return str(record.exit_code) if record.exit_code is not None else "-"


def display_log_path(record: HistoryRecord) -> str:
    if not record.log_path:
        return "-"
    suffix = "" if record.log_exists else " (missing)"
    return f"{record.log_path}{suffix}"
