from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from . import graphql_queries as queries


FIELD_COPY_NAMES = ("Status", "Priority", "Area", "Initiative", "Size")


@dataclass(frozen=True)
class ProjectIssueItem:
    item_id: str
    issue_id: str
    issue_number: int
    title: str
    values: dict[str, str]


@dataclass(frozen=True)
class ProjectSelectField:
    field_id: str
    options: dict[str, str]


@dataclass(frozen=True)
class ProjectFieldCopy:
    item_id: str
    issue_number: int
    field_name: str
    option_name: str
    field_id: str
    option_id: str


@dataclass(frozen=True)
class ProjectFieldCopySkip:
    issue_number: int
    field_name: str
    option_name: str
    reason: str


@dataclass(frozen=True)
class ProjectFieldCopyPlan:
    updates: tuple[ProjectFieldCopy, ...]
    skipped: tuple[ProjectFieldCopySkip, ...]


@dataclass(frozen=True)
class FieldCopySummary:
    applied_count: int
    skipped: tuple[ProjectFieldCopySkip, ...]


def plan_missing_field_copies(
    *,
    source_items: dict[str, ProjectIssueItem],
    target_items: dict[str, ProjectIssueItem],
    target_fields: dict[str, ProjectSelectField],
    field_names: tuple[str, ...] = FIELD_COPY_NAMES,
) -> ProjectFieldCopyPlan:
    updates: list[ProjectFieldCopy] = []
    skipped: list[ProjectFieldCopySkip] = []
    for issue_id, target in sorted(target_items.items(), key=lambda item: item[1].issue_number):
        source = source_items.get(issue_id)
        if source is None:
            continue
        for field_name in field_names:
            if target.values.get(field_name):
                continue
            option_name = source.values.get(field_name)
            if not option_name:
                continue
            target_field = target_fields.get(field_name)
            if target_field is None:
                skipped.append(
                    ProjectFieldCopySkip(
                        target.issue_number, field_name, option_name, "target field is missing"
                    )
                )
                continue
            option_id = target_field.options.get(option_name)
            if option_id is None:
                skipped.append(
                    ProjectFieldCopySkip(
                        target.issue_number, field_name, option_name, "target option is missing"
                    )
                )
                continue
            updates.append(
                ProjectFieldCopy(
                    item_id=target.item_id,
                    issue_number=target.issue_number,
                    field_name=field_name,
                    option_name=option_name,
                    field_id=target_field.field_id,
                    option_id=option_id,
                )
            )
    return ProjectFieldCopyPlan(tuple(updates), tuple(skipped))


def copy_missing_project_item_fields(
    *,
    run_graphql: Callable[[str, dict[str, object]], dict[str, object]],
    source_project_id: str,
    target_project_id: str,
    target_fields: Iterable[object],
) -> FieldCopySummary:
    plan = plan_missing_field_copies(
        source_items=fetch_project_issue_items(run_graphql, source_project_id),
        target_items=fetch_project_issue_items(run_graphql, target_project_id),
        target_fields=select_fields_by_name(target_fields),
    )
    for update in plan.updates:
        run_graphql(
            queries.UPDATE_ITEM_FIELD,
            {
                "projectId": target_project_id,
                "itemId": update.item_id,
                "fieldId": update.field_id,
                "optionId": update.option_id,
            },
        )
    return FieldCopySummary(len(plan.updates), plan.skipped)


def select_fields_by_name(fields: Iterable[object]) -> dict[str, ProjectSelectField]:
    selected: dict[str, ProjectSelectField] = {}
    for field in fields:
        if getattr(field, "data_type", "") != "SINGLE_SELECT":
            continue
        options = {
            option.name: option.option_id
            for option in getattr(field, "options", ())
            if option.option_id is not None
        }
        selected[field.name] = ProjectSelectField(field.field_id, options)
    return selected


def fetch_project_issue_items(
    run_graphql: Callable[[str, dict[str, object]], dict[str, object]],
    project_id: str,
) -> dict[str, ProjectIssueItem]:
    items: dict[str, ProjectIssueItem] = {}
    cursor: str | None = None
    while True:
        payload = run_graphql(
            queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_FIELDS,
            {"projectId": project_id, "cursor": cursor},
        )
        node = payload["data"].get("node")
        project_items = node["items"]
        for raw in project_items["nodes"]:
            content = raw.get("content") or {}
            issue_id = content.get("id")
            if not issue_id:
                continue
            items[issue_id] = ProjectIssueItem(
                item_id=raw["id"],
                issue_id=issue_id,
                issue_number=content["number"],
                title=content["title"],
                values=single_select_values(raw),
            )
        if not project_items["pageInfo"]["hasNextPage"]:
            return items
        cursor = project_items["pageInfo"]["endCursor"]


def single_select_values(raw_item: dict[str, object]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_value in raw_item["fieldValues"]["nodes"]:
        if raw_value.get("__typename") != "ProjectV2ItemFieldSingleSelectValue":
            continue
        field = raw_value.get("field") or {}
        field_name = field.get("name")
        if field_name:
            values[field_name] = raw_value["name"]
    return values
