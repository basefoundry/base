from __future__ import annotations

import sys

import base_cli
import click
from base_projects.command_helpers import ProjectUsageError

from . import project_parser
from . import graphql_queries as queries
# pylint: disable=unused-import
from .project_parser import HELP_OPTIONS, ISSUE_FIELD_OPTIONS, PROJECT_VALUE_OPTIONS
from .project_parser import OptionState, apply_project_option, apply_spaced_option, option_value
from .project_parser import parse_project_options, print_usage, require_project_title, state_to_args
# pylint: enable=unused-import
from .project_configure import standard_template_view_errors
from .project_item_fields import FieldCopySummary
from .project_item_fields import apply_missing_project_item_defaults as _apply_missing_project_item_defaults
from .project_item_fields import copy_missing_project_item_fields as _copy_missing_project_item_fields
# pylint: disable=unused-import
from .project_git import GIT_COMMAND_TIMEOUT_SECONDS  # pylint: disable=unused-import
from .project_git import infer_owner_from_git
from .project_git import infer_repo_from_git
from .project_git import require_owner
from .project_git import require_repo
from .project_git import split_repo
from .project_model import BASE_PROJECT_SCHEMA, DEFAULT_TEMPLATE_PROJECT
from .project_model import ConfigureAction, FieldUpdate, Finding, OwnerInfo
from .project_model import ProjectArguments, ProjectField, ProjectInfo, ProjectSchema, ProjectView
from .project_model import SelectFieldSpec, SelectOption
from .project_schema import ISSUE_DEFAULT_OUTPUT_ORDER  # pylint: disable=unused-import
from .project_schema import compare_schema
from .project_schema import configuration_plan
from .project_schema import find_option  # pylint: disable=unused-import
from .project_schema import issue_defaults_command
from .project_schema import issue_field_values_for_args
from .project_schema import merged_options
from .project_schema import missing_option_names
from .project_schema import options_payload
from .project_schema import project_config_for_args
from .project_schema import project_field_defaults_for_config
from .project_schema import read_project_config
from .project_schema import resolve_issue_field_updates
from .project_schema import schema_for_args
from .project_schema import schema_with_extra_options  # pylint: disable=unused-import
from .project_schema import schema_with_initiatives  # pylint: disable=unused-import
from .project_schema import schema_with_project_config  # pylint: disable=unused-import
# pylint: enable=unused-import
from .project_errors import ProjectAuthError, ProjectError
# pylint: disable=unused-import
from .project_graphql import GITHUB_GRAPHQL_TIMEOUT_SECONDS, is_project_scope_error, run_graphql
# pylint: enable=unused-import


app = base_cli.App(
    name="base_github_projects",
    help="Configure GitHub Projects for Base-managed repositories.",
)

PROJECT_AUTH_EXIT_CODE = 3


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "help_option_names": ["-h", "--help"],
        "ignore_unknown_options": True,
    }
)
@base_cli.argument("arguments", nargs=-1, type=click.UNPROCESSED)
def run(ctx: base_cli.Context, arguments: tuple[str, ...]) -> int:
    del ctx
    try:
        args = parse_args(arguments)
        return run_command(args)
    except SystemExit as exc:
        return int(exc.code or 0)
    except ProjectUsageError as exc:
        print_usage(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR
    except ProjectAuthError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Run `gh auth refresh -h github.com -s project` and retry.", file=sys.stderr)
        return PROJECT_AUTH_EXIT_CODE
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return base_cli.ExitCode.FAILURE


def parse_args(arguments: tuple[str, ...]) -> ProjectArguments:
    return project_parser.parse_args(
        arguments,
        infer_owner_from_git=infer_owner_from_git,
        infer_repo_from_git=infer_repo_from_git,
    )


def run_command(args: ProjectArguments) -> int:
    if args.command == "doctor":
        return doctor_command(args)
    if args.command == "configure":
        return configure_command(args)
    if args.command == "issue-set-fields":
        return issue_set_fields_command(args)
    if args.command == "issue-defaults":
        return issue_defaults_command(args)
    raise ProjectUsageError(f"Unknown project command '{args.command}'.")


def doctor_command(args: ProjectArguments) -> int:
    from .project_doctor_command import doctor_command as command

    return command(args, ops=sys.modules[__name__])


def configure_command(args: ProjectArguments) -> int:
    from .project_configure_command import configure_command as command

    return command(args, ops=sys.modules[__name__])


def issue_set_fields_command(args: ProjectArguments) -> int:
    from .project_issue_fields_command import issue_set_fields_command as command

    return command(args, ops=sys.modules[__name__])


def find_owner_and_project(owner: str, title: str) -> OwnerInfo:
    owner_node = find_owner_node("user", owner)
    if owner_node is None:
        owner_node = find_owner_node("organization", owner)
    if owner_node is None:
        raise ProjectError(f"GitHub owner '{owner}' was not found.")
    project = None
    for node in owner_node.get("projectsV2", {}).get("nodes", []):
        if node.get("title") == title:
            project = ProjectInfo(project_id=node["id"], title=node["title"])
            break
    return OwnerInfo(owner_id=owner_node["id"], login=owner_node["login"], project=project)


def copy_template_project(owner: str, owner_id: str, title: str) -> ProjectInfo:
    template = find_owner_and_project(owner, DEFAULT_TEMPLATE_PROJECT).project
    if template is None:
        raise ProjectError(f"Template Project '{DEFAULT_TEMPLATE_PROJECT}' was not found for owner '{owner}'.")
    return copy_project(template.project_id, owner_id, title)


def find_owner_node(kind: str, owner: str) -> dict[str, object] | None:
    query = f"""
query($login: String!) {{
  {kind}(login: $login) {{
    id
    login
    projectsV2(first: 100) {{ nodes {{ id title }} }}
  }}
}}
"""
    try:
        payload = run_graphql(query, {"login": owner})
    except ProjectAuthError:
        raise
    except ProjectError as exc:
        if is_missing_owner_lookup_error(str(exc), kind):
            return None
        raise
    return payload["data"].get(kind)


def is_missing_owner_lookup_error(message: str, kind: str) -> bool:
    owner_type = "User" if kind == "user" else "Organization"
    return f"Could not resolve to a {owner_type} with the login" in message


def fetch_project_fields(project_id: str) -> tuple[ProjectField, ...]:
    payload = run_graphql(queries.FETCH_PROJECT_FIELDS, {"id": project_id})
    node = payload["data"].get("node")
    if node is None:
        raise ProjectError("GitHub Project was not found.")
    fields: list[ProjectField] = []
    for raw in node["fields"]["nodes"]:
        if raw.get("__typename") not in ("ProjectV2Field", "ProjectV2SingleSelectField"):
            continue
        options = tuple(
            SelectOption(
                name=option["name"],
                color=option["color"],
                description=option.get("description", ""),
                option_id=option.get("id"),
            )
            for option in raw.get("options", ())
        )
        fields.append(ProjectField(raw["id"], raw["name"], raw["dataType"], options))
    return tuple(fields)


def fetch_project_views(project_id: str) -> tuple[ProjectView, ...]:
    payload = run_graphql(queries.FETCH_PROJECT_VIEWS, {"id": project_id})
    node = payload["data"].get("node")
    if node is None:
        raise ProjectError("GitHub Project was not found.")
    return tuple(ProjectView(raw["name"], raw["layout"]) for raw in node["views"]["nodes"])


def verify_standard_template_views(views: tuple[ProjectView, ...]) -> None:
    errors = standard_template_view_errors(views)
    if errors:
        raise ProjectError("Copied Project does not match template views: " + "; ".join(errors))


def create_project(owner_id: str, title: str) -> ProjectInfo:
    payload = run_graphql(queries.CREATE_PROJECT, {"ownerId": owner_id, "title": title})
    project = payload["data"]["createProjectV2"]["projectV2"]
    return ProjectInfo(project_id=project["id"], title=project["title"])


def copy_project(template_project_id: str, owner_id: str, title: str) -> ProjectInfo:
    payload = run_graphql(
        queries.COPY_PROJECT,
        {"projectId": template_project_id, "ownerId": owner_id, "title": title},
    )
    project = payload["data"]["copyProjectV2"]["projectV2"]
    return ProjectInfo(project_id=project["id"], title=project["title"])


def update_project(project_id: str, *, title: str | None = None, closed: bool | None = None) -> None:
    variable_defs = ["$projectId: ID!"]
    input_fields = ["projectId: $projectId"]
    variables: dict[str, object] = {"projectId": project_id}
    if title is not None:
        variable_defs.append("$title: String!")
        input_fields.append("title: $title")
        variables["title"] = title
    if closed is not None:
        variable_defs.append("$closed: Boolean!")
        input_fields.append("closed: $closed")
        variables["closed"] = closed
    if len(variables) == 1:
        raise ValueError("update_project requires title or closed.")

    query = f"""
mutation({', '.join(variable_defs)}) {{
  updateProjectV2(input: {{{', '.join(input_fields)}}}) {{
    projectV2 {{ id title closed }}
  }}
}}
"""
    run_graphql(query, variables)


def fetch_repository_id(repo: str) -> str:
    owner, name = split_repo(repo)
    payload = run_graphql(queries.FETCH_REPOSITORY_ID, {"owner": owner, "name": name})
    repository = payload["data"].get("repository")
    if repository is None:
        raise ProjectError(f"Repository '{repo}' was not found.")
    return repository["id"]


def link_project_to_repository(project_id: str, repo: str) -> None:
    if repo in fetch_project_repository_names(project_id):
        return
    repository_id = fetch_repository_id(repo)
    run_graphql(queries.LINK_PROJECT_TO_REPOSITORY, {"projectId": project_id, "repositoryId": repository_id})


def fetch_project_repository_names(project_id: str) -> set[str]:
    repo_names: set[str] = set()
    cursor: str | None = None
    while True:
        payload = run_graphql(queries.FETCH_PROJECT_REPOSITORY_NAMES, {"projectId": project_id, "cursor": cursor})
        node = payload["data"].get("node")
        if node is None:
            raise ProjectError("GitHub Project was not found.")
        repositories = node["repositories"]
        repo_names.update(raw["nameWithOwner"] for raw in repositories["nodes"])
        if not repositories["pageInfo"]["hasNextPage"]:
            return repo_names
        cursor = repositories["pageInfo"]["endCursor"]


def create_single_select_field(project_id: str, spec: SelectFieldSpec) -> None:
    run_graphql(
        queries.CREATE_SINGLE_SELECT_FIELD,
        {"projectId": project_id, "name": spec.name, "options": options_payload(spec.options)},
    )


def update_single_select_field(field: ProjectField, spec: SelectFieldSpec) -> None:
    run_graphql(
        queries.UPDATE_SINGLE_SELECT_FIELD,
        {"fieldId": field.field_id, "options": options_payload(merged_options(field, spec))},
    )


def fetch_issue_id(owner: str, name: str, number: int) -> str:
    payload = run_graphql(queries.FETCH_ISSUE_ID, {"owner": owner, "name": name, "number": number})
    issue = payload["data"]["repository"]["issue"]
    if issue is None:
        raise ProjectError(f"Issue #{number} was not found in {owner}/{name}.")
    return issue["id"]


def fetch_repository_issue_ids(repo: str) -> tuple[str, ...]:
    owner, name = split_repo(repo)
    issue_ids: list[str] = []
    cursor: str | None = None
    while True:
        payload = run_graphql(queries.FETCH_REPOSITORY_ISSUE_IDS, {"owner": owner, "name": name, "cursor": cursor})
        repository = payload["data"].get("repository")
        if repository is None:
            raise ProjectError(f"Repository '{repo}' was not found.")
        issues = repository["issues"]
        issue_ids.extend(node["id"] for node in issues["nodes"])
        if not issues["pageInfo"]["hasNextPage"]:
            return tuple(issue_ids)
        cursor = issues["pageInfo"]["endCursor"]


def fetch_project_issue_content_ids(project_id: str) -> set[str]:
    issue_ids: set[str] = set()
    cursor: str | None = None
    while True:
        payload = run_graphql(queries.FETCH_PROJECT_ISSUE_CONTENT_IDS, {"projectId": project_id, "cursor": cursor})
        node = payload["data"].get("node")
        if node is None:
            raise ProjectError("GitHub Project was not found.")
        items = node["items"]
        for item in items["nodes"]:
            issue_id = item.get("content", {}).get("id")
            if issue_id:
                issue_ids.add(issue_id)
        if not items["pageInfo"]["hasNextPage"]:
            return issue_ids
        cursor = items["pageInfo"]["endCursor"]


def backfill_repository_issues(project_id: str, repo: str) -> int:
    existing = fetch_project_issue_content_ids(project_id)
    added = 0
    for issue_id in fetch_repository_issue_ids(repo):
        if issue_id in existing:
            continue
        add_project_item(project_id, issue_id)
        existing.add(issue_id)
        added += 1
    return added


def find_project_item_id(project_id: str, issue_id: str) -> str | None:
    payload = run_graphql(queries.FIND_PROJECT_ITEM_ID, {"projectId": project_id})
    for item in payload["data"]["node"]["items"]["nodes"]:
        if item.get("content", {}).get("id") == issue_id:
            return item["id"]
    return None


def add_project_item(project_id: str, issue_id: str) -> str:
    payload = run_graphql(queries.ADD_PROJECT_ITEM, {"projectId": project_id, "contentId": issue_id})
    return payload["data"]["addProjectV2ItemById"]["item"]["id"]


def update_item_field(project_id: str, item_id: str, update: FieldUpdate) -> None:
    run_graphql(
        queries.UPDATE_ITEM_FIELD,
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": update.field_id,
            "optionId": update.option_id,
        },
    )


def copy_missing_project_item_fields(source_project_id: str, target_project_id: str) -> FieldCopySummary:
    return _copy_missing_project_item_fields(
        run_graphql=run_graphql,
        source_project_id=source_project_id,
        target_project_id=target_project_id,
        target_fields=fetch_project_fields(target_project_id),
    )


def apply_missing_project_item_defaults(
    target_project_id: str,
    target_fields: tuple[ProjectField, ...],
    field_defaults: dict[str, str],
) -> FieldCopySummary:
    return _apply_missing_project_item_defaults(
        run_graphql=run_graphql,
        target_project_id=target_project_id,
        target_fields=target_fields,
        field_defaults=field_defaults,
    )
