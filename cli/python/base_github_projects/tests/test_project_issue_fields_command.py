from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import base_cli
import pytest

from base_github_projects import engine
from base_github_projects import project_issue_fields_command
from base_github_projects.project_operations import ProjectOperations


PROJECT = engine.ProjectInfo(project_id="project-id", title="Base Roadmap")
FIELDS = (
    engine.ProjectField(field_id="status-field", name="Status", data_type="SINGLE_SELECT"),
    engine.ProjectField(field_id="priority-field", name="Priority", data_type="SINGLE_SELECT"),
)
UPDATES = (
    engine.FieldUpdate("status-field", "status-in-progress", "Status", "In Progress"),
    engine.FieldUpdate("priority-field", "priority-p2", "Priority", "P2"),
)


def unexpected(operation: str) -> Callable[..., NoReturn]:
    def fail(*_args: object, **_kwargs: object) -> NoReturn:
        pytest.fail(f"{operation} should not run")

    return fail


def issue_arguments(*, dry_run: bool = False, repo: str = "basefoundry/base") -> engine.ProjectArguments:
    return engine.ProjectArguments(
        area="project",
        command="issue-set-fields",
        project_title="Base Roadmap",
        owner="basefoundry",
        repo=repo,
        issue_number=1604,
        field_values={"status": "In Progress", "priority": "P2"},
        dry_run=dry_run,
    )


def base_operations() -> ProjectOperations:
    def find_project(owner: str, title: str) -> engine.OwnerInfo:
        assert owner == "basefoundry"
        assert title == "Base Roadmap"
        return engine.OwnerInfo(owner_id="owner-id", login=owner, project=PROJECT)

    def fetch_fields(project_id: str) -> tuple[engine.ProjectField, ...]:
        assert project_id == "project-id"
        return FIELDS

    def resolve_updates(
        fields: tuple[engine.ProjectField, ...],
        values: dict[str, str],
        *,
        project_title: str,
    ) -> tuple[engine.FieldUpdate, ...]:
        assert fields == FIELDS
        assert values == {"status": "In Progress", "priority": "P2"}
        assert project_title == "Base Roadmap"
        return UPDATES

    def fetch_issue(owner: str, name: str, number: int) -> str:
        assert (owner, name, number) == ("basefoundry", "base", 1604)
        return "issue-id"

    def find_item(project_id: str, issue_id: str) -> str:
        assert (project_id, issue_id) == ("project-id", "issue-id")
        return "item-id"

    return replace(
        engine.project_operations(),
        require_owner=lambda args: args.owner or pytest.fail("owner is required"),
        require_repo=lambda args: args.repo or pytest.fail("repo is required"),
        find_owner_and_project=find_project,
        fetch_project_fields=fetch_fields,
        issue_field_values_for_args=lambda args: args.field_values or {},
        resolve_issue_field_updates=resolve_updates,
        split_repo=engine.split_repo,
        fetch_issue_id=fetch_issue,
        find_project_item_id=find_item,
        add_project_item=unexpected("add_project_item"),
        update_item_field=unexpected("update_item_field"),
    )


def test_non_numeric_issue_number_exits_usage_before_command_operations(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BASE_CACHE_DIR", str(tmp_path / ".cache" / "base"))
    monkeypatch.setattr(engine, "run_command", unexpected("run_command"))

    status = engine.main(
        [
            "project",
            "issue",
            "set-fields",
            "not-a-number",
            "--project",
            "Base Roadmap",
            "--owner",
            "basefoundry",
            "--repo",
            "basefoundry/base",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ""
    assert "ERROR: Invalid issue number 'not-a-number'." in captured.err


def test_missing_project_is_a_controlled_error_before_field_lookup() -> None:
    ops = replace(
        base_operations(),
        find_owner_and_project=lambda owner, _title: engine.OwnerInfo(
            owner_id="owner-id",
            login=owner,
            project=None,
        ),
        fetch_project_fields=unexpected("fetch_project_fields"),
    )

    with pytest.raises(engine.ProjectError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert str(excinfo.value) == "Project 'Base Roadmap' was not found for owner 'basefoundry'."


def test_missing_field_updates_is_a_usage_error_before_issue_lookup() -> None:
    ops = replace(
        base_operations(),
        issue_field_values_for_args=lambda _args: {},
        resolve_issue_field_updates=lambda _fields, _values, *, project_title: (),
        split_repo=unexpected("split_repo"),
        fetch_issue_id=unexpected("fetch_issue_id"),
    )

    with pytest.raises(engine.ProjectUsageError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert str(excinfo.value) == "At least one field option must be provided."


def test_malformed_repo_is_a_usage_error_before_issue_lookup() -> None:
    ops = replace(base_operations(), fetch_issue_id=unexpected("fetch_issue_id"))

    with pytest.raises(engine.ProjectUsageError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(repo="basefoundry"), ops)

    assert str(excinfo.value) == "Repository must be in owner/name form, got 'basefoundry'."


def test_invalid_field_update_is_a_usage_error_before_issue_lookup() -> None:
    def reject_update(
        _fields: tuple[engine.ProjectField, ...],
        _values: dict[str, str],
        *,
        project_title: str,
    ) -> tuple[engine.FieldUpdate, ...]:
        raise engine.ProjectUsageError(f"Priority option 'P9' was not found in Project '{project_title}'.")

    ops = replace(
        base_operations(),
        resolve_issue_field_updates=reject_update,
        fetch_issue_id=unexpected("fetch_issue_id"),
    )

    with pytest.raises(engine.ProjectUsageError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert str(excinfo.value) == "Priority option 'P9' was not found in Project 'Base Roadmap'."


def test_dry_run_with_missing_item_performs_no_mutations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ops = replace(
        base_operations(),
        find_project_item_id=lambda _project_id, _issue_id: None,
    )

    status = project_issue_fields_command.issue_set_fields_command(issue_arguments(dry_run=True), ops)

    assert status == base_cli.ExitCode.SUCCESS
    assert capsys.readouterr().out.splitlines() == [
        "[DRY-RUN] Would add issue #1604 to Project 'Base Roadmap' if needed.",
        "[DRY-RUN] Would set Status to In Progress.",
        "[DRY-RUN] Would set Priority to P2.",
    ]


def test_existing_item_receives_multiple_updates_in_resolved_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    events: list[tuple[str, ...]] = []

    def find_item(project_id: str, issue_id: str) -> str:
        events.append(("find", project_id, issue_id))
        return "existing-item"

    def update_item(project_id: str, item_id: str, update: engine.FieldUpdate) -> None:
        events.append(("update", project_id, item_id, update.field_name, update.option_name))

    ops = replace(
        base_operations(),
        find_project_item_id=find_item,
        update_item_field=update_item,
    )

    status = project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert status == base_cli.ExitCode.SUCCESS
    assert events == [
        ("find", "project-id", "issue-id"),
        ("update", "project-id", "existing-item", "Status", "In Progress"),
        ("update", "project-id", "existing-item", "Priority", "P2"),
    ]
    assert capsys.readouterr().out == "✓ Updated Project metadata for issue #1604\n"


def test_missing_item_is_added_before_field_updates() -> None:
    events: list[tuple[str, ...]] = []

    def find_item(project_id: str, issue_id: str) -> None:
        events.append(("find", project_id, issue_id))

    def add_item(project_id: str, issue_id: str) -> str:
        events.append(("add", project_id, issue_id))
        return "new-item"

    def update_item(project_id: str, item_id: str, update: engine.FieldUpdate) -> None:
        events.append(("update", project_id, item_id, update.field_name, update.option_name))

    ops = replace(
        base_operations(),
        find_project_item_id=find_item,
        add_project_item=add_item,
        update_item_field=update_item,
    )

    status = project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert status == base_cli.ExitCode.SUCCESS
    assert events == [
        ("find", "project-id", "issue-id"),
        ("add", "project-id", "issue-id"),
        ("update", "project-id", "new-item", "Status", "In Progress"),
        ("update", "project-id", "new-item", "Priority", "P2"),
    ]


def test_issue_lookup_failure_propagates_controlled_error_without_mutation() -> None:
    def fail_issue_lookup(_owner: str, _name: str, number: int) -> str:
        raise engine.ProjectError(f"Issue #{number} was not found in basefoundry/base.")

    ops = replace(base_operations(), fetch_issue_id=fail_issue_lookup)

    with pytest.raises(engine.ProjectError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert str(excinfo.value) == "Issue #1604 was not found in basefoundry/base."


def test_add_item_failure_propagates_controlled_error_before_updates() -> None:
    def fail_add(_project_id: str, _issue_id: str) -> str:
        raise engine.ProjectError("Could not add issue to GitHub Project.")

    ops = replace(
        base_operations(),
        find_project_item_id=lambda _project_id, _issue_id: None,
        add_project_item=fail_add,
    )

    with pytest.raises(engine.ProjectError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert str(excinfo.value) == "Could not add issue to GitHub Project."


def test_partial_field_update_failure_is_deterministic_and_stops_later_updates() -> None:
    events: list[tuple[str, str]] = []
    updates = UPDATES + (engine.FieldUpdate("area-field", "area-ci", "Area", "CI"),)

    def update_item(_project_id: str, _item_id: str, update: engine.FieldUpdate) -> None:
        events.append((update.field_name, update.option_name))
        if update.field_name == "Priority":
            raise engine.ProjectError("Could not update Priority for Project item.")

    ops = replace(
        base_operations(),
        resolve_issue_field_updates=lambda _fields, _values, *, project_title: updates,
        update_item_field=update_item,
    )

    with pytest.raises(engine.ProjectError) as excinfo:
        project_issue_fields_command.issue_set_fields_command(issue_arguments(), ops)

    assert str(excinfo.value) == "Could not update Priority for Project item."
    assert events == [("Status", "In Progress"), ("Priority", "P2")]
