from __future__ import annotations

from collections.abc import Iterator

from base_github_projects import graphql_queries as queries
from base_github_projects import project_item_fields
from base_github_projects.project_model import ProjectField, SelectOption


def issue_item(
    item_id: str,
    issue_id: str | None,
    number: int,
    values: list[dict[str, object]],
) -> dict[str, object]:
    content = None if issue_id is None else {"id": issue_id, "number": number, "title": f"Issue {number}"}
    return {"id": item_id, "content": content, "fieldValues": {"nodes": values}}


def page(nodes: list[dict[str, object]], *, next_cursor: str | None = None) -> dict[str, object]:
    return {
        "data": {
            "node": {
                "items": {
                    "nodes": nodes,
                    "pageInfo": {
                        "hasNextPage": next_cursor is not None,
                        "endCursor": next_cursor,
                    },
                }
            }
        }
    }


def select_value(field_name: str, option_name: str) -> dict[str, object]:
    return {
        "__typename": "ProjectV2ItemFieldSingleSelectValue",
        "name": option_name,
        "field": {"name": field_name},
    }


def test_copy_missing_project_item_fields_paginates_and_updates_only_missing_values() -> None:
    responses: Iterator[dict[str, object]] = iter(
        [
            page([issue_item("source-1", "issue-1", 1, [select_value("Status", "Ready")])], next_cursor="source-2"),
            page(
                [
                    issue_item("source-2", "issue-2", 2, [select_value("Status", "Ready")]),
                    issue_item("draft", None, 0, []),
                ]
            ),
            page(
                [
                    issue_item("target-1", "issue-1", 1, []),
                    issue_item("target-2", "issue-2", 2, [select_value("Status", "Done")]),
                ]
            ),
            {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "target-1"}}}},
        ]
    )
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run(query: str, variables: dict[str, object]) -> dict[str, object]:
        calls.append((query, variables))
        return next(responses)

    fields = (
        ProjectField(
            "status-field",
            "Status",
            "SINGLE_SELECT",
            (
                SelectOption("Ready", "GREEN", "", "ready-option"),
                SelectOption("No ID", "GRAY", ""),
            ),
        ),
        ProjectField("title-field", "Title", "TITLE"),
    )

    summary = project_item_fields.copy_missing_project_item_fields(
        run_graphql=fake_run,
        source_project_id="source-project",
        target_project_id="target-project",
        target_fields=fields,
    )

    assert summary == project_item_fields.FieldCopySummary(1, ())
    assert calls == [
        (
            queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_FIELDS,
            {"projectId": "source-project", "cursor": None},
        ),
        (
            queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_FIELDS,
            {"projectId": "source-project", "cursor": "source-2"},
        ),
        (
            queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_FIELDS,
            {"projectId": "target-project", "cursor": None},
        ),
        (
            queries.UPDATE_ITEM_FIELD,
            {
                "projectId": "target-project",
                "itemId": "target-1",
                "fieldId": "status-field",
                "optionId": "ready-option",
            },
        ),
    ]


def test_apply_missing_project_item_defaults_updates_supported_values_and_reports_skips() -> None:
    responses: Iterator[dict[str, object]] = iter(
        [
            page([issue_item("target-7", "issue-7", 7, [])]),
            {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "target-7"}}}},
        ]
    )
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run(query: str, variables: dict[str, object]) -> dict[str, object]:
        calls.append((query, variables))
        return next(responses)

    fields = (
        ProjectField(
            "priority-field",
            "Priority",
            "SINGLE_SELECT",
            (SelectOption("P2", "YELLOW", "", "p2-option"),),
        ),
        ProjectField("area-field", "Area", "SINGLE_SELECT", ()),
    )

    summary = project_item_fields.apply_missing_project_item_defaults(
        run_graphql=fake_run,
        target_project_id="target-project",
        target_fields=fields,
        field_defaults={"Priority": "P2", "Size": "S", "Area": "Workspace"},
    )

    assert summary.applied_count == 1
    assert summary.skipped == (
        project_item_fields.ProjectFieldCopySkip(7, "Size", "S", "target field is missing"),
        project_item_fields.ProjectFieldCopySkip(7, "Area", "Workspace", "target option is missing"),
    )
    assert calls[-1] == (
        queries.UPDATE_ITEM_FIELD,
        {
            "projectId": "target-project",
            "itemId": "target-7",
            "fieldId": "priority-field",
            "optionId": "p2-option",
        },
    )


def test_copy_planner_preserves_existing_values_and_ignores_missing_source_items() -> None:
    source = project_item_fields.ProjectIssueItem(
        item_id="source-item",
        issue_id="issue-present",
        issue_number=1,
        title="Present source",
        values={"Status": "Ready", "Area": "Workspace"},
    )
    targets = {
        "issue-present": project_item_fields.ProjectIssueItem(
            item_id="target-present",
            issue_id="issue-present",
            issue_number=1,
            title="Present target",
            values={"Status": "Done"},
        ),
        "issue-without-source": project_item_fields.ProjectIssueItem(
            item_id="target-without-source",
            issue_id="issue-without-source",
            issue_number=2,
            title="No matching source",
            values={},
        ),
    }

    plan = project_item_fields.plan_missing_field_copies(
        source_items={"issue-present": source},
        target_items=targets,
        target_fields={
            "Status": project_item_fields.ProjectSelectField("status-field", {"Ready": "ready-id"}),
            "Area": project_item_fields.ProjectSelectField("area-field", {}),
        },
        field_names=("Status", "Area"),
    )

    assert not plan.updates
    assert plan.skipped == (
        project_item_fields.ProjectFieldCopySkip(
            1, "Area", "Workspace", "target option is missing"
        ),
    )


def test_single_select_values_ignores_other_value_types_and_unnamed_fields() -> None:
    raw_item = issue_item(
        "item",
        "issue",
        1,
        [
            select_value("Status", "Ready"),
            {"__typename": "ProjectV2ItemFieldTextValue", "text": "notes"},
            {
                "__typename": "ProjectV2ItemFieldSingleSelectValue",
                "name": "P2",
                "field": None,
            },
        ],
    )

    assert project_item_fields.single_select_values(raw_item) == {"Status": "Ready"}
