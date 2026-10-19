from __future__ import annotations

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
    updates = ops.resolve_issue_field_updates(
        fields,
        ops.issue_field_values_for_args(args),
        project_title=args.project_title or "",
    )
    if not updates:
        raise ops.ProjectUsageError("At least one field option must be provided.")
    issue_id = ops.fetch_issue_id(repo_owner, repo_name, args.issue_number or 0)
    item_state = ops.find_project_item_state(project.project_id, issue_id)
    if args.dry_run:
        print(f"[DRY-RUN] Would add issue #{args.issue_number} to Project '{args.project_title}' if needed.")
        for update in updates:
            print(f"[DRY-RUN] Would set {update.field_name} to {update.option_name}.")
        return base_cli.ExitCode.SUCCESS
    if item_state is None:
        item_id = ops.add_project_item(project.project_id, issue_id)
        pending_updates = updates
    else:
        item_id = item_state.item_id
        pending_updates = tuple(
            update for update in updates if item_state.values.get(update.field_name) != update.option_name
        )
    for update in pending_updates:
        ops.update_item_field(project.project_id, item_id, update)
    if pending_updates:
        print(f"✓ Updated Project metadata for issue #{args.issue_number}")
    else:
        print(f"✓ Project metadata already current for issue #{args.issue_number}")
    return base_cli.ExitCode.SUCCESS
