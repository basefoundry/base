from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from .project_configure import ConfigureDryRunPlan, ProjectReplacement
from .project_configure import legacy_project_title, render_dry_run_configure, standard_template_view_errors


@dataclass(frozen=True)
class ConfigureExecution:
    owner: str
    owner_info: Any
    args: Any
    project: Any
    replacement: ProjectReplacement | None
    ops: Any


def configure_command(args: Any, ops: Any) -> int:
    owner = ops.require_owner(args)
    if args.replace_project and not args.repo:
        raise ops.ProjectUsageError("--replace-project requires --repo.")
    project_config = ops.project_config_for_args(args)
    schema = ops.schema_for_args(args)
    owner_info = ops.find_owner_and_project(owner, args.project_title or "")
    project = owner_info.project
    replacement = replacement_plan_for_args(args, owner, project, ops)
    should_copy_template = args.repo is not None and project is None
    fields = fetch_existing_configure_fields(project, replacement, ops)
    if should_copy_template or replacement is not None:
        actions = ()
    else:
        actions = ops.configuration_plan(project_exists=project is not None, fields=fields, schema=schema)
    errors = [action for action in actions if action.action == "error"]
    if errors:
        for action in errors:
            print(f"ERROR   {action.name}  {action.message}", file=sys.stderr)
        return 1
    if args.dry_run:
        render_dry_run_configure(
            args,
            ConfigureDryRunPlan(
                actions=actions,
                would_copy_template=should_copy_template,
                replacement=replacement,
                project_config=project_config,
            ),
        )
        return 0
    project = prepare_configure_project(
        ConfigureExecution(
            owner=owner,
            owner_info=owner_info,
            args=args,
            project=project,
            replacement=replacement,
            ops=ops,
        )
    )
    fields = ops.fetch_project_fields(project.project_id)
    ensure_schema_fields(project.project_id, fields, schema, ops)
    fields = ops.fetch_project_fields(project.project_id)
    link_and_backfill_project(project.project_id, args.repo, ops)
    copy_replacement_project_fields(project.project_id, replacement, ops)
    copy_project_fields_from_source(owner, project.project_id, args.copy_fields_from_project, ops)
    apply_project_config_defaults(project.project_id, fields, project_config, ops)
    close_replacement_project(replacement, ops)
    print(f"✓ Configured GitHub Project {args.project_title}")
    return 0


def replacement_plan_for_args(
    args: Any,
    owner: str,
    project: Any,
    ops: Any,
) -> ProjectReplacement | None:
    if not args.replace_project:
        return None
    if not args.repo:
        raise ops.ProjectUsageError("--replace-project requires --repo.")
    if project is None:
        raise ops.ProjectError(
            f"Project '{args.project_title}' was not found for owner '{owner}'; cannot replace it."
        )
    view_errors = standard_template_view_errors(ops.fetch_project_views(project.project_id))
    if not view_errors:
        print(f"INFO: Project '{args.project_title}' already has standard Base views; skipping replacement.")
        return None
    return ProjectReplacement(
        legacy_project=project,
        legacy_title=legacy_project_title(args.project_title or ""),
        view_errors=view_errors,
    )


def fetch_existing_configure_fields(
    project: Any,
    replacement: ProjectReplacement | None,
    ops: Any,
) -> tuple[Any, ...]:
    if project is None or replacement is not None:
        return ()
    return ops.fetch_project_fields(project.project_id)


def prepare_configure_project(execution: ConfigureExecution) -> Any:
    if execution.replacement is not None:
        execution.ops.update_project(
            execution.replacement.legacy_project.project_id,
            title=execution.replacement.legacy_title,
        )
        new_project = execution.ops.copy_template_project(
            execution.owner,
            execution.owner_info.owner_id,
            execution.args.project_title or "",
        )
        execution.ops.verify_standard_template_views(execution.ops.fetch_project_views(new_project.project_id))
        print(f"✓ Renamed existing Project {execution.args.project_title} to {execution.replacement.legacy_title}")
        return new_project
    if execution.project is not None:
        return execution.project
    if execution.args.repo:
        new_project = execution.ops.copy_template_project(
            execution.owner,
            execution.owner_info.owner_id,
            execution.args.project_title or "",
        )
        execution.ops.verify_standard_template_views(execution.ops.fetch_project_views(new_project.project_id))
        return new_project
    return execution.ops.create_project(execution.owner_info.owner_id, execution.args.project_title or "")


def ensure_schema_fields(
    project_id: str,
    fields: tuple[Any, ...],
    schema: Any,
    ops: Any,
) -> None:
    by_name = {field.name: field for field in fields}
    for spec in schema.fields:
        field = by_name.get(spec.name)
        if field is None:
            ops.create_single_select_field(project_id, spec)
        elif ops.missing_option_names(field, spec):
            ops.update_single_select_field(field, spec)


def link_and_backfill_project(project_id: str, repo: str | None, ops: Any) -> None:
    if not repo:
        return
    ops.link_project_to_repository(project_id, repo)
    count = ops.backfill_repository_issues(project_id, repo)
    print(f"✓ Backfilled {count} issue(s) from {repo}")


def copy_replacement_project_fields(
    project_id: str,
    replacement: ProjectReplacement | None,
    ops: Any,
) -> None:
    if replacement is None:
        return
    summary = ops.copy_missing_project_item_fields(replacement.legacy_project.project_id, project_id)
    print(f"✓ Copied {summary.applied_count} Project item field value(s) from {replacement.legacy_title}")
    for skipped in summary.skipped:
        print(
            f"WARN    Issue #{skipped.issue_number} {skipped.field_name}={skipped.option_name}: {skipped.reason}",
            file=sys.stderr,
        )


def close_replacement_project(replacement: ProjectReplacement | None, ops: Any) -> None:
    if replacement is None:
        return
    ops.update_project(replacement.legacy_project.project_id, closed=True)
    print(f"✓ Closed legacy GitHub Project {replacement.legacy_title}")


def copy_project_fields_from_source(
    owner: str,
    target_project_id: str,
    source_project_title: str | None,
    ops: Any,
) -> None:
    if not source_project_title:
        return
    source = ops.find_owner_and_project(owner, source_project_title).project
    if source is None:
        raise ops.ProjectError(f"Source Project '{source_project_title}' was not found for owner '{owner}'.")
    summary = ops.copy_missing_project_item_fields(source.project_id, target_project_id)
    print(f"✓ Copied {summary.applied_count} Project item field value(s) from {source_project_title}")
    for skipped in summary.skipped:
        print(
            f"WARN    Issue #{skipped.issue_number} {skipped.field_name}={skipped.option_name}: {skipped.reason}",
            file=sys.stderr,
        )


def apply_project_config_defaults(
    target_project_id: str,
    target_fields: tuple[Any, ...],
    project_config: Any,
    ops: Any,
) -> None:
    defaults = ops.project_field_defaults_for_config(project_config)
    if not defaults:
        return
    summary = ops.apply_missing_project_item_defaults(target_project_id, target_fields, defaults)
    print(f"✓ Applied {summary.applied_count} default Project item field value(s)")
    for skipped in summary.skipped:
        print(
            f"WARN    Issue #{skipped.issue_number} {skipped.field_name}={skipped.option_name}: {skipped.reason}",
            file=sys.stderr,
        )
