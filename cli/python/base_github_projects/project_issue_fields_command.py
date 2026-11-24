from __future__ import annotations

from datetime import date
import sys

import base_cli

from .project_model import ProjectArguments
from .project_operations import ProjectOperations


def issue_set_fields_command(args: ProjectArguments, ops: ProjectOperations) -> int:
    owner = ops.require_owner(args)
    repo = ops.require_repo(args)
    repo_owner, repo_name = ops.split_repo(repo)
    repo = f"{repo_owner}/{repo_name}"
    owner_info = ops.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        raise ops.ProjectError(f"Project '{args.project_title}' was not found for owner '{owner}'.")
    project = owner_info.project
    linked_repositories = ops.fetch_project_repository_names(project.project_id)
    normalized_repo = repo.casefold()
    if not args.allow_cross_repo and normalized_repo not in {linked.casefold() for linked in linked_repositories}:
        linked_summary = ", ".join(sorted(linked_repositories)) or "none"
        raise ops.ProjectUsageError(
            f"Project '{args.project_title}' is not linked to repository '{repo}'. "
            "Refusing to add or update an issue across repositories. "
            "Use the repository's linked Project or pass --allow-cross-repo intentionally. "
            f"Linked repositories: {linked_summary}."
        )
    if args.allow_cross_repo and normalized_repo not in {linked.casefold() for linked in linked_repositories}:
        print(
            f"WARNING: Updating Project '{args.project_title}' with issue repository '{repo}' "
            "because --allow-cross-repo was supplied.",
            file=sys.stderr,
        )
    fields = ops.fetch_project_fields(project.project_id)
    config = ops.project_config_for_args(args)
    values = ops.issue_field_values_for_args(args)
    issue_field_names = {
        "priority": "Priority",
        "effort": "Effort",
        "risk_tier": "Risk tier",
        "start_date": "Start date",
        "target_date": "Target date",
    }
    if config.field_source is None and any(key in values for key in ("risk_tier", "start_date", "target_date")):
        raise ops.ProjectUsageError("Risk tier and date options require project.field_source to be set.")
    issue_values = {
        issue_field_names[key]: value
        for key, value in values.items()
        if key in issue_field_names and (key not in {"priority", "effort"} or config.field_source == "issue_fields")
    }
    project_values = {
        key: value
        for key, value in values.items()
        if key in {"status", "priority", "area", "initiative", "size"}
        and not (config.field_source == "issue_fields" and key in {"priority", "size"})
    }
    if args.start_date_today_if_empty and config.field_source is not None:
        issue_field_ids = ops.organization_issue_field_ids(repo_owner)
        if "Start date" not in issue_field_ids:
            raise ops.ProjectError("Organization issue field 'Start date' was not found.")
        current_issue_values = ops.read_issue_field_values(repo_owner, repo_name, args.issue_number or 0)
        if not current_issue_values.get("Start date") and "start_date" not in values:
            issue_values["Start date"] = date.today().isoformat()
    else:
        issue_field_ids = {}

    updates = ops.resolve_issue_field_updates(
        fields,
        project_values,
        project_title=args.project_title or "",
    )
    if not updates and not issue_values:
        raise ops.ProjectUsageError("At least one field option must be provided.")
    issue_id = ops.fetch_issue_id(repo_owner, repo_name, args.issue_number or 0)
    item_state = ops.find_project_item_state(project.project_id, issue_id)
    issue_fields_to_write: dict[str, str] = {}
    if issue_values:
        if not issue_field_ids:
            issue_field_ids = ops.organization_issue_field_ids(repo_owner)
        missing_fields = sorted(set(issue_values) - set(issue_field_ids))
        if missing_fields:
            raise ops.ProjectError("Organization issue field(s) not found: " + ", ".join(missing_fields) + ".")
        current_issue_values = ops.read_issue_field_values(repo_owner, repo_name, args.issue_number or 0)
        issue_fields_to_write = {
            name: value for name, value in issue_values.items() if current_issue_values.get(name) != value
        }
    if args.dry_run:
        if updates:
            print(f"[DRY-RUN] Would add issue #{args.issue_number} to Project '{args.project_title}' if needed.")
            for update in updates:
                print(f"[DRY-RUN] Would set {update.field_name} to {update.option_name}.")
        for name, value in issue_fields_to_write.items():
            print(f"[DRY-RUN] Would set issue field {name} to {value}.")
        return base_cli.ExitCode.SUCCESS
    if item_state is None and updates:
        item_id = ops.add_project_item(project.project_id, issue_id)
        pending_updates = updates
    elif item_state is None:
        item_id = ""
        pending_updates = ()
    else:
        item_id = item_state.item_id
        pending_updates = tuple(
            update for update in updates if item_state.values.get(update.field_name) != update.option_name
        )
    for update in pending_updates:
        ops.update_item_field(project.project_id, item_id, update)
    if issue_fields_to_write:
        ops.write_issue_field_values(
            owner,
            repo_name,
            args.issue_number or 0,
            issue_fields_to_write,
            field_ids=issue_field_ids,
            repository_owner=repo_owner,
        )
    if pending_updates or issue_fields_to_write:
        if pending_updates and issue_fields_to_write:
            print(f"✓ Updated Project and issue metadata for issue #{args.issue_number}")
        elif pending_updates:
            print(f"✓ Updated Project metadata for issue #{args.issue_number}")
        else:
            print(f"✓ Updated issue fields for issue #{args.issue_number}")
    else:
        print(f"✓ Project metadata already current for issue #{args.issue_number}")
    return base_cli.ExitCode.SUCCESS
