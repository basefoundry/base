from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from base_cli.paths import base_cache_root


RUN_ID_RE = re.compile(r"^(?P<stamp>\d{8}T\d{6})_[A-Za-z0-9]+$")


@dataclass(frozen=True)
class LogEntry:
    command: str
    raw_command: str
    run_id: str
    path: Path
    timestamp: datetime
    status: str


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="base_logs", description="List recent Base CLI runtime logs.")
    parser.add_argument("--command", help="Filter by basectl command or Python CLI name.")
    parser.add_argument("--limit", type=parse_positive_int, default=10, help="Maximum log entries to list.")
    parser.add_argument("--path", action="store_true", help="Print the most recent matching log path only.")
    parser.add_argument("--tail", action="store_true", help="Tail and follow the most recent matching log.")
    parser.add_argument("--open", action="store_true", help="Open the most recent matching log in PAGER or EDITOR.")
    parser.add_argument("--lines", type=parse_positive_int, default=40, help="Line count to show before following.")
    return parser


def parse_positive_int(value: str) -> int:
    if not value.isdigit():
        raise argparse.ArgumentTypeError("must be a positive integer")
    amount = int(value)
    if amount <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return amount


def run(args: argparse.Namespace) -> int:
    selected_actions = sum(1 for name in ("path", "tail", "open") if getattr(args, name))
    if selected_actions > 1:
        print("ERROR: Choose only one of --path, --tail, or --open.", file=sys.stderr)
        return 2

    entries = recent_logs(base_cache_root(), command_filter=args.command)
    if not entries:
        return report_no_logs(args)
    return run_with_entries(args, entries)


def report_no_logs(args: argparse.Namespace) -> int:
    if args.path or args.tail or args.open:
        print("ERROR: No Base CLI logs found.", file=sys.stderr)
        return 1
    print(f"No Base CLI logs found under {base_cache_root() / 'cli'}.")
    return 0


def run_with_entries(args: argparse.Namespace, entries: list[LogEntry]) -> int:
    newest = entries[0]
    if args.path:
        print(newest.path)
        return 0
    if args.tail:
        return tail_log(newest.path, args.lines)
    if args.open:
        return open_log(newest.path)

    print_log_table(entries[: args.limit])
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
