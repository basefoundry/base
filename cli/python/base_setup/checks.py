from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


DIAGNOSTIC_JSON_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    ok: bool
    message: str
    fix: str
    finding_id: str
    status: str = ""


def check_to_json(check: ArtifactCheck) -> dict[str, str]:
    return {
        "id": check.finding_id,
        "status": doctor_status(check),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def check_to_doctor_json(check: ArtifactCheck) -> dict[str, str]:
    return check_to_json(check)


def checks_status(checks: Iterable[ArtifactCheck]) -> str:
    statuses = tuple(doctor_status(check) for check in checks)
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


def checks_payload_to_json(checks: Iterable[ArtifactCheck], **metadata: Any) -> dict[str, Any]:
    check_tuple = tuple(checks)
    return {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "status": checks_status(check_tuple),
        **metadata,
        "checks": [check_to_json(check) for check in check_tuple],
    }


def doctor_status(check: ArtifactCheck) -> str:
    return check.status or ("ok" if check.ok else "error")


def print_doctor_finding(status: str, finding_id: str, name: str, message: str, fix: str = "") -> None:
    print(f"{status:<5}  {finding_id:<9}  {name:<26}  {message}")
    if fix:
        print(f"       Fix: {fix}")
