from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    ok: bool
    message: str
    fix: str
    finding_id: str
    status: str = ""


def check_to_json(check: ArtifactCheck) -> dict[str, str | bool]:
    return {
        "name": check.name,
        "ok": check.ok,
        "message": check.message,
        "fix": check.fix,
    }


def check_to_doctor_json(check: ArtifactCheck) -> dict[str, str]:
    return {
        "id": check.finding_id,
        "status": doctor_status(check),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def doctor_status(check: ArtifactCheck) -> str:
    return check.status or ("ok" if check.ok else "error")


def print_doctor_finding(status: str, finding_id: str, name: str, message: str, fix: str = "") -> None:
    print(f"{status:<5}  {finding_id:<9}  {name:<26}  {message}")
    if fix:
        print(f"       Fix: {fix}")
