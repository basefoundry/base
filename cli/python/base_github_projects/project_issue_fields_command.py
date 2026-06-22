from __future__ import annotations

from typing import Any


def issue_set_fields_command(args: Any, ops: Any) -> int:
    owner = ops.require_owner(args)
    repo = ops.require_repo(args)
    owner_info = ops.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        raise ops.ProjectError(f"Project '{args.project_title}' was not found for owner '{owner}'.")
    project = owner_info.project
    fields = ops.fetch_project_fields(project.project_id)
    updates = ops.resolve_issue_field_updates(
        fields,
        ops.issue_field_values_for_args(args),
        project_title=args.project_title or "",
    )
    if not updates:
        raise ops.ProjectUsageError("At least one field option must be provided.")
    repo_owner, repo_name = ops.split_repo(repo)
    issue_id = ops.fetch_issue_id(repo_owner, repo_name, args.issue_number or 0)
    item_id = ops.find_project_item_id(project.project_id, issue_id)
    if args.dry_run:
        print(f"[DRY-RUN] Would add issue #{args.issue_number} to Project '{args.project_title}' if needed.")
        for update in updates:
            print(f"[DRY-RUN] Would set {update.field_name} to {update.option_name}.")
        return 0
    if item_id is None:
        item_id = ops.add_project_item(project.project_id, issue_id)
    for update in updates:
        ops.update_item_field(project.project_id, item_id, update)
    print(f"✓ Updated Project metadata for issue #{args.issue_number}")
    return 0
