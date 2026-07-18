from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import base_cli
from base_cli.history import HISTORY_PATH
from base_cli.history import HISTORY_SCOPE_INTERNAL
from base_cli.history import HISTORY_SCOPE_PRIMARY
from base_cli.history import optional_int
from base_cli.history import optional_string
from base_cli.history import parse_finished_history_record_line
from base_cli.history import parse_positive_int
from base_cli.history import redact_history_argv
from base_cli.history import redact_history_text
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
    scope: str

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
    report: bool
    include_internal: bool


@dataclass(frozen=True)
class CommandFamilySummary:
    command: str
    count: int
    failures: int


@dataclass(frozen=True)
class HistoryReport:
    cache_root: Path
    history_path: Path
    records: list[HistoryRecord]
    status_counts: dict[str, int]
    command_families: list[CommandFamilySummary]
    failures: list[HistoryRecord]


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--project", "project_filter", help="Filter by Base project name.")
@base_cli.option("--command", "command_filter", help="Filter by basectl command name.")
@base_cli.option("--status", "status_filter", help="Filter by status: ok, warn, or error.")
@base_cli.option("--limit", default="10", help="Maximum history records to list.")
@base_cli.option("--format", "output_format", default="text", help="Output format: text, markdown, or json.")
@base_cli.option("--report", is_flag=True, help="Print a privacy-conscious local activity report.")
@base_cli.option("--include-internal", is_flag=True, help="Include delegated internal steps in the output.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    project_filter: str | None,
    command_filter: str | None,
    status_filter: str | None,
    limit: str,
    output_format: str,
    report: bool,
    include_internal: bool,
) -> int:
    try:
        options = HistoryOptions(
            project=project_filter,
            command=command_filter,
            status=normalize_optional_filter(status_filter),
            limit=parse_positive_int("--limit", limit),
            output_format=normalize_report_format(output_format) if report else normalize_format(output_format),
            report=report,
            include_internal=include_internal,
        )
    except ValueError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    cache_root = base_cache_root()
    records = recent_history(cache_root, options=options, logger=ctx.log)
    if options.report:
        history_report = build_history_report(cache_root, records)
        if options.output_format == "json":
            print(json.dumps(history_report_to_json(history_report), indent=2, sort_keys=True))
        else:
            print_history_report_markdown(history_report)
        return base_cli.ExitCode.SUCCESS

    if options.output_format == "json":
        print(json.dumps([record.to_json() for record in records], indent=2))
        return base_cli.ExitCode.SUCCESS
    if not records:
        print(f"No Base command history found under {cache_root / HISTORY_PATH}.")
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


def normalize_report_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "text":
        return "markdown"
    if normalized not in {"markdown", "json"}:
        raise ValueError(f"Unsupported report output format '{value}'. Expected one of: markdown, json.")
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
        scope=optional_string(payload.get("scope")) or HISTORY_SCOPE_PRIMARY,
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
    if not options.include_internal:
        filtered = [record for record in filtered if record.scope != HISTORY_SCOPE_INTERNAL]
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


def build_history_report(cache_root: Path, records: list[HistoryRecord]) -> HistoryReport:
    return HistoryReport(
        cache_root=cache_root,
        history_path=cache_root / HISTORY_PATH,
        records=records,
        status_counts=build_status_counts(records),
        command_families=build_command_family_summaries(records),
        failures=[record for record in records if is_failure(record)],
    )


def build_status_counts(records: list[HistoryRecord]) -> dict[str, int]:
    counts = Counter(record.status for record in records)
    return {status: counts.get(status, 0) for status in ("error", "ok", "warn")}


def build_command_family_summaries(records: list[HistoryRecord]) -> list[CommandFamilySummary]:
    counts: dict[str, int] = {}
    failures: dict[str, int] = {}
    for record in records:
        command = command_family(record.command)
        counts[command] = counts.get(command, 0) + 1
        if is_failure(record):
            failures[command] = failures.get(command, 0) + 1
    summaries = [
        CommandFamilySummary(command=command, count=count, failures=failures.get(command, 0))
        for command, count in counts.items()
    ]
    return sorted(summaries, key=lambda item: (-item.failures, -item.count, item.command))


def command_family(command: str) -> str:
    return command.split()[0] if command.split() else command


def is_failure(record: HistoryRecord) -> bool:
    if record.status == "error":
        return True
    return record.exit_code is not None and record.exit_code != 0


def history_report_to_json(report: HistoryReport) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "cache_root": sanitize_report_path(str(report.cache_root)),
        "history_path": sanitize_report_path(str(report.history_path)),
        "summary": {
            "record_count": len(report.records),
            "failure_count": len(report.failures),
            "status_counts": report.status_counts,
        },
        "command_families": [
            {"command": family.command, "count": family.count, "failures": family.failures}
            for family in report.command_families
        ],
        "failures": [report_record_to_json(record) for record in report.failures],
        "recent": [report_record_to_json(record) for record in report.records],
        "privacy": {
            "raw_logs_included": False,
            "redaction_rules": [
                "Raw log contents are not included by default.",
                "Home directory paths are compacted to '~'.",
                "Secret-looking option values, environment assignments, and URL credentials are redacted.",
            ],
        },
    }


def report_record_to_json(record: HistoryRecord) -> dict[str, Any]:
    return {
        "run_id": sanitize_report_text(record.run_id),
        "command": sanitize_report_text(record.command),
        "project": sanitize_report_text(record.project) if record.project else None,
        "status": sanitize_report_text(record.status),
        "exit_code": record.exit_code,
        "ended_at": sanitize_report_text(record.ended_at),
        "log_path": sanitize_report_path(record.log_path) if record.log_path else None,
        "log_exists": record.log_exists,
        "argv": sanitize_report_argv(record.payload.get("argv")),
    }


def sanitize_report_argv(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    redacted = redact_history_argv([str(arg) for arg in value], sensitive_options=set())
    return [compact_report_home_text(arg) for arg in redacted]


def sanitize_report_path(value: str) -> str:
    text = sanitize_report_text(value)
    if text.startswith("/") or text.startswith("~"):
        return redact_history_text(str(Path(text).expanduser().resolve(strict=False)))
    return text


def sanitize_report_text(value: str) -> str:
    return compact_report_home_text(redact_history_text(value))


def compact_report_home_text(value: str) -> str:
    home = os.environ.get("HOME")
    if not home:
        return value
    raw_home = str(Path(home).expanduser())
    resolved_home = str(Path(home).expanduser().resolve(strict=False))
    candidates = {raw_home, resolved_home}
    for candidate in (raw_home, resolved_home):
        if candidate.startswith("/var/"):
            candidates.add(f"/private{candidate}")
        if candidate.startswith("/private/var/"):
            candidates.add(candidate.removeprefix("/private"))
    for candidate in sorted(candidates, key=len, reverse=True):
        if value == candidate:
            return "~"
        if value.startswith(f"{candidate}/"):
            return f"~/{value[len(candidate) + 1:]}"
    return value


def print_history_report_markdown(report: HistoryReport) -> None:
    print("# Base Local Activity Report")
    print()
    print(f"- History index: `{sanitize_report_path(str(report.history_path))}`")
    print(f"- Cache root: `{sanitize_report_path(str(report.cache_root))}`")
    print(f"- History records: {len(report.records)}")
    print(f"- Failures: {len(report.failures)}")
    print(f"- Warnings: {report.status_counts.get('warn', 0)}")
    print()

    if not report.records:
        print("No command history records found.")
        print()
        print_report_privacy_section()
        return

    print("## Status Summary")
    print()
    for status in ("ok", "warn", "error"):
        print(f"- {status}: {report.status_counts.get(status, 0)}")
    print()

    print("## Common Failing Command Families")
    print()
    failing_families = [family for family in report.command_families if family.failures > 0]
    if not failing_families:
        print("No failing command families found in the selected recent history.")
    else:
        for family in failing_families:
            print(f"- `{family.command}`: {family.failures} failures across {family.count} runs")
    print()

    print("## Recent Commands")
    print()
    print("| Time | Command | Project | Status | Exit | Log |")
    print("| --- | --- | --- | --- | --- | --- |")
    for record in report.records:
        print(
            "| "
            f"{markdown_cell(display_time(record))} | "
            f"`{markdown_cell(record.command)}` | "
            f"{markdown_cell(display_project(record))} | "
            f"{markdown_cell(record.status)} | "
            f"{markdown_cell(display_exit_code(record))} | "
            f"{markdown_cell(display_report_log_path(record))} |"
        )
    print()

    if report.failures:
        print("## Failure Details")
        print()
        for record in report.failures:
            print(f"- `{sanitize_report_text(record.command)}` at {display_time(record)}")
            print(f"  - status: {sanitize_report_text(record.status)}")
            print(f"  - exit: {display_exit_code(record)}")
            print(f"  - log: {display_report_log_path(record)}")
            argv = sanitize_report_argv(record.payload.get("argv"))
            if argv:
                print(f"  - argv: `{markdown_inline(' '.join(argv))}`")
        print()

    print_report_privacy_section()


def display_report_log_path(record: HistoryRecord) -> str:
    if not record.log_path:
        return "-"
    path = sanitize_report_path(record.log_path)
    suffix = "" if record.log_exists else " (missing)"
    return f"`{path}`{suffix}"


def print_report_privacy_section() -> None:
    print("## Privacy")
    print()
    print("- Raw log contents are not included by default.")
    print("- Home directory paths are compacted to `~`.")
    print("- Secret-looking option values, environment assignments, and URL credentials are shown as `[REDACTED]`.")


def markdown_cell(value: str) -> str:
    return sanitize_report_text(value).replace("|", "\\|")


def markdown_inline(value: str) -> str:
    return sanitize_report_text(value).replace("`", "\\`")
