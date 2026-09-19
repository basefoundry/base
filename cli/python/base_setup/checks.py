from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any


DIAGNOSTIC_JSON_SCHEMA_VERSION = 1
CHECK_STATUS_FILE_ENVIRONMENT_VARIABLE = "BASE_SETUP_CHECK_STATUS_FILE"
DOCTOR_NO_COLOR_ENVIRONMENT_VARIABLE = "BASE_SETUP_DOCTOR_NO_COLOR"
VALID_STATUSES = {"ok", "warn", "error"}


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    ok: bool
    message: str
    fix: str
    finding_id: str
    status: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DoctorFinding:
    status: str
    finding_id: str
    name: str
    message: str
    fix: str = ""
    visual_status: bool = False
    color_control_env: str | None = None


def check_to_json(check: ArtifactCheck) -> dict[str, Any]:
    return serialize_check(check)


def checks_status(checks: Iterable[ArtifactCheck]) -> str:
    return aggregate_check_statuses(doctor_status(check) for check in checks)


def aggregate_check_statuses(statuses: Iterable[str]) -> str:
    return merge_statuses(*statuses)


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


def publish_check_status(status: str) -> None:
    if status not in {"ok", "warn", "error"}:
        raise ValueError(f"Unsupported check status '{status}'.")

    status_file = os.environ.get(CHECK_STATUS_FILE_ENVIRONMENT_VARIABLE)
    if status_file:
        Path(status_file).write_text(f"{status}\n", encoding="utf-8")


def checks_payload_to_json(checks: Iterable[ArtifactCheck], **metadata: Any) -> dict[str, Any]:
    check_tuple = tuple(checks)
    return {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "status": checks_status(check_tuple),
        **metadata,
        "checks": [check_to_json(check) for check in check_tuple],
    }


def doctor_status(check: ArtifactCheck) -> str:
    return resolve_check_status(check.ok, check.status)


def resolve_check_status(ok: bool, status: str = "") -> str:
    return status or ("ok" if ok else "error")


def serialize_check(
    check: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": check.finding_id,
        "status": resolve_check_status(check.ok, check.status),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }
    details = getattr(check, "details", None)
    if details:
        payload["details"] = dict(details)
    return payload


def _doctor_visual_status_parts(status: str) -> tuple[str, str, str]:
    if status == "ok":
        return "✓ ok", "\033[0;32m", "   "
    if status == "warn":
        return "! warn", "\033[0;33m", " "
    if status == "error":
        return "✗ error", "\033[0;31m", ""
    return status, "", ""


def doctor_visual_status_enabled(stream: Any, *, color_control_env: str | None = None) -> bool:
    return (
        (not color_control_env or os.environ.get(color_control_env) != "true")
        and not os.environ.get("NO_COLOR")
        and os.environ.get("TERM", "") not in {"", "dumb"}
        and stream.isatty()
    )


def render_doctor_finding(finding: DoctorFinding) -> None:
    stream = sys.stderr if finding.status in {"error", "warn"} else sys.stdout
    if finding.visual_status and doctor_visual_status_enabled(
        stream, color_control_env=finding.color_control_env
    ):
        label, color, padding = _doctor_visual_status_parts(finding.status)
        status_prefix = f"{label}{padding}  "
        print(
            f"{color}{label}\033[0m{padding}  {finding.finding_id:<9}  "
            f"{finding.name:<26}  {finding.message}",
            file=stream,
        )
    else:
        status_prefix = f"{finding.status:<5}  "
        print(
            f"{status_prefix}{finding.finding_id:<9}  {finding.name:<26}  {finding.message}",
            file=stream,
        )
    if finding.fix:
        print(f"{' ' * len(status_prefix)}Fix: {finding.fix}", file=stream)


def print_doctor_finding(status: str, finding_id: str, name: str, message: str, fix: str = "") -> None:
    render_doctor_finding(
        DoctorFinding(
            status=status,
            finding_id=finding_id,
            name=name,
            message=message,
            fix=fix,
            visual_status=True,
            color_control_env=DOCTOR_NO_COLOR_ENVIRONMENT_VARIABLE,
        )
    )
