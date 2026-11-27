from __future__ import annotations

import base_cli

from .project_config_resolution import ResolvedProjectConfig, render_config_resolution, resolve_project_config
from .project_model import ProjectArguments
from .project_operations import ProjectOperations
from .project_schema import render_legacy_schema_fields, schema_for_config


def doctor_command(
    args: ProjectArguments, ops: ProjectOperations, *, resolved: ResolvedProjectConfig | None = None
) -> int:
    owner = ops.require_owner(args)
    resolved = resolved or resolve_project_config(args, owner)
    schema = schema_for_config(args, resolved.config)
    render_config_resolution(resolved)
    owner_info = ops.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        print(f"MISSING Project {args.project_title}")
        return base_cli.ExitCode.FAILURE
    fields = ops.fetch_project_fields(owner_info.project.project_id)
    render_legacy_schema_fields(fields, schema)
    findings = ops.compare_schema(fields, schema)
    if not findings:
        print(f"OK      Project {args.project_title}")
        return base_cli.ExitCode.SUCCESS
    for finding in findings:
        print(f"{finding.status.upper():<8}{finding.name}  {finding.message}")
    return base_cli.ExitCode.FAILURE
