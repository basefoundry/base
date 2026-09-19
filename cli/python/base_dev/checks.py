from __future__ import annotations

from dataclasses import dataclass

from base_setup.checks import aggregate_check_statuses
from base_setup.checks import DoctorFinding
from base_setup.checks import render_doctor_finding
from base_setup.checks import resolve_check_status
from base_setup.checks import serialize_check


@dataclass(frozen=True)
class DevCheck:
    name: str
    ok: bool
    message: str
    fix: str
    status: str = ""
    finding_id: str = "BASE-D100"


def check_to_json(check: DevCheck) -> dict[str, str]:
    return serialize_check(check)


def check_to_doctor_json(check: DevCheck) -> dict[str, str]:
    return check_to_json(check)


def checks_status(checks: tuple[DevCheck, ...]) -> str:
    return aggregate_check_statuses(doctor_status(check) for check in checks)


def doctor_status(check: DevCheck) -> str:
    return resolve_check_status(check.ok, check.status)


def print_doctor_finding(status: str, finding_id: str, name: str, message: str, fix: str = "") -> None:
    render_doctor_finding(DoctorFinding(status, finding_id, name, message, fix))
