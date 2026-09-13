from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import base_cli

from base_projects.command_helpers import ProjectUsageError

from .project_errors import ProjectAuthError
from .project_errors import ProjectDuplicateItemError
from .project_errors import ProjectError
from .project_errors import ProjectTransportError
from .project_model import FieldUpdate
from .project_model import OwnerInfo
from .project_model import ProjectArguments
from .project_model import ProjectField
from .project_model import ProjectInfo
from .project_model import SelectOption


GITHUB_REST_TIMEOUT_SECONDS = 60
REST_MANAGED_FIELDS = ("Status", "Priority", "Area", "Initiative", "Size")


@dataclass(frozen=True)
class RestIssueFieldRequest:
    owner: str
    repo_owner: str
    repo_name: str
    issue_number: int
    project_title: str
    field_values: dict[str, str]
    resolve_updates: Callable[[tuple[ProjectField, ...], dict[str, str]], tuple[FieldUpdate, ...]]
    dry_run: bool
    allow_cross_repo: bool


@dataclass(frozen=True)
class RestItemLookup:
    project: ProjectInfo
    issue_id: str
    repo: str
    issue_title: str
    field_ids: tuple[str, ...]
    item_id: str | None = None


def run_rest(
    path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
) -> Any:
    command = ["gh", "api"]
    if method != "GET":
        command.extend(["--method", method])
    command.append(path)
    input_payload = None
    if payload is not None:
        command.extend(["--input", "-"])
        input_payload = json.dumps(payload)
    try:
        result = subprocess.run(
            command,
            input=input_payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=GITHUB_REST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        timeout = exc.timeout if exc.timeout is not None else GITHUB_REST_TIMEOUT_SECONDS
        raise ProjectTransportError(f"Timed out running GitHub REST request after {timeout} seconds.") from exc
    except OSError as exc:
        raise ProjectTransportError(f"Could not run GitHub REST request: {exc}") from exc

    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        if is_project_auth_error(message):
            raise ProjectAuthError(message or "GitHub Project REST access requires authentication.")
        if is_project_transport_error(message):
            raise ProjectTransportError(message or "GitHub Project REST transport failed.")
        if "content already exists in this project" in message.lower():
            raise ProjectDuplicateItemError(message)
        raise ProjectError(message or "GitHub REST request failed.")

    output = result.stdout.strip()
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise ProjectError("GitHub REST returned invalid JSON.") from exc


def is_project_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in (
            "bad credentials",
            "401 unauthorized",
            "requires authentication",
            "resource not accessible",
            "project scope",
            "403 forbidden",
        )
    )


def is_project_transport_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in (
            "rate limit",
            "secondary rate limit",
            "abuse detection",
            "retry-after",
            "x-ratelimit-reset",
            "could not resolve host",
            "connection reset",
            "connection refused",
            "timed out",
            "timeout",
            "502 bad gateway",
            "503 service unavailable",
            "504 gateway timeout",
            "http 5",
        )
    )


class RestProjectTransport:
    """Small REST adapter for Project discovery and exact issue-item updates."""

    def __init__(
        self,
        *,
        run: Callable[..., Any] = run_rest,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._run = run
        self._sleep = sleep

    def find_owner_and_project(self, owner: str, title: str) -> OwnerInfo:
        owner_payload = self._run(f"users/{owner}")
        owner_type = str(owner_payload.get("type", ""))
        if owner_type not in {"Organization", "User"}:
            raise ProjectError(f"REST Project owner '{owner}' has unsupported type '{owner_type}'.")
        projects = self._run(f"{self._owner_prefix(owner, owner_type)}/projectsV2?per_page=100")
        project_nodes = _list_payload(projects, "projects")
        project = next((node for node in project_nodes if node.get("title") == title), None)
        if project is None:
            return OwnerInfo(
                owner_id=str(owner_payload.get("id", owner)),
                login=owner,
                project=None,
            )
        number = _project_number(project)
        return OwnerInfo(
            owner_id=str(owner_payload.get("id", owner)),
            login=owner,
            project=ProjectInfo(
                project_id=str(project.get("id", "")),
                title=str(project.get("title", title)),
                project_number=number,
                owner_login=owner,
                owner_type=owner_type,
            ),
        )

    def fetch_project_fields(self, project: ProjectInfo) -> tuple[ProjectField, ...]:
        path = self._project_path(project, "fields?per_page=100")
        fields = self._run(path)
        return tuple(_parse_project_field(raw) for raw in _list_payload(fields, "fields"))

    def fetch_issue(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        issue = self._run(f"repos/{owner}/{repo}/issues/{number}")
        if not isinstance(issue, dict) or not issue.get("id"):
            raise ProjectError(f"Issue #{number} was not found in {owner}/{repo}.")
        return issue

    def find_project_item(self, lookup: RestItemLookup) -> dict[str, Any] | None:
        fields_query = ",".join(lookup.field_ids)
        for attempt in range(1, 4):
            if lookup.item_id is not None:
                try:
                    item = self._run(
                        self._project_path(lookup.project, f"items/{lookup.item_id}?fields={fields_query}")
                    )
                except ProjectError as exc:
                    if "404" not in str(exc):
                        raise
                    item = {}
                if _item_matches(item, lookup.issue_id, lookup.item_id):
                    return item

            query = urlencode(
                {
                    "per_page": "100",
                    "q": f'repo:{lookup.repo} is:issue title:"{lookup.issue_title}"',
                    "fields": fields_query,
                }
            )
            items = self._run(self._project_path(lookup.project, f"items?{query}"))
            for item in _list_payload(items, "items"):
                if _item_matches(item, lookup.issue_id, lookup.item_id):
                    return item
            if attempt < 3:
                self._sleep(float(attempt))
        return None

    def add_project_item(self, project: ProjectInfo, issue_id: str) -> str:
        raw_id: object = int(issue_id) if issue_id.isdigit() else issue_id
        response = self._run(
            self._project_path(project, "items"),
            method="POST",
            payload={"type": "Issue", "id": raw_id},
        )
        item_id = _nested_value(response, "id")
        if item_id is None:
            raise ProjectError("REST Project item add did not return an item id.")
        return str(item_id)

    def update_project_item(self, project: ProjectInfo, item_id: str, updates: tuple[FieldUpdate, ...]) -> None:
        fields = [
            {
                "id": int(update.field_id) if update.field_id.isdigit() else update.field_id,
                "value": update.option_id,
            }
            for update in updates
        ]
        self._run(
            self._project_path(project, f"items/{item_id}"),
            method="PATCH",
            payload={"fields": fields},
        )

    def reconcile_issue_fields(self, request: RestIssueFieldRequest) -> int:
        owner_info = self.find_owner_and_project(request.owner, request.project_title)
        if owner_info.project is None:
            raise ProjectError(
                f"Project '{request.project_title}' was not found for owner '{request.owner}'."
            )
        project = owner_info.project
        if not request.allow_cross_repo and request.repo_owner.casefold() != request.owner.casefold():
            raise ProjectUsageError(
                f"Project '{request.project_title}' could not verify repository ownership for "
                f"'{request.repo_owner}/{request.repo_name}' "
                "during REST recovery. The REST fallback only permits same-owner repositories; "
                "pass --allow-cross-repo intentionally."
            )
        if request.allow_cross_repo and request.repo_owner.casefold() != request.owner.casefold():
            print(
                f"WARNING: Updating Project '{request.project_title}' with issue repository "
                f"'{request.repo_owner}/{request.repo_name}' "
                "through REST recovery because --allow-cross-repo was supplied.",
                file=sys.stderr,
            )

        fields = self.fetch_project_fields(project)
        updates = request.resolve_updates(fields, request.field_values)
        if not updates:
            raise ProjectUsageError("At least one field option must be provided.")
        issue = self.fetch_issue(request.repo_owner, request.repo_name, request.issue_number)
        if request.dry_run:
            print(
                f"[DRY-RUN] Would add issue #{request.issue_number} to Project "
                f"'{request.project_title}' if needed."
            )
            for update in updates:
                print(f"[DRY-RUN] Would set {update.field_name} to {update.option_name}.")
            return base_cli.ExitCode.SUCCESS

        field_ids = tuple(field.field_id for field in fields if field.name in REST_MANAGED_FIELDS)
        lookup = RestItemLookup(
            project=project,
            issue_id=str(issue["id"]),
            repo=f"{request.repo_owner}/{request.repo_name}",
            issue_title=str(issue.get("title", "")),
            field_ids=field_ids,
        )
        item = self.find_project_item(lookup)
        if item is None:
            try:
                item_id = self.add_project_item(project, str(issue["id"]))
            except ProjectDuplicateItemError:
                item_id = ""
            item = self.find_project_item(
                RestItemLookup(
                    project=project,
                    issue_id=str(issue["id"]),
                    repo=f"{request.repo_owner}/{request.repo_name}",
                    issue_title=str(issue.get("title", "")),
                    field_ids=field_ids,
                    item_id=item_id or None,
                )
            )
        if item is None:
            raise ProjectError(
                f"REST Project item for issue #{request.issue_number} was not visible "
                "after bounded recovery attempts."
            )
        item_id = str(item.get("id", ""))
        if not item_id:
            raise ProjectError("REST Project item did not return an item id.")

        current_values = _item_field_values(item)
        pending = tuple(update for update in updates if current_values.get(update.field_name) != update.option_name)
        if pending:
            self.update_project_item(project, item_id, pending)
        verified = self.find_project_item(
            RestItemLookup(
                project=project,
                issue_id=str(issue["id"]),
                repo=f"{request.repo_owner}/{request.repo_name}",
                issue_title=str(issue.get("title", "")),
                field_ids=field_ids,
                item_id=item_id,
            )
        )
        if verified is None or any(
            _item_field_values(verified).get(update.field_name) != update.option_name for update in updates
        ):
            raise ProjectError("REST Project field validation failed after the update.")
        print(f"✓ Updated Project metadata for issue #{request.issue_number} (REST fallback)")
        return base_cli.ExitCode.SUCCESS

    @staticmethod
    def _owner_prefix(owner: str, owner_type: str) -> str:
        return f"{'orgs' if owner_type == 'Organization' else 'users'}/{owner}"

    def _project_path(self, project: ProjectInfo, suffix: str) -> str:
        if project.project_number is None or not project.owner_login or not project.owner_type:
            raise ProjectError("REST Project metadata is missing its owner or project number.")
        return (
            f"{self._owner_prefix(project.owner_login, project.owner_type)}"
            f"/projectsV2/{project.project_number}/{suffix}"
        )


def rest_doctor_command(
    args: ProjectArguments,
    *,
    transport: RestProjectTransport,
    compare_schema: Callable[[tuple[ProjectField, ...], Any], tuple[Any, ...]],
    schema_for_args: Callable[[ProjectArguments], Any],
) -> int:
    owner = args.owner
    if not owner:
        raise ProjectUsageError("Project owner is required for REST Project recovery.")
    owner_info = transport.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        print(f"MISSING Project {args.project_title}")
        return base_cli.ExitCode.FAILURE
    fields = transport.fetch_project_fields(owner_info.project)
    findings = compare_schema(fields, schema_for_args(args))
    if not findings:
        print(f"OK      Project {args.project_title} (REST fallback)")
        return base_cli.ExitCode.SUCCESS
    for finding in findings:
        print(f"{finding.status.upper():<8}{finding.name}  {finding.message}")
    return base_cli.ExitCode.FAILURE


def _list_payload(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return [item for item in payload[key] if isinstance(item, dict)]
    raise ProjectError(f"GitHub REST response did not contain a '{key}' list.")


def _project_number(project: Mapping[str, object]) -> int:
    try:
        return int(project["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectError("GitHub REST Project response did not contain a valid project number.") from exc


def _parse_project_field(raw: Mapping[str, Any]) -> ProjectField:
    raw_options = raw.get("options")
    options: list[SelectOption] = []
    if isinstance(raw_options, list):
        for option in raw_options:
            if not isinstance(option, dict) or option.get("id") is None:
                continue
            name = option.get("name", "")
            if isinstance(name, dict):
                name = name.get("raw", "")
            options.append(
                SelectOption(
                    name=str(name),
                    color=str(option.get("color", "")),
                    description=_nested_text(option.get("description", "")),
                    option_id=str(option["id"]),
                )
            )
    data_type = str(raw.get("data_type", raw.get("dataType", "SINGLE_SELECT" if raw_options is not None else "")))
    return ProjectField(str(raw.get("id", "")), str(raw.get("name", "")), data_type.upper(), tuple(options))


def _nested_text(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("raw", value.get("html", "")))
    return str(value)


def _nested_value(payload: Any, key: str) -> object | None:
    if isinstance(payload, dict):
        if payload.get(key) is not None:
            return payload[key]
        nested = payload.get("value")
        if isinstance(nested, dict) and nested.get(key) is not None:
            return nested[key]
    return None


def _item_matches(item: Any, issue_id: str, item_id: str | None) -> bool:
    if not isinstance(item, dict) or (item_id is not None and str(item.get("id", "")) != item_id):
        return False
    content = item.get("content")
    return isinstance(content, dict) and str(content.get("id", "")) == issue_id


def _item_field_values(item: Mapping[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    raw_fields = item.get("fields", [])
    if not isinstance(raw_fields, list):
        return values
    for field in raw_fields:
        if not isinstance(field, dict):
            continue
        value = field.get("value")
        if isinstance(value, dict):
            name = value.get("name", "")
            if isinstance(name, dict):
                name = name.get("raw", "")
        else:
            name = value or ""
        values[str(field.get("name", ""))] = str(name)
    return values
