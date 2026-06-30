from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class DevCheck:
    name: str
    ok: bool
    message: str
    fix: str
    status: str = ""
    finding_id: str = "BASE-D100"


def check_to_json(check: DevCheck) -> dict[str, str]:
    return {
        "id": check.finding_id,
        "status": doctor_status(check),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def check_to_doctor_json(check: DevCheck) -> dict[str, str]:
    return check_to_json(check)


def checks_status(checks: tuple[DevCheck, ...]) -> str:
    statuses = tuple(doctor_status(check) for check in checks)
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


def doctor_status(check: DevCheck) -> str:
    return check.status or ("ok" if check.ok else "error")


def print_doctor_finding(status: str, finding_id: str, name: str, message: str, fix: str = "") -> None:
    stream = sys.stderr if status in {"error", "warn"} else sys.stdout
    print(f"{status:<5}  {finding_id:<9}  {name:<26}  {message}", file=stream)
    if fix:
        print(f"       Fix: {fix}", file=stream)
