from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import base_cli
import click

from . import graphql_queries as queries
from .project_configure import standard_template_view_errors
from .project_item_fields import FieldCopySummary
from .project_item_fields import apply_missing_project_item_defaults as _apply_missing_project_item_defaults
from .project_item_fields import copy_missing_project_item_fields as _copy_missing_project_item_fields
from .project_model import BASE_PROJECT_SCHEMA, DEFAULT_TEMPLATE_PROJECT, FIELD_OPTION_TO_PROJECT_FIELD
from .project_model import ConfigureAction, FieldUpdate, Finding, OwnerInfo
from .project_model import ProjectArguments, ProjectField, ProjectInfo, ProjectSchema, ProjectView
from .project_model import SelectFieldSpec, SelectOption
from .project_config import ProjectConfig, ProjectConfigError
from .project_config import read_project_config as _read_project_config
from .project_errors import missing_issue_field_option_message


class ProjectUsageError(RuntimeError):
    pass


class ProjectError(RuntimeError):
    pass


class ProjectAuthError(ProjectError):
    pass


app = base_cli.App(
    name="base_github_projects",
    help="Configure GitHub Projects for Base-managed repositories.",
)

HELP_OPTIONS = ("-h", "--help", "help")
PROJECT_VALUE_OPTIONS = (
    "--project",
    "--owner",
    "--repo",
    "--schema",
    "--config",
    "--copy-fields-from",
    "--initiative-option",
)
ISSUE_FIELD_OPTIONS = ("--status", "--priority", "--area", "--initiative", "--size")


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
        return 2
    except ProjectAuthError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Run `gh auth refresh -h github.com -s project` and retry.", file=sys.stderr)
        return 3
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def print_usage(file=sys.stdout) -> None:
    command = base_cli.delegated_display_command("base_github_projects")
    print(
        "\n".join(
            (
                "Usage:",
                f"  {command} project doctor --project <title> "
                "[--owner <login>] [--schema base-project]",
                f"  {command} project configure --project <title> "
                "[--owner <login>] [--repo <owner/name>] [--schema base-project] [--config <path>] "
                "[--copy-fields-from <title>] [--replace-project] [--initiative-option <name>] [--dry-run]",
                f"  {command} project issue set-fields <number> "
                "--repo <owner/name> --project <title> [--config <path>] [field options...]",
            )
        ),
        file=file,
    )


def parse_args(arguments: tuple[str, ...]) -> ProjectArguments:
    if not arguments or arguments[0] in HELP_OPTIONS:
        print_usage()
        raise SystemExit(0)
    if arguments[0] != "project":
        raise ProjectUsageError(f"Unknown area '{arguments[0]}'.")
    if len(arguments) < 2:
        raise ProjectUsageError("The 'project' area requires a command.")

    command = arguments[1]
    remaining = list(arguments[2:])
    if command == "doctor":
        state = parse_project_options(remaining, allow_fields=False, allow_issue=False)
        require_project_title(state)
        return state_to_args("doctor", state)
    if command == "configure":
        state = parse_project_options(remaining, allow_fields=False, allow_issue=False)
        require_project_title(state)
        return state_to_args("configure", state)
    if command == "issue":
        if len(remaining) < 2 or remaining[0] != "set-fields":
            raise ProjectUsageError("Expected 'project issue set-fields <number>'.")
        try:
            issue_number = int(remaining[1])
        except ValueError as exc:
            raise ProjectUsageError(f"Invalid issue number '{remaining[1]}'.") from exc
        state = parse_project_options(remaining[2:], allow_fields=True, allow_issue=True)
        require_project_title(state)
        if not state.repo:
            state.repo = infer_repo_from_git()
        if not state.repo:
            raise ProjectUsageError("The 'project issue set-fields' command requires --repo.")
        return state_to_args("issue-set-fields", state, issue_number=issue_number)
    raise ProjectUsageError(f"Unknown project command '{command}'.")


@dataclass
class OptionState:
    project_title: str | None = None
    owner: str | None = None
    repo: str | None = None
    schema: str = "base-project"
    config_path: str | None = None
    copy_fields_from_project: str | None = None
    initiative_options: list[str] | None = None
    replace_project: bool = False
    dry_run: bool = False
    field_values: dict[str, str] | None = None


def parse_project_options(remaining: list[str], *, allow_fields: bool, allow_issue: bool) -> OptionState:
    state = OptionState(initiative_options=[], field_values={})
    index = 0
    while index < len(remaining):
        arg = remaining[index]
        if arg in HELP_OPTIONS:
            print_usage()
            raise SystemExit(0)
        if arg == "--dry-run":
            state.dry_run = True
            index += 1
            continue
        if arg == "--replace-project":
            state.replace_project = True
            index += 1
            continue
        consumed = apply_spaced_option(state, remaining, index, allow_fields=allow_fields)
        if consumed:
            index += consumed
            continue
        if allow_issue:
            raise ProjectUsageError(f"Unknown issue field option '{arg}'.")
        raise ProjectUsageError(f"Unknown option '{arg}'.")
    if state.schema != "base-project":
        raise ProjectUsageError("Only project schema 'base-project' is supported.")
    if not state.owner and state.repo:
        state.owner = state.repo.split("/", 1)[0]
    if not state.owner:
        state.owner = infer_owner_from_git()
    return state


def apply_spaced_option(state: OptionState, remaining: list[str], index: int, *, allow_fields: bool) -> int:
    option = remaining[index]
    if option in PROJECT_VALUE_OPTIONS:
        apply_project_option(state, option, option_value(remaining, index))
        return 2
    if allow_fields and option in ISSUE_FIELD_OPTIONS:
        state.field_values[option[2:]] = option_value(remaining, index)
        return 2
    return 0


def option_value(remaining: list[str], index: int) -> str:
    option = remaining[index]
    if index + 1 >= len(remaining):
        raise ProjectUsageError(f"Option '{option}' requires an argument.")
    return remaining[index + 1]


def apply_project_option(state: OptionState, option: str, value: str) -> None:
    if option == "--project":
        state.project_title = value
    elif option == "--owner":
        state.owner = value
    elif option == "--repo":
        state.repo = value
    elif option == "--schema":
        state.schema = value
    elif option == "--config":
        state.config_path = value
    elif option == "--copy-fields-from":
        state.copy_fields_from_project = value
    elif option == "--initiative-option":
        state.initiative_options.append(value)


def require_project_title(state: OptionState) -> None:
    if not state.project_title:
        raise ProjectUsageError("The project command requires --project.")


def state_to_args(command: str, state: OptionState, issue_number: int | None = None) -> ProjectArguments:
    return ProjectArguments(
        area="project",
        command=command,
        project_title=state.project_title,
        owner=state.owner,
        repo=state.repo,
        schema=state.schema,
        config_path=state.config_path,
        copy_fields_from_project=state.copy_fields_from_project,
        initiative_options=tuple(state.initiative_options or ()),
        replace_project=state.replace_project,
        dry_run=state.dry_run,
        issue_number=issue_number,
        field_values=dict(state.field_values or {}),
    )


def run_command(args: ProjectArguments) -> int:
    if args.command == "doctor":
        return doctor_command(args)
    if args.command == "configure":
        return configure_command(args)
    if args.command == "issue-set-fields":
        return issue_set_fields_command(args)
    raise ProjectUsageError(f"Unknown project command '{args.command}'.")


def schema_for_args(args: ProjectArguments) -> ProjectSchema:
    if args.schema != "base-project":
        raise ProjectUsageError("Only project schema 'base-project' is supported.")
    config = project_config_for_args(args)
    if args.initiative_options:
        return schema_with_project_config(
            schema_with_initiatives(BASE_PROJECT_SCHEMA, args.initiative_options),
            config,
        )
    return schema_with_project_config(BASE_PROJECT_SCHEMA, config)


def project_config_for_args(args: ProjectArguments) -> ProjectConfig:
    if not args.config_path:
        return ProjectConfig()
    return read_project_config(Path(args.config_path))


def issue_field_values_for_args(args: ProjectArguments) -> dict[str, str]:
    config = project_config_for_args(args)
    values = dict(config.issue_defaults)
    values.update(args.field_values or {})
    return values


def project_field_defaults_for_config(config: ProjectConfig) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for value_key, field_name in FIELD_OPTION_TO_PROJECT_FIELD.items():
        option_name = config.issue_defaults.get(value_key)
        if option_name:
            defaults[field_name] = option_name
    return defaults


def read_project_config(path: Path) -> ProjectConfig:
    try:
        return _read_project_config(path)
    except ProjectConfigError as exc:
        raise ProjectUsageError(str(exc)) from exc


def schema_with_initiatives(schema: ProjectSchema, initiative_options: tuple[str, ...]) -> ProjectSchema:
    return schema_with_extra_options(schema, "Initiative", initiative_options, "Project-specific initiative.")


def schema_with_project_config(schema: ProjectSchema, config: ProjectConfig) -> ProjectSchema:
    schema = schema_with_extra_options(schema, "Area", config.areas, "Repository-specific area.")
    return schema_with_extra_options(schema, "Initiative", config.initiatives, "Repository-specific initiative.")


def schema_with_extra_options(
    schema: ProjectSchema, field_name: str, option_names: tuple[str, ...], description: str
) -> ProjectSchema:
    if not option_names:
        return schema
    fields: list[SelectFieldSpec] = []
    for field in schema.fields:
        if field.name != field_name:
            fields.append(field)
            continue
        existing = {option.name for option in field.options}
        options = list(field.options)
        for option_name in option_names:
            if option_name not in existing:
                options.append(SelectOption(option_name, "GRAY", description))
                existing.add(option_name)
        fields.append(SelectFieldSpec(field.name, tuple(options)))
    return ProjectSchema(tuple(fields))


def compare_schema(fields: tuple[ProjectField, ...], schema: ProjectSchema) -> tuple[Finding, ...]:
    by_name = {field.name: field for field in fields}
    findings: list[Finding] = []
    for spec in schema.fields:
        field = by_name.get(spec.name)
        if field is None:
            findings.append(Finding("missing", spec.name, f"{spec.name} field is missing."))
            continue
        if field.data_type != "SINGLE_SELECT":
            findings.append(
                Finding("error", spec.name, f"{spec.name} exists with type {field.data_type}; expected SINGLE_SELECT.")
            )
            continue
        existing_options = {option.name for option in field.options}
        for option in spec.options:
            if option.name not in existing_options:
                findings.append(Finding("missing-option", spec.name, f"{spec.name} option {option.name} is missing."))
    return tuple(findings)


def configuration_plan(
    *, project_exists: bool, fields: tuple[ProjectField, ...], schema: ProjectSchema
) -> tuple[ConfigureAction, ...]:
    actions: list[ConfigureAction] = []
    if not project_exists:
        actions.append(ConfigureAction("create-project", "Project", "Create GitHub Project."))
    by_name = {field.name: field for field in fields}
    for spec in schema.fields:
        field = by_name.get(spec.name)
        if field is None:
            actions.append(ConfigureAction("create-field", spec.name, f"Create {spec.name} as SINGLE_SELECT."))
            continue
        if field.data_type != "SINGLE_SELECT":
            message = f"{spec.name} exists with type {field.data_type}; expected SINGLE_SELECT."
            actions.append(
                ConfigureAction("error", spec.name, message)
            )
            continue
        existing_options = {option.name for option in field.options}
        missing_options = [option.name for option in spec.options if option.name not in existing_options]
        if missing_options:
            actions.append(
                ConfigureAction("update-field", spec.name, f"Add missing options: {', '.join(missing_options)}.")
            )
    return tuple(actions)


def merged_options(field: ProjectField, spec: SelectFieldSpec) -> tuple[SelectOption, ...]:
    merged = list(field.options)
    names = {option.name for option in merged}
    for option in spec.options:
        if option.name not in names:
            merged.append(option)
            names.add(option.name)
    return tuple(merged)


def resolve_issue_field_updates(
    fields: tuple[ProjectField, ...], values: dict[str, str], *, project_title: str
) -> tuple[FieldUpdate, ...]:
    by_name = {field.name: field for field in fields}
    updates: list[FieldUpdate] = []
    for value_key, field_name in FIELD_OPTION_TO_PROJECT_FIELD.items():
        option_name = values.get(value_key)
        if not option_name:
            continue
        field = by_name.get(field_name)
        if field is None:
            raise ProjectUsageError(f"{field_name} field was not found in Project '{project_title}'.")
        option = find_option(field, option_name)
        if option is None or option.option_id is None:
            raise ProjectUsageError(missing_issue_field_option_message(field_name, option_name, project_title))
        updates.append(FieldUpdate(field.field_id, option.option_id, field_name, option_name))
    return tuple(updates)


def find_option(field: ProjectField, name: str) -> SelectOption | None:
    for option in field.options:
        if option.name == name:
            return option
    return None


def doctor_command(args: ProjectArguments) -> int:
    from .project_doctor_command import doctor_command as command

    return command(args, ops=sys.modules[__name__])


def configure_command(args: ProjectArguments) -> int:
    from .project_configure_command import configure_command as command

    return command(args, ops=sys.modules[__name__])


def issue_set_fields_command(args: ProjectArguments) -> int:
    from .project_issue_fields_command import issue_set_fields_command as command

    return command(args, ops=sys.modules[__name__])


def require_owner(args: ProjectArguments) -> str:
    owner = args.owner
    if not owner and args.repo:
        owner = args.repo.split("/", 1)[0]
    if not owner:
        owner = infer_owner_from_git()
    if not owner:
        raise ProjectUsageError("Project owner is required. Pass --owner <login>.")
    return owner


def require_repo(args: ProjectArguments) -> str:
    repo = args.repo or infer_repo_from_git()
    if not repo:
        raise ProjectUsageError("Repository is required. Pass --repo <owner/name>.")
    return repo


def split_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ProjectUsageError(f"Repository must be in owner/name form, got '{repo}'.")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise ProjectUsageError(f"Repository must be in owner/name form, got '{repo}'.")
    return owner, name


def infer_owner_from_git() -> str | None:
    repo = infer_repo_from_git()
    return repo.split("/", 1)[0] if repo else None


def infer_repo_from_git() -> str | None:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    if remote.startswith("git@github.com:"):
        remote = remote.removeprefix("git@github.com:")
    elif remote.startswith("https://github.com/"):
        remote = remote.removeprefix("https://github.com/")
    else:
        return None
    remote = remote.removesuffix(".git")
    return remote if "/" in remote else None


def run_graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
    payload = json.dumps({"query": query, "variables": variables})
    result = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        if is_project_scope_error(message):
            raise ProjectAuthError(message or "GitHub Project access requires the project scope.")
        raise ProjectError(message or "GitHub GraphQL request failed.")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProjectError("GitHub GraphQL returned invalid JSON.") from exc
    if data.get("errors"):
        message = "; ".join(str(error.get("message", error)) for error in data["errors"])
        if is_project_scope_error(message):
            raise ProjectAuthError(message)
        raise ProjectError(message)
    return data


def is_project_scope_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "project" in lowered
        and ("scope" in lowered or "resource not accessible" in lowered or "forbidden" in lowered)
    ) or "projectv2" in lowered and "not accessible" in lowered


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


def options_payload(options: tuple[SelectOption, ...]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for option in options:
        item = {"name": option.name, "color": option.color, "description": option.description}
        if option.option_id:
            item["id"] = option.option_id
        payload.append(item)
    return payload


def missing_option_names(field: ProjectField, spec: SelectFieldSpec) -> tuple[str, ...]:
    existing = {option.name for option in field.options}
    return tuple(option.name for option in spec.options if option.name not in existing)


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
