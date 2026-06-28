from __future__ import annotations

from typing import Any

import base_cli


def doctor_command(args: Any, ops: Any) -> int:
    owner = ops.require_owner(args)
    owner_info = ops.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        print(f"MISSING Project {args.project_title}")
        return base_cli.ExitCode.FAILURE
    fields = ops.fetch_project_fields(owner_info.project.project_id)
    findings = ops.compare_schema(fields, ops.schema_for_args(args))
    if not findings:
        print(f"OK      Project {args.project_title}")
        return base_cli.ExitCode.SUCCESS
    for finding in findings:
        print(f"{finding.status.upper():<8}{finding.name}  {finding.message}")
    return base_cli.ExitCode.FAILURE
