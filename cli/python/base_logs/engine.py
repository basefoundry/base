from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import base_cli
from base_cli.paths import base_cache_root


RUN_ID_RE = re.compile(r"^(?P<stamp>\d{8}T\d{6})_[A-Za-z0-9]+$")

app = base_cli.App(name="base_logs", log_to_file=False)


@dataclass(frozen=True)
class LogEntry:
    command: str
    raw_command: str
    run_id: str
    path: Path
    timestamp: datetime
    status: str


@dataclass(frozen=True)
class LogCommandOptions:
    command_filter: str | None
    limit: int
    path_only: bool
    tail: bool
    open_file: bool
    lines: int


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--command", "command_filter", help="Filter by basectl command or Python CLI name.")
@base_cli.option("--limit", default="10", help="Maximum log entries to list.")
@base_cli.option("--path", "path_only", is_flag=True, help="Print the most recent matching log path only.")
@base_cli.option("--tail", is_flag=True, help="Tail and follow the most recent matching log.")
@base_cli.option("--open", "open_file", is_flag=True, help="Open the most recent matching log in PAGER or EDITOR.")
@base_cli.option("--lines", default="40", help="Line count to show before following.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    command_filter: str | None,
    limit: str,
    path_only: bool,
    tail: bool,
    open_file: bool,
    lines: str,
) -> int:
    try:
        limit_value = parse_positive_int("--limit", limit)
        line_count = parse_positive_int("--lines", lines)
    except ValueError as exc:
        ctx.log.error(str(exc))
        return 2

    options = LogCommandOptions(
        command_filter=command_filter,
        limit=limit_value,
        path_only=path_only,
        tail=tail,
        open_file=open_file,
        lines=line_count,
    )
    selected_actions = sum(1 for selected in (path_only, tail, open_file) if selected)
    if selected_actions > 1:
        ctx.log.error("Choose only one of --path, --tail, or --open.")
        return 2

    cache_root = base_cache_root()
    ctx.log.debug("Scanning Base cache root '%s'.", cache_root)
    entries = recent_logs(cache_root, command_filter=options.command_filter)
    if not entries:
        return report_no_logs(ctx, cache_root, options)
    return run_with_entries(entries, options)


def parse_positive_int(option: str, value: str) -> int:
    if not value.isdigit():
        raise ValueError(f"Option '{option}' must be a positive integer.")
    amount = int(value)
    if amount <= 0:
        raise ValueError(f"Option '{option}' must be greater than zero.")
    return amount


def report_no_logs(ctx: base_cli.Context, cache_root: Path, options: LogCommandOptions) -> int:
    if options.path_only or options.tail or options.open_file:
        ctx.log.error("No Base CLI logs found.")
        return 1
    print(f"No Base CLI logs found under {cache_root / 'cli'}.")
    return 0


def run_with_entries(entries: list[LogEntry], options: LogCommandOptions) -> int:
    newest = entries[0]
    if options.path_only:
        print(newest.path)
        return 0
    if options.tail:
        return tail_log(newest.path, options.lines)
    if options.open_file:
        return open_log(newest.path)

    print_log_table(entries[: options.limit])
    return 0


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

    entries: list[LogEntry] = []
    for logs_dir in sorted(cli_root.glob("*/logs"), key=str):
        if not logs_dir.is_dir():
            continue
        raw_command = logs_dir.parent.name
        for path in sorted(logs_dir.glob("*.log"), key=lambda item: item.name):
            if not path.is_file():
                continue
            entries.append(
                LogEntry(
                    command=infer_display_command(raw_command, path),
                    raw_command=raw_command,
                    run_id=path.stem,
                    path=path,
                    timestamp=entry_timestamp(path),
                    status=infer_status(path),
                )
            )
    return entries


def infer_display_command(raw_command: str, path: Path) -> str:
    if raw_command == "base_setup":
        action = infer_base_setup_action(path)
        return action or "setup"
    if raw_command.startswith("base_"):
        return raw_command.removeprefix("base_").replace("_", "-")
    return raw_command.replace("_", "-")


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


def compact_path(path: Path) -> str:
    try:
        return f"~/{path.expanduser().resolve().relative_to(Path.home().resolve())}"
    except ValueError:
        return str(path)


def tail_log(path: Path, lines: int) -> int:
    tail = shutil.which("tail")
    if tail is None:
        print(f"ERROR: tail was not found on PATH. Log path: {path}", file=sys.stderr)
        return 1
    os.execv(tail, [tail, "-n", str(lines), "-f", str(path)])
    return 1


def open_log(path: Path) -> int:
    command = os.environ.get("PAGER") or os.environ.get("EDITOR")
    if not command:
        print(path)
        return 0

    args = shlex.split(command)
    if not args:
        print(path)
        return 0
    if shutil.which(args[0]) is None:
        print(f"ERROR: {args[0]} was not found on PATH. Log path: {path}", file=sys.stderr)
        return 1
    return subprocess.call([*args, str(path)])
