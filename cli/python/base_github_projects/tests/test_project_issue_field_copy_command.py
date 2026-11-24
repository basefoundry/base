from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import base_cli
import pytest

from base_github_projects import engine, graphql_queries, project_issue_field_copy_command as copy_command


PROJECT = engine.ProjectInfo(project_id="P1", title="base", project_number=10, owner_login="basefoundry")
FIELDS = (
    engine.ProjectField("legacy-priority", "Legacy priority", "SINGLE_SELECT", tuple(
        engine.SelectOption(name, "BLUE", "", f"p-{name}") for name in ("P0", "P1", "P2", "P3")
    )),
    engine.ProjectField("legacy-size", "Legacy size", "SINGLE_SELECT", tuple(
        engine.SelectOption(name, "BLUE", "", f"s-{name}") for name in ("T", "S", "M", "L")
    )),
)


def project_item(*, issue_values: dict[str, str] | None = None, project_values: dict[str, str] | None = None):
    return engine.ProjectIssueData(
        item_id="item-1",
        issue_id="issue-1",
        repository="basefoundry/base",
        number=42,
        title="test issue",
        project_values=project_values or {},
        issue_values=issue_values or {},
    )


def copy_ops(items: list[engine.ProjectIssueData], events: list[tuple], *, mismatches: set[tuple] | None = None):
    mismatches = mismatches or set()

    def fetch_items(_project_id: str):
        return tuple(items)

    def write_issue(owner: str, repo: str, number: int, values: dict[str, str], **kwargs: object):
        events.append(("issue", owner, kwargs.get("repository_owner"), repo, number, dict(values)))
        item = items[0]
        item.issue_values.update(values)
        for field, actual in mismatches:
            if field in values:
                item.issue_values[field] = actual

    def update_item(_project_id: str, item_id: str, update: engine.FieldUpdate):
        events.append(("project", item_id, update.field_name, update.option_name))
        item = items[0]
        item.project_values[update.field_name] = update.option_name
        for field, actual in mismatches:
            if field == update.field_name:
                item.project_values[field] = actual

    return replace(
        engine.project_operations(),
        require_owner=lambda _args: "basefoundry",
        find_owner_and_project=lambda _owner, _title: engine.OwnerInfo("org-1", "basefoundry", PROJECT),
        fetch_project_issue_items=fetch_items,
        fetch_project_fields=lambda _project_id: FIELDS,
        organization_issue_field_ids=lambda _owner: {"Priority": 10, "Effort": 20},
        write_issue_field_values=write_issue,
        update_item_field=update_item,
    )


def args(direction: str, *, write: bool = False, export_path: Path | None = None) -> engine.ProjectArguments:
    return engine.ProjectArguments(
        area="project",
        command="issue-copy-fields",
        project_title="base",
        owner="basefoundry",
        copy_direction=direction,
        write=write,
        export_path=str(export_path) if export_path else None,
    )


def test_fetch_project_issue_items_uses_issue_field_query(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {
        "data": {
            "node": {
                "items": {
                    "nodes": [
                        {
                            "id": "item-1",
                            "content": {
                                "id": "issue-1",
                                "number": 42,
                                "title": "test issue",
                                "repository": {"nameWithOwner": "basefoundry/base"},
                                "issueFieldValues": {
                                    "nodes": [
                                        {
                                            "__typename": "IssueFieldSingleSelectValue",
                                            "name": "High",
                                            "field": {"name": "Priority"},
                                        },
                                        {
                                            "__typename": "IssueFieldDateValue",
                                            "value": "2026-11-24",
                                            "field": {"name": "Start date"},
                                        },
                                    ]
                                },
                            },
                            "fieldValues": {
                                "nodes": [
                                    {
                                        "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                        "name": "P1",
                                        "field": {"name": "Legacy priority"},
                                    }
                                ]
                            },
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run(query: str, variables: dict[str, object]) -> dict[str, object]:
        calls.append((query, variables))
        return response

    monkeypatch.setattr(engine, "run_graphql", fake_run)

    items = engine.fetch_project_issue_items("project-1")

    assert calls == [
        (
            graphql_queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_ISSUE_FIELDS,
            {"projectId": "project-1", "cursor": None},
        )
    ]
    assert items == (
        engine.ProjectIssueData(
            item_id="item-1",
            issue_id="issue-1",
            repository="basefoundry/base",
            number=42,
            title="test issue",
            project_values={"Legacy priority": "P1"},
            issue_values={"Priority": "High", "Start date": "2026-11-24"},
        ),
    )


def test_project_to_issue_copy_is_dry_run_by_default_and_only_plans_differences(capsys):
    items = [
        project_item(project_values={"Legacy priority": "P1", "Legacy size": "S"}, issue_values={"Priority": "High"}),
        engine.ProjectIssueData("item-2", "issue-2", "basefoundry/base", 43, "already current",
            {"Legacy priority": "P2", "Legacy size": "M"}, {"Priority": "Medium", "Effort": "Medium"}),
    ]
    events: list[tuple] = []
    status = copy_command.copy_issue_fields_command(args("project-to-issue"), copy_ops(items, events))

    output = capsys.readouterr().out
    assert status == base_cli.ExitCode.SUCCESS
    assert events == []
    assert "Mode: dry run" in output
    assert "Values to change: 1" in output
    assert "Readback mismatches: not checked (dry run)" in output
    assert "Priority: High=1, Medium=1" in output
    assert "Effort: Medium=1, Small=1" in output


def test_project_to_issue_write_exports_before_state_and_reads_back(tmp_path: Path, capsys):
    export_path = tmp_path / "migration" / "before.json"
    items = [project_item(project_values={"Legacy priority": "P1", "Legacy size": "S"})]
    events: list[tuple] = []
    status = copy_command.copy_issue_fields_command(
        args("project-to-issue", write=True, export_path=export_path), copy_ops(items, events)
    )

    output = capsys.readouterr().out
    snapshot = json.loads(export_path.read_text(encoding="utf-8"))
    assert status == base_cli.ExitCode.SUCCESS
    assert snapshot["items"][0]["issue_values"] == {}
    assert events == [("issue", "basefoundry", "basefoundry", "base", 42, {"Priority": "High", "Effort": "Small"})]
    assert "Priority: High=1" in output
    assert "Effort: Small=1" in output
    assert "Readback mismatches: 0" in output


def test_project_to_issue_write_refuses_to_overwrite_export(tmp_path: Path):
    export_path = tmp_path / "before.json"
    export_path.write_text("keep", encoding="utf-8")
    items = [project_item(project_values={"Legacy priority": "P1"})]

    with pytest.raises(engine.ProjectUsageError, match="Could not write before-state export"):
        copy_command.copy_issue_fields_command(
            args("project-to-issue", write=True, export_path=export_path), copy_ops(items, [])
        )
    assert export_path.read_text(encoding="utf-8") == "keep"


def test_project_to_issue_rerun_skips_values_that_already_match(tmp_path: Path, capsys):
    export_path = tmp_path / "before.json"
    items = [project_item(
        project_values={"Legacy priority": "P1", "Legacy size": "S"},
        issue_values={"Priority": "High", "Effort": "Small"},
    )]
    events: list[tuple] = []

    status = copy_command.copy_issue_fields_command(
        args("project-to-issue", write=True, export_path=export_path), copy_ops(items, events)
    )

    assert status == base_cli.ExitCode.SUCCESS
    assert events == []
    assert "Values to change: 0" in capsys.readouterr().out


def test_issue_to_project_copy_writes_only_differences_and_verifies(tmp_path: Path, capsys):
    export_path = tmp_path / "before.json"
    items = [project_item(issue_values={"Priority": "Urgent", "Effort": "Tiny"})]
    events: list[tuple] = []
    status = copy_command.copy_issue_fields_command(
        args("issue-to-project", write=True, export_path=export_path), copy_ops(items, events)
    )

    output = capsys.readouterr().out
    assert status == base_cli.ExitCode.SUCCESS
    assert events == [("project", "item-1", "Legacy priority", "P0"), ("project", "item-1", "Legacy size", "T")]
    assert json.loads(export_path.read_text(encoding="utf-8"))["items"][0]["project_values"] == {}
    assert "Legacy priority: P0=1" in output
    assert "Legacy size: T=1" in output
    assert "Readback mismatches: 0" in output


def test_issue_to_project_copy_defaults_to_dry_run(capsys):
    items = [project_item(issue_values={"Priority": "Urgent", "Effort": "Tiny"})]
    events: list[tuple] = []

    status = copy_command.copy_issue_fields_command(args("issue-to-project"), copy_ops(items, events))

    output = capsys.readouterr().out
    assert status == base_cli.ExitCode.SUCCESS
    assert events == []
    assert "Mode: dry run" in output
    assert "Legacy priority: P0=1" in output
    assert "Legacy size: T=1" in output
    assert "Readback mismatches: not checked (dry run)" in output


def test_issue_to_project_rerun_skips_already_matching_values(tmp_path: Path, capsys):
    export_path = tmp_path / "before.json"
    items = [project_item(
        issue_values={"Priority": "Low", "Effort": "Large"},
        project_values={"Legacy priority": "P3", "Legacy size": "L"},
    )]
    events: list[tuple] = []
    status = copy_command.copy_issue_fields_command(
        args("issue-to-project", write=True, export_path=export_path), copy_ops(items, events)
    )

    assert status == base_cli.ExitCode.SUCCESS
    assert events == []
    assert "Values to change: 0" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("project_values", "field"),
    [
        ({"Legacy priority": "Tiny"}, "Priority"),
        ({"Legacy size": "High"}, "Effort"),
    ],
)
def test_project_to_issue_rejects_option_from_the_other_field(
    project_values: dict[str, str], field: str,
) -> None:
    item = project_item(project_values=project_values)

    with pytest.raises(engine.ProjectUsageError, match=f"unmapped {field} value"):
        copy_command.copy_issue_fields_command(args("project-to-issue"), copy_ops([item], []))

