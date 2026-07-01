"""Internal pre-CLI JSON renderer for setup/check/doctor shell orchestration.

This module intentionally does not expose a public ``base_cli.App`` command.
``setup_common.sh`` calls it while collecting host diagnostics, including cases
where Click, PyYAML, or the normal Base CLI runtime may be missing or unhealthy.
It therefore accepts only its argparse subcommands, writes structured payloads
to stdout or explicit output files, and does not provide base_cli.App debug,
log-file, history, run-id, or standard-option behavior.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base_cli

from .checks import DIAGNOSTIC_JSON_SCHEMA_VERSION


VALID_STATUSES = {"ok", "warn", "error"}
BASE_CHECK_FINDING_IDS = {
    "homebrew": "BASE-D001",
    "xcode_command_line_tools": "BASE-D002",
    "python": "BASE-D003",
    "base_virtualenv": "BASE-D004",
    "pyyaml": "BASE-D005",
    "click": "BASE-D006",
    "base_bash_libraries": "BASE-D007",
    "bash": "BASE-D008",
    "python_venv": "BASE-D009",
    "git": "BASE-D010",
    "gh": "BASE-D011",
    "bats": "BASE-D012",
    "shellcheck": "BASE-D013",
    "jq": "BASE-D014",
    "go": "BASE-D015",
}


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: str
    message: str
    fix: str = ""


def validate_status(status: str) -> str:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid diagnostic status '{status}'.")
    return status


def merge_statuses(*statuses: str) -> str:
    normalized = tuple(validate_status(status) for status in statuses if status)
    if "error" in normalized:
        return "error"
    if "warn" in normalized:
        return "warn"
    return "ok"


def payload_status(payload: Any) -> str:
    if isinstance(payload, dict):
        status = payload.get("status", "ok")
        return validate_status(status) if isinstance(status, str) else "ok"
    if isinstance(payload, list):
        return merge_statuses(
            *(
                item.get("status", "ok")
                for item in payload
                if isinstance(item, dict) and isinstance(item.get("status", "ok"), str)
            )
        )
    return "ok"


def check_item(finding_id: str, check: DiagnosticCheck) -> dict[str, str]:
    return {
        "id": finding_id,
        "status": validate_status(check.status),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def base_check_item(check: DiagnosticCheck) -> dict[str, str]:
    return check_item(BASE_CHECK_FINDING_IDS.get(check.name, "BASE-D000"), check)


def project_venv_check_item(status: str, message: str, fix: str) -> dict[str, str]:
    return check_item(
        "BASE-P050",
        DiagnosticCheck(
            name="project_virtualenv",
            status=status,
            message=message,
            fix=fix,
        ),
    )


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def render_top_level_payload(payload: dict[str, Any]) -> str:
    lines = ["{"]
    items = list(payload.items())
    for index, (key, value) in enumerate(items):
        suffix = "," if index < len(items) - 1 else ""
        if isinstance(value, list):
            lines.append(f'  {json.dumps(key)}: [')
            for item_index, item in enumerate(value):
                item_suffix = "," if item_index < len(value) - 1 else ""
                lines.append(f"    {compact_json(item)}{item_suffix}")
            lines.append(f"  ]{suffix}")
        elif isinstance(value, dict):
            lines.append(f'  {json.dumps(key)}: {compact_json(value)}{suffix}')
        else:
            lines.append(f'  {json.dumps(key)}: {json.dumps(value, ensure_ascii=True)}{suffix}')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_base_diagnostic_payload(
    checks: tuple[DiagnosticCheck, ...],
    item_key: str,
    project: str | None = None,
    embedded_payloads: tuple[tuple[str, str], ...] = (),
) -> str:
    embedded = tuple((key, json.loads(payload_text)) for key, payload_text in embedded_payloads)
    base_status = merge_statuses(*(check.status for check in checks))
    status = merge_statuses(base_status, *(payload_status(payload) for _key, payload in embedded))
    payload: dict[str, Any] = {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "status": status,
    }
    if project:
        payload["project"] = project
    payload[item_key] = [base_check_item(check) for check in checks]
    for key, embedded_payload in embedded:
        payload[key] = embedded_payload
    return render_top_level_payload(payload)


def render_base_check_payload(
    checks: tuple[DiagnosticCheck, ...],
    project: str | None = None,
    embedded_payloads: tuple[tuple[str, str], ...] = (),
) -> str:
    return render_base_diagnostic_payload(
        checks=checks,
        item_key="checks",
        project=project,
        embedded_payloads=embedded_payloads,
    )


def render_base_doctor_payload(
    checks: tuple[DiagnosticCheck, ...],
    project: str | None = None,
    embedded_payloads: tuple[tuple[str, str], ...] = (),
) -> str:
    return render_base_diagnostic_payload(
        checks=checks,
        item_key="findings",
        project=project,
        embedded_payloads=embedded_payloads,
    )


def render_project_venv_check_payload(
    project: str,
    status: str,
    message: str,
    fix: str,
    precheck_json: str = "[]",
) -> str:
    precheck_payload = json.loads(precheck_json)
    checks = precheck_payload if isinstance(precheck_payload, list) else precheck_payload.get("checks", [])
    check_items = [*checks, project_venv_check_item(status, message, fix)]
    payload = {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "status": merge_statuses(payload_status(precheck_payload), status),
        "project": project,
        "checks": check_items,
    }
    return render_top_level_payload(payload)


def render_project_venv_doctor_payload(
    status: str,
    message: str,
    fix: str,
    precheck_json: str = "[]",
) -> str:
    precheck_payload = json.loads(precheck_json)
    checks = precheck_payload if isinstance(precheck_payload, list) else precheck_payload.get("checks", [])
    return compact_json([*checks, project_venv_check_item(status, message, fix)]) + "\n"


def render_check_record(project: str, status: str, checked_at: str) -> str:
    payload = {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "project": project,
        "command": "basectl check",
        "status": validate_status(status),
        "checked_at": checked_at,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2) + "\n"


def write_check_record(path: Path, project: str, status: str, checked_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(render_check_record(project, status, checked_at), encoding="utf-8")
    temp_path.replace(path)


def parse_check(values: list[str]) -> DiagnosticCheck:
    name, status, message, fix = values
    return DiagnosticCheck(name=name, status=status, message=message, fix=fix)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="base_setup.diagnostics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_json = subparsers.add_parser("check-json")
    check_json.add_argument("--project")
    check_json.add_argument(
        "--check",
        action="append",
        nargs=4,
        default=[],
        metavar=("NAME", "STATUS", "MESSAGE", "FIX"),
    )
    check_json.add_argument("--embedded-payload", action="append", nargs=2, default=[], metavar=("KEY", "JSON"))
    check_json.add_argument("--record-path")
    check_json.add_argument("--checked-at")

    doctor_json = subparsers.add_parser("doctor-json")
    doctor_json.add_argument("--project")
    doctor_json.add_argument(
        "--finding",
        action="append",
        nargs=4,
        default=[],
        metavar=("NAME", "STATUS", "MESSAGE", "FIX"),
    )
    doctor_json.add_argument("--embedded-payload", action="append", nargs=2, default=[], metavar=("KEY", "JSON"))

    record_check = subparsers.add_parser("record-check")
    record_check.add_argument("--project", required=True)
    record_check.add_argument("--status", required=True)
    record_check.add_argument("--checked-at", required=True)
    record_check.add_argument("--output-path", required=True)

    venv_check = subparsers.add_parser("project-venv-check-json")
    venv_check.add_argument("--project", required=True)
    venv_check.add_argument("--status", required=True)
    venv_check.add_argument("--message", required=True)
    venv_check.add_argument("--fix", default="")
    venv_check.add_argument("--precheck-json", default="[]")

    venv_doctor = subparsers.add_parser("project-venv-doctor-json")
    venv_doctor.add_argument("--status", required=True)
    venv_doctor.add_argument("--message", required=True)
    venv_doctor.add_argument("--fix", default="")
    venv_doctor.add_argument("--precheck-json", default="[]")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check-json":
        checks = tuple(parse_check(check) for check in args.check)
        embedded_payloads = tuple((key, payload) for key, payload in args.embedded_payload)
        payload = render_base_check_payload(checks, project=args.project, embedded_payloads=embedded_payloads)
        print(payload, end="")
        status = payload_status(json.loads(payload))
        if args.record_path and args.project and args.checked_at:
            write_check_record(Path(args.record_path), args.project, status, args.checked_at)
        return base_cli.ExitCode.SUCCESS if status != "error" else base_cli.ExitCode.FAILURE
    if args.command == "doctor-json":
        checks = tuple(parse_check(finding) for finding in args.finding)
        embedded_payloads = tuple((key, payload) for key, payload in args.embedded_payload)
        payload = render_base_doctor_payload(checks, project=args.project, embedded_payloads=embedded_payloads)
        print(payload, end="")
        status = payload_status(json.loads(payload))
        return base_cli.ExitCode.SUCCESS if status != "error" else base_cli.ExitCode.FAILURE
    if args.command == "record-check":
        write_check_record(Path(args.output_path), args.project, args.status, args.checked_at)
        return base_cli.ExitCode.SUCCESS
    if args.command == "project-venv-check-json":
        print(
            render_project_venv_check_payload(
                project=args.project,
                status=args.status,
                message=args.message,
                fix=args.fix,
                precheck_json=args.precheck_json,
            ),
            end="",
        )
        return base_cli.ExitCode.SUCCESS if args.status != "error" else base_cli.ExitCode.FAILURE
    if args.command == "project-venv-doctor-json":
        print(
            render_project_venv_doctor_payload(
                status=args.status,
                message=args.message,
                fix=args.fix,
                precheck_json=args.precheck_json,
            ),
            end="",
        )
        return base_cli.ExitCode.SUCCESS if args.status != "error" else base_cli.ExitCode.FAILURE
    parser.error(f"Unsupported diagnostics command '{args.command}'.")
    return base_cli.ExitCode.USAGE_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
