from __future__ import annotations

from datetime import date
import sys

import base_cli
from base_projects.command_helpers import ProjectUsageError

from .project_config import ProjectConfig
from .project_model import FieldUpdate, OwnerInfo, ProjectArguments, ProjectInfo, ProjectItemState
from .project_operations import ProjectOperations


ISSUE_FIELD_NAMES = {
    "priority": "Priority",
    "effort": "Effort",
    "risk_tier": "Risk tier",
    "start_date": "Start date",
    "target_date": "Target date",
}
PROJECT_FIELD_KEYS = {"status", "priority", "area", "initiative", "size"}
DATE_FIELD_KEYS = {"risk_tier", "start_date", "target_date"}
COMMAND_FIELD_KEYS = PROJECT_FIELD_KEYS | set(ISSUE_FIELD_NAMES)


def validate_issue_field_keys(field_values: dict[str, str] | None) -> None:
    """Reject command-line fields that this command would otherwise drop."""
    unknown = sorted(set(field_values or {}) - COMMAND_FIELD_KEYS)
    if unknown:
        names = ", ".join(unknown)
        raise ProjectUsageError(f"Unknown issue field key(s): {names}.")


def issue_set_fields_command(args: ProjectArguments, ops: ProjectOperations) -> int:
    validate_issue_field_keys(args.field_values)
    owner = ops.require_owner(args)
    repo_owner, repo_name = ops.split_repo(ops.require_repo(args))
    repository = f"{repo_owner}/{repo_name}"
    project = require_project_for_repository(args, ops, owner, repository)
    fields = ops.fetch_project_fields(project.project_id)
    config = ops.project_config_for_args(args)
    project_values, issue_values, issue_field_ids = requested_values(
        args, ops, config, repo_owner, repo_name
    )
    updates = ops.resolve_issue_field_updates(
        fields,
        project_values,
        project_title=args.project_title or "",
    )
    if not updates and not issue_values:
        raise ops.ProjectUsageError("At least one field option must be provided.")

    issue_id = ops.fetch_issue_id(repo_owner, repo_name, args.issue_number or 0)
    item_state = ops.find_project_item_state(project.project_id, issue_id)
    issue_field_ids, issue_writes = issue_field_changes(
        ops, repository, args.issue_number or 0, issue_values, issue_field_ids
    )
    if args.dry_run:
        print_dry_run(args, updates, issue_writes)
        return base_cli.ExitCode.SUCCESS

    item_id, pending_updates = pending_project_updates(ops, project.project_id, item_state, updates, issue_id)
    for update in pending_updates:
        ops.update_item_field(project.project_id, item_id, update)
    if issue_writes:
        ops.write_issue_field_values(
            repo_owner,
            repository,
            args.issue_number or 0,
            issue_writes,
            field_ids=issue_field_ids,
        )
    report_update(args, pending_updates, issue_writes)
    return base_cli.ExitCode.SUCCESS


def require_project_for_repository(
    args: ProjectArguments,
    ops: ProjectOperations,
    owner: str,
    repository: str,
) -> ProjectInfo:
    owner_info: OwnerInfo = ops.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        raise ops.ProjectError(f"Project '{args.project_title}' was not found for owner '{owner}'.")
    linked_repositories = ops.fetch_project_repository_names(owner_info.project.project_id)
    is_linked = repository.casefold() in {linked.casefold() for linked in linked_repositories}
    if is_linked:
        return owner_info.project
    if not args.allow_cross_repo:
        linked_summary = ", ".join(sorted(linked_repositories)) or "none"
        raise ops.ProjectUsageError(
            f"Project '{args.project_title}' is not linked to repository '{repository}'. "
            "Refusing to add or update an issue across repositories. "
            "Use the repository's linked Project or pass --allow-cross-repo intentionally. "
            f"Linked repositories: {linked_summary}."
        )
    print(
        f"WARNING: Updating Project '{args.project_title}' with issue repository '{repository}' "
        "because --allow-cross-repo was supplied.",
        file=sys.stderr,
    )
    return owner_info.project


def requested_values(
    args: ProjectArguments,
    ops: ProjectOperations,
    config: ProjectConfig,
    repo_owner: str,
    repo_name: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    values = ops.issue_field_values_for_args(args)
    if config.field_source is None and DATE_FIELD_KEYS.intersection(values):
        raise ops.ProjectUsageError("Risk tier and date options require project.field_source to be set.")
    issue_values = {
        ISSUE_FIELD_NAMES[key]: value
        for key, value in values.items()
        if key in ISSUE_FIELD_NAMES and (key not in {"priority", "effort"} or config.field_source == "issue_fields")
    }
    project_values = {
        key: value
        for key, value in values.items()
        if key in PROJECT_FIELD_KEYS
        and not (config.field_source == "issue_fields" and key in {"priority", "size"})
    }
    field_ids: dict[str, int] = {}
    if args.start_date_today_if_empty and config.field_source is not None:
        field_ids = ops.organization_issue_field_ids(repo_owner)
        if "Start date" not in field_ids:
            raise ops.ProjectError("Organization issue field 'Start date' was not found.")
        current_values = ops.read_issue_field_values(repo_owner, repo_name, args.issue_number or 0)
        if not current_values.get("Start date") and "start_date" not in values:
            issue_values["Start date"] = date.today().isoformat()
    return project_values, issue_values, field_ids


def issue_field_changes(
    ops: ProjectOperations,
    repository: str,
    issue_number: int,
    issue_values: dict[str, str],
    field_ids: dict[str, int],
) -> tuple[dict[str, int], dict[str, str]]:
    if not issue_values:
        return field_ids, {}
    repo_owner, repo_name = ops.split_repo(repository)
    if not field_ids:
        field_ids = ops.organization_issue_field_ids(repo_owner)
    missing_fields = sorted(set(issue_values) - set(field_ids))
    if missing_fields:
        raise ops.ProjectError("Organization issue field(s) not found: " + ", ".join(missing_fields) + ".")
    current_values = ops.read_issue_field_values(repo_owner, repo_name, issue_number)
    writes = {name: value for name, value in issue_values.items() if current_values.get(name) != value}
    return field_ids, writes


def print_dry_run(
    args: ProjectArguments,
    updates: tuple[FieldUpdate, ...],
    issue_writes: dict[str, str],
) -> None:
    if updates:
        print(f"[DRY-RUN] Would add issue #{args.issue_number} to Project '{args.project_title}' if needed.")
        for update in updates:
            print(f"[DRY-RUN] Would set {update.field_name} to {update.option_name}.")
    for name, value in issue_writes.items():
        print(f"[DRY-RUN] Would set issue field {name} to {value}.")


def pending_project_updates(
    ops: ProjectOperations,
    project_id: str,
    item_state: ProjectItemState | None,
    updates: tuple[FieldUpdate, ...],
    issue_id: str,
) -> tuple[str, tuple[FieldUpdate, ...]]:
    if item_state is None:
        if not updates:
            return "", ()
        return ops.add_project_item(project_id, issue_id), updates
    pending = tuple(
        update for update in updates if item_state.values.get(update.field_name) != update.option_name
    )
    return item_state.item_id, pending


def report_update(
    args: ProjectArguments,
    pending_updates: tuple[FieldUpdate, ...],
    issue_writes: dict[str, str],
) -> None:
    if pending_updates and issue_writes:
        print(f"✓ Updated Project and issue metadata for issue #{args.issue_number}")
    elif pending_updates:
        print(f"✓ Updated Project metadata for issue #{args.issue_number}")
    elif issue_writes:
        print(f"✓ Updated issue fields for issue #{args.issue_number}")
    else:
        print(f"✓ Project metadata already current for issue #{args.issue_number}")
