from __future__ import annotations

import json
import sys

import base_cli
from base_setup.checks import DIAGNOSTIC_JSON_SCHEMA_VERSION

from .checks import DevCheck
from .checks import check_to_doctor_json
from .checks import check_to_json
from .checks import checks_status
from .checks import doctor_status
from .checks import print_doctor_finding


def print_check_results(
    ctx: base_cli.Context,
    checks: tuple[DevCheck, ...],
    output_format: str,
    profiles: tuple[str, ...],
) -> int:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
                    "status": checks_status(checks),
                    "profiles": list(profiles),
                    "checks": [check_to_json(check) for check in checks],
                },
                indent=2,
            )
        )
    elif output_format == "text":
        for check in checks:
            if check.ok:
                ctx.log.info(check.message)
            else:
                ctx.log.warning(check.message)
    else:
        ctx.log.error("Unsupported check output format '%s'. Expected text or json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR

    if all(doctor_status(check) != "error" for check in checks):
        return base_cli.ExitCode.SUCCESS
    return base_cli.ExitCode.FAILURE


def print_doctor_results(checks: tuple[DevCheck, ...], output_format: str) -> int:
    if output_format == "json":
        print(json.dumps([check_to_doctor_json(check) for check in checks], indent=2))
        return min(sum(1 for check in checks if doctor_status(check) == "error"), 125)
    if output_format != "text":
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR

    error_count = 0
    for check in checks:
        status = doctor_status(check)
        if status == "error":
            print_doctor_finding("error", check.finding_id, check.name, check.message, check.fix)
            error_count += 1
        else:
            print_doctor_finding(status, check.finding_id, check.name, check.message, check.fix)
    return min(error_count, 125)
