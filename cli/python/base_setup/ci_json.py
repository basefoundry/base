from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


LOG_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+"
    r"\d{2}:\d{2}:\d{2}\s+"
    r"[A-Z]+\s+"
    r"\S+\s+"
    r"(?P<message>.*)$"
)


def compact_setup_output_lines(lines: list[str]) -> list[str]:
    messages: list[str] = []
    for line in lines:
        if line == "":
            continue
        match = LOG_LINE_RE.match(line)
        if match is not None:
            messages.append(match.group("message"))
        else:
            messages.append(line)
    return messages


def read_output_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def build_setup_payload(
    *,
    project: str,
    exit_code: int,
    stdout_lines: list[str],
    stderr_lines: list[str],
) -> dict[str, Any]:
    compact_stderr = compact_setup_output_lines(stderr_lines)
    compact_stdout = compact_setup_output_lines(stdout_lines)
    output_lines = compact_stderr or compact_stdout
    payload: dict[str, Any] = {
        "schema_version": 1,
        "command": "setup",
        "status": "error" if exit_code else "ok",
        "project": project,
        "output": output_lines[-1] if output_lines else "",
    }
    if exit_code and output_lines:
        payload["output_lines"] = output_lines
    return payload


def build_setup_payload_from_files(
    *,
    project: str,
    exit_code: int,
    stdout_file: Path,
    stderr_file: Path,
) -> dict[str, Any]:
    return build_setup_payload(
        project=project,
        exit_code=exit_code,
        stdout_lines=read_output_lines(stdout_file),
        stderr_lines=read_output_lines(stderr_file),
    )


def serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_payload(payload: dict[str, Any]) -> None:
    rendered = serialize_payload(payload) + "\n"
    sys.stdout.buffer.write(rendered.encode("utf-8"))


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="base_setup.ci_json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_json = subparsers.add_parser("setup-json")
    setup_json.add_argument("--project", required=True)
    setup_json.add_argument("--exit-code", required=True, type=int)
    setup_json.add_argument("--stdout-file", required=True, type=Path)
    setup_json.add_argument("--stderr-file", required=True, type=Path)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "setup-json":
        write_payload(
            build_setup_payload_from_files(
                project=args.project,
                exit_code=args.exit_code,
                stdout_file=args.stdout_file,
                stderr_file=args.stderr_file,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

