from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass


class ProjectUsageError(RuntimeError):
    pass


class ProjectError(RuntimeError):
    pass


class ProjectAuthError(ProjectError):
    pass


@dataclass(frozen=True)
class SelectOption:
    name: str
    color: str
    description: str
    option_id: str | None = None


@dataclass(frozen=True)
class SelectFieldSpec:
    name: str
    options: tuple[SelectOption, ...]


@dataclass(frozen=True)
class ProjectSchema:
    fields: tuple[SelectFieldSpec, ...]

    def field_by_name(self, name: str) -> SelectFieldSpec:
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError(name)


@dataclass(frozen=True)
class ProjectField:
    field_id: str
    name: str
    data_type: str
    options: tuple[SelectOption, ...] = ()


@dataclass(frozen=True)
class Finding:
    status: str
    name: str
    message: str


@dataclass(frozen=True)
class ConfigureAction:
    action: str
    name: str
    message: str


@dataclass(frozen=True)
class FieldUpdate:
    field_id: str
    option_id: str
    field_name: str
    option_name: str


@dataclass(frozen=True)
class ProjectInfo:
    project_id: str
    title: str


@dataclass(frozen=True)
class OwnerInfo:
    owner_id: str
    login: str
    project: ProjectInfo | None


@dataclass(frozen=True)
class ProjectArguments:
    area: str
    command: str
    project_title: str | None = None
    owner: str | None = None
    repo: str | None = None
    schema: str = "base-roadmap"
    initiative_options: tuple[str, ...] = ()
    dry_run: bool = False
    issue_number: int | None = None
    field_values: dict[str, str] | None = None


BASE_ROADMAP_SCHEMA = ProjectSchema(
    fields=(
        SelectFieldSpec(
            "Status",
            (
                SelectOption("Triage", "GRAY", "Needs clarification or initial classification."),
                SelectOption("Backlog", "BLUE", "Accepted but not yet scheduled."),
                SelectOption("Ready", "GREEN", "Scoped enough to pick up."),
                SelectOption("In Progress", "YELLOW", "Actively being worked on."),
                SelectOption("In Review", "ORANGE", "Pull request open, waiting on checks or review."),
                SelectOption("Done", "PURPLE", "Completed or no further work remains."),
            ),
        ),
        SelectFieldSpec(
            "Priority",
            (
                SelectOption("P0", "RED", "Urgent or blocking."),
                SelectOption("P1", "ORANGE", "High priority."),
                SelectOption("P2", "YELLOW", "Normal priority."),
                SelectOption("P3", "BLUE", "Low priority or opportunistic."),
            ),
        ),
        SelectFieldSpec(
            "Area",
            (
                SelectOption("CLI", "GRAY", "Command surface and user-facing CLI behavior."),
                SelectOption("Setup", "GRAY", "Installation, setup, check, and doctor behavior."),
                SelectOption("Workspace", "GRAY", "Workspace discovery and workspace-level commands."),
                SelectOption("Manifest", "GRAY", "Manifest schema and project contract handling."),
                SelectOption("Runtime", "GRAY", "Activation, shell runtime, and environment behavior."),
                SelectOption("Shell", "GRAY", "Shell libraries, completions, and startup files."),
                SelectOption("Python", "GRAY", "Python command packages and shared Python helpers."),
                SelectOption("Docs", "GRAY", "Documentation and AI context."),
                SelectOption("CI", "GRAY", "Continuous integration and validation automation."),
                SelectOption("Packaging", "GRAY", "Release, Homebrew, installer, and distribution work."),
                SelectOption("Security", "GRAY", "Permission, secret-handling, and hardening work."),
                SelectOption("Product", "GRAY", "Product direction, roadmap, and adoption work."),
            ),
        ),
        SelectFieldSpec(
            "Size",
            (
                SelectOption("S", "GREEN", "Small, focused change."),
                SelectOption("M", "YELLOW", "Medium change with multiple files or interactions."),
                SelectOption("L", "ORANGE", "Large change that should be split if possible."),
            ),
        ),
        SelectFieldSpec(
            "Initiative",
            (
                SelectOption("BanyanLabs Dogfood", "GRAY", "Dogfood Base through BanyanLabs."),
                SelectOption("Workspace Handling", "GRAY", "Workspace discovery and orchestration."),
                SelectOption("pyproject/uv", "GRAY", "Python packaging and uv integration."),
                SelectOption("v1.0 Readiness", "GRAY", "Stable public release readiness."),
                SelectOption("Adoption Polish", "GRAY", "Install, docs, and adoption polish."),
            ),
        ),
    )
)


FIELD_OPTION_TO_PROJECT_FIELD = {
    "status": "Status",
    "priority": "Priority",
    "area": "Area",
    "initiative": "Initiative",
    "size": "Size",
}
HELP_OPTIONS = ("-h", "--help", "help")
PROJECT_VALUE_OPTIONS = ("--project", "--owner", "--repo", "--schema", "--initiative-option")
ISSUE_FIELD_OPTIONS = ("--status", "--priority", "--area", "--initiative", "--size")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(tuple(sys.argv[1:] if argv is None else argv))
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
    print(
        "\n".join(
            (
                "Usage:",
                "  base_github_projects project doctor --project <title> "
                "[--owner <login>] [--schema base-roadmap]",
                "  base_github_projects project configure --project <title> "
                "[--owner <login>] [--repo <owner/name>] [--schema base-roadmap] "
                "[--initiative-option <name>] [--dry-run]",
                "  base_github_projects project issue set-fields <number> "
                "--repo <owner/name> --project <title> [field options...]",
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
    schema: str = "base-roadmap"
    initiative_options: list[str] | None = None
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
        if apply_equals_option(state, arg, allow_fields=allow_fields):
            index += 1
            continue
        if arg == "--dry-run":
            state.dry_run = True
            index += 1
            continue
        consumed = apply_spaced_option(state, remaining, index, allow_fields=allow_fields)
        if consumed:
            index += consumed
            continue
        if allow_issue:
            raise ProjectUsageError(f"Unknown issue field option '{arg}'.")
        raise ProjectUsageError(f"Unknown option '{arg}'.")
    if state.schema != "base-roadmap":
        raise ProjectUsageError("Only project schema 'base-roadmap' is supported.")
    if not state.owner and state.repo:
        state.owner = state.repo.split("/", 1)[0]
    if not state.owner:
        state.owner = infer_owner_from_git()
    return state


def apply_equals_option(state: OptionState, arg: str, *, allow_fields: bool) -> bool:
    if not arg.startswith("--") or "=" not in arg:
        return False
    name, value = arg.split("=", 1)
    if name in PROJECT_VALUE_OPTIONS:
        apply_project_option(state, name, value)
        return True
    if allow_fields and name in ISSUE_FIELD_OPTIONS:
        state.field_values[name[2:]] = value
        return True
    return False


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
        initiative_options=tuple(state.initiative_options or ()),
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
    if args.schema != "base-roadmap":
        raise ProjectUsageError("Only project schema 'base-roadmap' is supported.")
    if args.initiative_options:
        return schema_with_initiatives(BASE_ROADMAP_SCHEMA, args.initiative_options)
    return BASE_ROADMAP_SCHEMA


def schema_with_initiatives(schema: ProjectSchema, initiative_options: tuple[str, ...]) -> ProjectSchema:
    fields: list[SelectFieldSpec] = []
    for field in schema.fields:
        if field.name != "Initiative":
            fields.append(field)
            continue
        existing = {option.name for option in field.options}
        options = list(field.options)
        for option_name in initiative_options:
            if option_name not in existing:
                options.append(SelectOption(option_name, "GRAY", "Project-specific initiative."))
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
            if field_name == "Initiative":
                raise ProjectUsageError(
                    f"Initiative option '{option_name}' was not found in Project '{project_title}'. "
                    f'Run `basectl gh project configure --project "{project_title}" '
                    f'--initiative-option "{option_name}"` first.'
                )
            raise ProjectUsageError(f"{field_name} option '{option_name}' was not found in Project '{project_title}'.")
        updates.append(FieldUpdate(field.field_id, option.option_id, field_name, option_name))
    return tuple(updates)


def find_option(field: ProjectField, name: str) -> SelectOption | None:
    for option in field.options:
        if option.name == name:
            return option
    return None


def doctor_command(args: ProjectArguments) -> int:
    owner = require_owner(args)
    owner_info = find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        print(f"MISSING Project {args.project_title}")
        return 1
    fields = fetch_project_fields(owner_info.project.project_id)
    findings = compare_schema(fields, schema_for_args(args))
    if not findings:
        print(f"OK      Project {args.project_title}")
        return 0
    for finding in findings:
        print(f"{finding.status.upper():<8}{finding.name}  {finding.message}")
    return 1


def configure_command(args: ProjectArguments) -> int:
    owner = require_owner(args)
    schema = schema_for_args(args)
    owner_info = find_owner_and_project(owner, args.project_title or "")
    project = owner_info.project
    fields: tuple[ProjectField, ...] = ()
    if project is not None:
        fields = fetch_project_fields(project.project_id)
    actions = configuration_plan(project_exists=project is not None, fields=fields, schema=schema)
    errors = [action for action in actions if action.action == "error"]
    if errors:
        for action in errors:
            print(f"ERROR   {action.name}  {action.message}", file=sys.stderr)
        return 1
    if args.dry_run:
        render_dry_run_configure(args, actions)
        return 0
    if project is None:
        project = create_project(owner_info.owner_id, args.project_title or "")
        fields = ()
    by_name = {field.name: field for field in fields}
    for spec in schema.fields:
        field = by_name.get(spec.name)
        if field is None:
            create_single_select_field(project.project_id, spec)
        elif missing_option_names(field, spec):
            update_single_select_field(field, spec)
    print(f"✓ Configured GitHub Project {args.project_title}")
    return 0


def render_dry_run_configure(args: ProjectArguments, actions: tuple[ConfigureAction, ...]) -> None:
    print(
        f"[DRY-RUN] Would configure GitHub Project '{args.project_title}' "
        f"for '{args.repo or args.owner or ''}' with --schema {args.schema}."
    )
    print("[DRY-RUN] Fields: Status, Priority, Area, Size, Initiative")
    if args.initiative_options:
        for option in args.initiative_options:
            print(f"[DRY-RUN] Would ensure Initiative option {option}.")
    for action in actions:
        print(f"[DRY-RUN] Would {action.message}")


def issue_set_fields_command(args: ProjectArguments) -> int:
    owner = require_owner(args)
    repo = require_repo(args)
    owner_info = find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        raise ProjectError(f"Project '{args.project_title}' was not found for owner '{owner}'.")
    project = owner_info.project
    fields = fetch_project_fields(project.project_id)
    updates = resolve_issue_field_updates(fields, args.field_values or {}, project_title=args.project_title or "")
    if not updates:
        raise ProjectUsageError("At least one field option must be provided.")
    repo_owner, repo_name = split_repo(repo)
    issue_id = fetch_issue_id(repo_owner, repo_name, args.issue_number or 0)
    item_id = find_project_item_id(project.project_id, issue_id)
    if args.dry_run:
        print(f"[DRY-RUN] Would add issue #{args.issue_number} to Project '{args.project_title}' if needed.")
        for update in updates:
            print(f"[DRY-RUN] Would set {update.field_name} to {update.option_name}.")
        return 0
    if item_id is None:
        item_id = add_project_item(project.project_id, issue_id)
    for update in updates:
        update_item_field(project.project_id, item_id, update)
    print(f"✓ Updated Project metadata for issue #{args.issue_number}")
    return 0


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
    query = """
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          __typename
          ... on ProjectV2Field { id name dataType }
          ... on ProjectV2SingleSelectField {
            id
            name
            dataType
            options { id name color description }
          }
        }
      }
    }
  }
}
"""
    payload = run_graphql(query, {"id": project_id})
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


def create_project(owner_id: str, title: str) -> ProjectInfo:
    query = """
mutation($ownerId: ID!, $title: String!) {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 { id title }
  }
}
"""
    payload = run_graphql(query, {"ownerId": owner_id, "title": title})
    project = payload["data"]["createProjectV2"]["projectV2"]
    return ProjectInfo(project_id=project["id"], title=project["title"])


def create_single_select_field(project_id: str, spec: SelectFieldSpec) -> None:
    query = """
mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  createProjectV2Field(input: {
    projectId: $projectId,
    dataType: SINGLE_SELECT,
    name: $name,
    singleSelectOptions: $options
  }) {
    projectV2Field { ... on ProjectV2SingleSelectField { id name } }
  }
}
"""
    run_graphql(query, {"projectId": project_id, "name": spec.name, "options": options_payload(spec.options)})


def update_single_select_field(field: ProjectField, spec: SelectFieldSpec) -> None:
    query = """
mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  updateProjectV2Field(input: {
    fieldId: $fieldId,
    singleSelectOptions: $options
  }) {
    projectV2Field { ... on ProjectV2SingleSelectField { id name } }
  }
}
"""
    run_graphql(query, {"fieldId": field.field_id, "options": options_payload(merged_options(field, spec))})


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
    query = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) { id }
  }
}
"""
    payload = run_graphql(query, {"owner": owner, "name": name, "number": number})
    issue = payload["data"]["repository"]["issue"]
    if issue is None:
        raise ProjectError(f"Issue #{number} was not found in {owner}/{name}.")
    return issue["id"]


def find_project_item_id(project_id: str, issue_id: str) -> str | None:
    query = """
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id
          content { ... on Issue { id } }
        }
      }
    }
  }
}
"""
    payload = run_graphql(query, {"projectId": project_id})
    for item in payload["data"]["node"]["items"]["nodes"]:
        if item.get("content", {}).get("id") == issue_id:
            return item["id"]
    return None


def add_project_item(project_id: str, issue_id: str) -> str:
    query = """
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}
"""
    payload = run_graphql(query, {"projectId": project_id, "contentId": issue_id})
    return payload["data"]["addProjectV2ItemById"]["item"]["id"]


def update_item_field(project_id: str, item_id: str, update: FieldUpdate) -> None:
    query = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId,
    itemId: $itemId,
    fieldId: $fieldId,
    value: {singleSelectOptionId: $optionId}
  }) {
    projectV2Item { id }
  }
}
"""
    run_graphql(
        query,
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": update.field_id,
            "optionId": update.option_id,
        },
    )
