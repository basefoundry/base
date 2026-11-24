from __future__ import annotations

import sys
from datetime import date

import base_cli
from base_cli_profile import base_cli_app
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
from .project_model import ProjectArguments, ProjectField, ProjectInfo, ProjectIssueData
from .project_model import ProjectItemState, ProjectSchema, ProjectView
from .project_model import SelectFieldSpec, SelectOption
from .project_operations import ProjectOperations
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
from .project_errors import ProjectAuthError, ProjectError, ProjectTransportError
# pylint: disable=unused-import
from .project_graphql import GITHUB_GRAPHQL_TIMEOUT_SECONDS, is_project_scope_error, run_graphql
from .issue_field_values import organization_issue_field_ids, read_issue_field_values, write_issue_field_values
from .project_rest import RestIssueFieldRequest, RestProjectTransport, rest_doctor_command
# pylint: enable=unused-import


app = base_cli_app(
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
    if args.command == "issue-copy-fields":
        return copy_issue_fields_command(args)
    if args.command == "issue-defaults":
        return issue_defaults_command(args)
    raise ProjectUsageError(f"Unknown project command '{args.command}'.")


def project_operations() -> ProjectOperations:
    return ProjectOperations(
        ProjectError=ProjectError,
        ProjectUsageError=ProjectUsageError,
        add_project_item=add_project_item,
        apply_missing_project_item_defaults=apply_missing_project_item_defaults,
        backfill_repository_issues=backfill_repository_issues,
        compare_schema=compare_schema,
        configuration_plan=configuration_plan,
        copy_missing_project_item_fields=copy_missing_project_item_fields,
        copy_template_project=copy_template_project,
        create_project=create_project,
        create_single_select_field=create_single_select_field,
        fetch_issue_id=fetch_issue_id,
        fetch_project_fields=fetch_project_fields,
        fetch_project_issue_items=fetch_project_issue_items,
        organization_issue_field_ids=organization_issue_field_ids,
        fetch_project_repository_names=fetch_project_repository_names,
        fetch_project_views=fetch_project_views,
        find_owner_and_project=find_owner_and_project,
        find_project_item_id=find_project_item_id,
        find_project_item_state=find_project_item_state,
        issue_field_values_for_args=issue_field_values_for_args,
        link_project_to_repository=link_project_to_repository,
        missing_option_names=missing_option_names,
        project_config_for_args=project_config_for_args,
        project_field_defaults_for_config=project_field_defaults_for_config,
        read_issue_field_values=read_issue_field_values,
        require_owner=require_owner,
        require_repo=require_repo,
        resolve_issue_field_updates=resolve_issue_field_updates,
        schema_for_args=schema_for_args,
        split_repo=split_repo,
        update_item_field=update_item_field,
        write_issue_field_values=write_issue_field_values,
        update_project=update_project,
        update_single_select_field=update_single_select_field,
        verify_standard_template_views=verify_standard_template_views,
    )


def doctor_command(args: ProjectArguments) -> int:
    from .project_doctor_command import doctor_command as command

    try:
        return command(args, ops=project_operations())
    except ProjectTransportError as exc:
        print(
            f"WARNING: GraphQL Project transport unavailable; using REST Projects API: {exc}",
            file=sys.stderr,
        )
        return rest_doctor_command(
            args,
            transport=RestProjectTransport(),
            compare_schema=compare_schema,
            schema_for_args=schema_for_args,
        )


def configure_command(args: ProjectArguments) -> int:
    from .project_configure_command import configure_command as command

    return command(args, ops=project_operations())


def issue_set_fields_command(args: ProjectArguments) -> int:
    from .project_issue_fields_command import issue_set_fields_command as command

    try:
        return command(args, ops=project_operations())
    except ProjectTransportError as exc:
        print(
            f"WARNING: GraphQL Project transport unavailable; using REST Projects API: {exc}",
            file=sys.stderr,
        )
        return rest_issue_set_fields_command(args)


def copy_issue_fields_command(args: ProjectArguments) -> int:
    from .project_issue_field_copy_command import copy_issue_fields_command as command

    return command(args, ops=project_operations())


def rest_issue_set_fields_command(args: ProjectArguments) -> int:
    owner = require_owner(args)
    repo = require_repo(args)
    repo_owner, repo_name = split_repo(repo)
    config = project_config_for_args(args)
    values = issue_field_values_for_args(args)

    issue_field_names = {
        "priority": "Priority",
        "effort": "Effort",
        "risk_tier": "Risk tier",
        "start_date": "Start date",
        "target_date": "Target date",
    }
    if config.field_source is None and any(
        key in values for key in ("risk_tier", "start_date", "target_date")
    ):
        raise ProjectUsageError("Risk tier and date options require project.field_source to be set.")
    issue_values = {
        issue_field_names[key]: value
        for key, value in values.items()
        if key in issue_field_names and (key not in {"priority", "effort"} or config.field_source == "issue_fields")
    }
    if args.start_date_today_if_empty and config.field_source is not None and "start_date" not in values:
        current_values = read_issue_field_values(repo_owner, repo_name, args.issue_number or 0)
        if not current_values.get("Start date"):
            issue_values["Start date"] = date.today().isoformat()
    project_values = {
        key: value
        for key, value in values.items()
        if key in {"status", "priority", "area", "initiative", "size"}
        and not (config.field_source == "issue_fields" and key in {"priority", "size"})
    }
    if not project_values and not issue_values:
        raise ProjectUsageError("At least one field option must be provided.")

    def resolve_updates(fields: tuple[ProjectField, ...], field_values: dict[str, str]) -> tuple[FieldUpdate, ...]:
        return resolve_issue_field_updates(fields, field_values, project_title=args.project_title or "")

    if project_values:
        RestProjectTransport().reconcile_issue_fields(
            RestIssueFieldRequest(
                owner=owner,
                repo_owner=repo_owner,
                repo_name=repo_name,
                issue_number=args.issue_number or 0,
                project_title=args.project_title or "",
                field_values=project_values,
                resolve_updates=resolve_updates,
                dry_run=args.dry_run,
                allow_cross_repo=args.allow_cross_repo,
            )
        )
    else:
        transport = RestProjectTransport()
        owner_info = transport.find_owner_and_project(owner, args.project_title or "")
        if owner_info.project is None:
            raise ProjectError(f"Project '{args.project_title}' was not found for owner '{owner}'.")
        if not args.allow_cross_repo and owner.casefold() != repo_owner.casefold():
            raise ProjectUsageError(
                f"Project '{args.project_title}' could not verify repository ownership for "
                f"'{repo_owner}/{repo_name}' during REST recovery. The REST fallback only permits "
                "same-owner repositories; pass --allow-cross-repo intentionally."
            )

    update_rest_issue_fields(args, owner, repo_owner, repo_name, issue_values)
    return base_cli.ExitCode.SUCCESS


def update_rest_issue_fields(
    args: ProjectArguments,
    owner: str,
    repo_owner: str,
    repo_name: str,
    issue_values: dict[str, str],
) -> None:
    if not issue_values:
        return
    field_ids = organization_issue_field_ids(owner)
    missing_fields = sorted(set(issue_values) - set(field_ids))
    if missing_fields:
        raise ProjectError("Organization issue field(s) not found: " + ", ".join(missing_fields) + ".")
    current_values = read_issue_field_values(repo_owner, repo_name, args.issue_number or 0)
    pending = {name: value for name, value in issue_values.items() if current_values.get(name) != value}
    if args.dry_run:
        for name, value in pending.items():
            print(f"[DRY-RUN] Would set issue field {name} to {value}.")
    elif pending:
        write_issue_field_values(
            owner,
            f"{repo_owner}/{repo_name}",
            args.issue_number or 0,
            pending,
            field_ids=field_ids,
        )
        print(f"✓ Updated issue fields for issue #{args.issue_number} (REST fallback)")


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


def fetch_project_issue_items(project_id: str) -> tuple[ProjectIssueData, ...]:
    items_found: list[ProjectIssueData] = []
    cursor: str | None = None
    while True:
        payload = run_graphql(
            queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_ISSUE_FIELDS,
            {"projectId": project_id, "cursor": cursor},
        )
        node = payload["data"].get("node")
        if node is None:
            raise ProjectError("GitHub Project was not found.")
        items = node["items"]
        for item in items["nodes"]:
            content = item.get("content") or {}
            repository = (content.get("repository") or {}).get("nameWithOwner")
            if not content.get("id") or not content.get("number") or not repository:
                continue
            project_values: dict[str, str] = {}
            for raw in item.get("fieldValues", {}).get("nodes", []):
                if raw.get("__typename") != "ProjectV2ItemFieldSingleSelectValue":
                    continue
                field_name = (raw.get("field") or {}).get("name")
                if field_name and raw.get("name"):
                    project_values[field_name] = raw["name"]
            issue_values: dict[str, str] = {}
            for raw in content.get("issueFieldValues", {}).get("nodes", []):
                field_name = (raw.get("field") or {}).get("name")
                value = raw.get("name") or raw.get("value")
                if field_name and value is not None:
                    issue_values[field_name] = str(value)
            items_found.append(
                ProjectIssueData(
                    item_id=item["id"],
                    issue_id=content["id"],
                    repository=repository,
                    number=int(content["number"]),
                    title=str(content.get("title") or ""),
                    project_values=project_values,
                    issue_values=issue_values,
                )
            )
        if not items["pageInfo"]["hasNextPage"]:
            return tuple(items_found)
        cursor = items["pageInfo"]["endCursor"]


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


def fetch_repository_issues(repo: str) -> tuple[tuple[str, int], ...]:
    owner, name = split_repo(repo)
    issues_found: list[tuple[str, int]] = []
    cursor: str | None = None
    while True:
        payload = run_graphql(queries.FETCH_REPOSITORY_ISSUES, {"owner": owner, "name": name, "cursor": cursor})
        repository = payload["data"].get("repository")
        if repository is None:
            raise ProjectError(f"Repository '{repo}' was not found.")
        issues = repository["issues"]
        issues_found.extend((node["id"], node["number"]) for node in issues["nodes"])
        if not issues["pageInfo"]["hasNextPage"]:
            return tuple(issues_found)
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


def backfill_repository_issues(project_id: str, repo: str) -> tuple[int, ...]:
    existing = fetch_project_issue_content_ids(project_id)
    added: list[int] = []
    for issue_id, issue_number in fetch_repository_issues(repo):
        if issue_id in existing:
            continue
        add_project_item(project_id, issue_id)
        existing.add(issue_id)
        added.append(issue_number)
    return tuple(sorted(added))


def find_project_item_id(project_id: str, issue_id: str) -> str | None:
    payload = run_graphql(queries.FIND_PROJECT_ITEM_ID, {"projectId": project_id})
    for item in payload["data"]["node"]["items"]["nodes"]:
        if item.get("content", {}).get("id") == issue_id:
            return item["id"]
    return None


def find_project_item_state(project_id: str, issue_id: str) -> ProjectItemState | None:
    payload = run_graphql(queries.FIND_PROJECT_ITEM_WITH_FIELDS, {"projectId": project_id})
    for item in payload["data"]["node"]["items"]["nodes"]:
        if (item.get("content") or {}).get("id") != issue_id:
            continue
        values: dict[str, str] = {}
        for raw_value in item.get("fieldValues", {}).get("nodes", []):
            if raw_value.get("__typename") != "ProjectV2ItemFieldSingleSelectValue":
                continue
            field_name = (raw_value.get("field") or {}).get("name")
            if field_name and raw_value.get("name"):
                values[field_name] = raw_value["name"]
        return ProjectItemState(item_id=item["id"], values=values)
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
