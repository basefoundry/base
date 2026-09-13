from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from base_github_projects import engine
from base_github_projects import project_rest
from base_github_projects.project_errors import ProjectAuthError
from base_github_projects.project_errors import ProjectDuplicateItemError
from base_github_projects.project_errors import ProjectTransportError
from base_github_projects.project_model import FieldUpdate
from base_github_projects.project_model import ProjectArguments


FIXTURE_PATH = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "project-transport.json"


def fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_engine_routes_classified_graphql_failure_to_rest_issue_recovery(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[project_rest.RestIssueFieldRequest] = []

    def fail_transport(_owner: str, _title: str) -> engine.OwnerInfo:
        raise ProjectTransportError("API rate limit already exceeded")

    class FakeRestTransport:
        def reconcile_issue_fields(self, request: project_rest.RestIssueFieldRequest) -> int:
            calls.append(request)
            return 0

    monkeypatch.setattr(engine, "RestProjectTransport", FakeRestTransport)
    args = ProjectArguments(
        area="project",
        command="issue-set-fields",
        project_title="base",
        owner="basefoundry",
        repo="basefoundry/base",
        issue_number=1311,
        field_values={"status": "Backlog"},
    )
    ops = replace(engine.project_operations(), find_owner_and_project=fail_transport)
    monkeypatch.setattr(engine, "project_operations", lambda: ops)

    assert engine.issue_set_fields_command(args) == 0
    assert calls[0].project_title == "base"
    assert "using REST Projects API" in capsys.readouterr().err


def test_rest_transport_reads_the_shared_project_contract_fixture() -> None:
    payload = fixture()

    def run(path: str, **_kwargs: object) -> object:
        if path == "users/basefoundry":
            return payload["owner"]
        if path == "orgs/basefoundry/projectsV2?per_page=100":
            return payload["projects"]
        if path.endswith("projectsV2/1/fields?per_page=100"):
            return payload["fields"]
        raise AssertionError(f"unexpected REST path: {path}")

    transport = project_rest.RestProjectTransport(run=run, sleep=lambda _seconds: None)
    owner = transport.find_owner_and_project("basefoundry", "base")

    assert owner.project is not None
    assert owner.project.project_number == 1
    assert owner.project.owner_type == "Organization"
    assert [field.name for field in transport.fetch_project_fields(owner.project)] == [
        "Status",
        "Priority",
        "Size",
        "Area",
        "Initiative",
    ]


def test_run_rest_keeps_auth_transport_and_duplicate_failures_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = [
        ("Bad credentials", ProjectAuthError),
        ("API rate limit exceeded", ProjectTransportError),
        ("Content already exists in this project (HTTP 422)", ProjectDuplicateItemError),
    ]
    for message, error_type in cases:
        completed = project_rest.subprocess.CompletedProcess(
            ["gh"], 1, stdout="", stderr=message
        )
        monkeypatch.setattr(
            project_rest.subprocess,
            "run",
            lambda *args, _completed=completed, **kwargs: _completed,
        )
        with pytest.raises(error_type, match=message.split(" ", maxsplit=1)[0]):
            project_rest.run_rest("users/basefoundry")


def test_run_rest_passes_json_patch_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = project_rest.subprocess.CompletedProcess(
        ["gh"], 0, stdout="{}", stderr=""
    )
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> project_rest.subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return completed

    monkeypatch.setattr(project_rest.subprocess, "run", fake_run)

    assert project_rest.run_rest(
        "orgs/basefoundry/projectsV2/1/items/101",
        method="PATCH",
        payload={"fields": [{"id": 10, "value": "O_backlog"}]},
    ) == {}
    assert calls[0][0] == [
        "gh",
        "api",
        "--method",
        "PATCH",
        "orgs/basefoundry/projectsV2/1/items/101",
        "--input",
        "-",
    ]
    assert calls[0][1]["timeout"] == project_rest.GITHUB_REST_TIMEOUT_SECONDS
    assert json.loads(str(calls[0][1]["input"])) == {
        "fields": [{"id": 10, "value": "O_backlog"}]
    }


def test_rest_reconcile_recovers_duplicate_add_and_reads_back_fields(  # pylint: disable=too-many-return-statements
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = fixture()
    item = copy.deepcopy(payload["item"])
    calls: list[tuple[str, str, object]] = []
    search_count = 0

    def run(path: str, *, method: str = "GET", payload: object = None) -> object:
        nonlocal search_count
        calls.append((method, path, payload))
        if path == "users/basefoundry":
            return payload_fixture["owner"]
        if path == "orgs/basefoundry/projectsV2?per_page=100":
            return payload_fixture["projects"]
        if path.endswith("projectsV2/1/fields?per_page=100"):
            return payload_fixture["fields"]
        if path == "repos/basefoundry/base/issues/1311":
            return payload_fixture["issue"]
        if "projectsV2/1/items?" in path:
            search_count += 1
            return [] if search_count <= 3 else [item]
        if path.endswith("projectsV2/1/items") and method == "POST":
            raise ProjectDuplicateItemError("Content already exists in this project (HTTP 422)")
        if "projectsV2/1/items/101?fields=" in path and method == "GET":
            return item
        if path.endswith("projectsV2/1/items/101") and method == "PATCH":
            assert isinstance(payload, dict)
            for field in payload["fields"]:
                for current in item["fields"]:
                    if current["id"] == field["id"]:
                        current["value"]["name"]["raw"] = {10: "Backlog", 11: "P2"}[field["id"]]
            return item
        raise AssertionError(f"unexpected REST call: {method} {path}")

    payload_fixture = payload
    transport = project_rest.RestProjectTransport(run=run, sleep=lambda _seconds: None)
    updates = (
        FieldUpdate("10", "O_backlog", "Status", "Backlog"),
        FieldUpdate("11", "O_p2", "Priority", "P2"),
    )

    status = transport.reconcile_issue_fields(
        project_rest.RestIssueFieldRequest(
            owner="basefoundry",
            repo_owner="basefoundry",
            repo_name="base",
            issue_number=1311,
            project_title="base",
            field_values={"status": "Backlog", "priority": "P2"},
            resolve_updates=lambda _fields, _values: updates,
            dry_run=False,
            allow_cross_repo=False,
        )
    )

    assert status == 0
    assert sum(method == "POST" for method, _path, _payload in calls) == 1
    patch_calls = [call for call in calls if call[0] == "PATCH"]
    assert len(patch_calls) == 1
    assert patch_calls[0][2] == {
        "fields": [{"id": 10, "value": "O_backlog"}, {"id": 11, "value": "O_p2"}]
    }
    assert "REST fallback" in capsys.readouterr().out


def test_rest_recovery_rejects_cross_owner_repository_without_explicit_consent() -> None:
    payload = fixture()

    def run(path: str, **_kwargs: object) -> object:
        if path == "users/basefoundry":
            return payload["owner"]
        if path == "orgs/basefoundry/projectsV2?per_page=100":
            return payload["projects"]
        raise AssertionError(f"unexpected REST path: {path}")

    transport = project_rest.RestProjectTransport(run=run, sleep=lambda _seconds: None)
    with pytest.raises(project_rest.ProjectUsageError, match="same-owner repositories"):
        transport.reconcile_issue_fields(
            project_rest.RestIssueFieldRequest(
                owner="basefoundry",
                repo_owner="other-owner",
                repo_name="repo",
                issue_number=1311,
                project_title="base",
                field_values={"status": "Backlog"},
                resolve_updates=lambda _fields, _values: (),
                dry_run=False,
                allow_cross_repo=False,
            )
        )


def test_rest_doctor_uses_project_field_schema() -> None:
    payload = fixture()

    def run(path: str, **_kwargs: object) -> object:
        if path == "users/basefoundry":
            return payload["owner"]
        if path == "orgs/basefoundry/projectsV2?per_page=100":
            return payload["projects"]
        if path.endswith("projectsV2/1/fields?per_page=100"):
            return payload["fields"]
        raise AssertionError(f"unexpected REST path: {path}")

    args = ProjectArguments(area="project", command="doctor", project_title="base", owner="basefoundry")
    transport = project_rest.RestProjectTransport(run=run, sleep=lambda _seconds: None)
    assert project_rest.rest_doctor_command(
        args,
        transport=transport,
        compare_schema=lambda fields, _schema: () if len(fields) == 5 else ("missing",),
        schema_for_args=lambda _args: object(),
    ) == 0
