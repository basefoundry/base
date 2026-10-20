from __future__ import annotations

from collections.abc import Iterator

import pytest

from base_github_projects import engine
from base_github_projects import graphql_queries as queries


def graphql_responses(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[dict[str, object]],
) -> list[tuple[str, dict[str, object]]]:
    remaining: Iterator[dict[str, object]] = iter(responses)
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run(query: str, variables: dict[str, object]) -> dict[str, object]:
        calls.append((query, variables))
        return next(remaining)

    monkeypatch.setattr(engine, "run_graphql", fake_run)
    return calls


def test_fetch_project_fields_and_views_parse_supported_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {
                "data": {
                    "node": {
                        "fields": {
                            "nodes": [
                                {
                                    "__typename": "ProjectV2Field",
                                    "id": "title-field",
                                    "name": "Title",
                                    "dataType": "TITLE",
                                },
                                {
                                    "__typename": "ProjectV2SingleSelectField",
                                    "id": "status-field",
                                    "name": "Status",
                                    "dataType": "SINGLE_SELECT",
                                    "options": [
                                        {"id": "ready", "name": "Ready", "color": "GREEN"},
                                    ],
                                },
                                {"__typename": "ProjectV2IterationField", "id": "iteration"},
                            ]
                        }
                    }
                }
            },
            {
                "data": {
                    "node": {
                        "views": {
                            "nodes": [
                                {"name": "Backlog", "layout": "TABLE_LAYOUT"},
                                {"name": "Board", "layout": "BOARD_LAYOUT"},
                            ]
                        }
                    }
                }
            },
        ],
    )

    fields = engine.fetch_project_fields("project-id")
    views = engine.fetch_project_views("project-id")

    assert fields == (
        engine.ProjectField("title-field", "Title", "TITLE"),
        engine.ProjectField(
            "status-field",
            "Status",
            "SINGLE_SELECT",
            (engine.SelectOption("Ready", "GREEN", "", "ready"),),
        ),
    )
    assert views == (
        engine.ProjectView("Backlog", "TABLE_LAYOUT"),
        engine.ProjectView("Board", "BOARD_LAYOUT"),
    )
    assert calls == [
        (queries.FETCH_PROJECT_FIELDS, {"id": "project-id"}),
        (queries.FETCH_PROJECT_VIEWS, {"id": "project-id"}),
    ]


@pytest.mark.parametrize("fetch", [engine.fetch_project_fields, engine.fetch_project_views])
def test_fetch_project_metadata_reports_missing_project(
    monkeypatch: pytest.MonkeyPatch,
    fetch: object,
) -> None:
    graphql_responses(monkeypatch, [{"data": {"node": None}}])

    with pytest.raises(engine.ProjectError, match="GitHub Project was not found"):
        fetch("missing-project")  # type: ignore[operator]


def test_project_create_copy_and_update_send_expected_mutations(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {"data": {"createProjectV2": {"projectV2": {"id": "created", "title": "New"}}}},
            {"data": {"copyProjectV2": {"projectV2": {"id": "copied", "title": "Copy"}}}},
            {"data": {"updateProjectV2": {"projectV2": {"id": "copied"}}}},
        ],
    )

    assert engine.create_project("owner-id", "New") == engine.ProjectInfo("created", "New")
    assert engine.copy_project("template-id", "owner-id", "Copy") == engine.ProjectInfo("copied", "Copy")
    engine.update_project("copied", title="Renamed", closed=False)

    assert calls[:2] == [
        (queries.CREATE_PROJECT, {"ownerId": "owner-id", "title": "New"}),
        (
            queries.COPY_PROJECT,
            {"projectId": "template-id", "ownerId": "owner-id", "title": "Copy"},
        ),
    ]
    update_query, update_variables = calls[2]
    assert "updateProjectV2" in update_query
    assert "$title: String!" in update_query
    assert "$closed: Boolean!" in update_query
    assert update_variables == {"projectId": "copied", "title": "Renamed", "closed": False}

    with pytest.raises(ValueError, match="requires title or closed"):
        engine.update_project("copied")


def test_repository_link_fetches_id_and_creates_link(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {
                "data": {
                    "node": {
                        "repositories": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
            {"data": {"repository": {"id": "repository-id"}}},
            {"data": {"linkProjectV2ToRepository": {"repository": {"id": "repository-id"}}}},
        ],
    )

    engine.link_project_to_repository("project-id", "basefoundry/base")

    assert calls == [
        (
            queries.FETCH_PROJECT_REPOSITORY_NAMES,
            {"projectId": "project-id", "cursor": None},
        ),
        (
            queries.FETCH_REPOSITORY_ID,
            {"owner": "basefoundry", "name": "base"},
        ),
        (
            queries.LINK_PROJECT_TO_REPOSITORY,
            {"projectId": "project-id", "repositoryId": "repository-id"},
        ),
    ]


def test_fetch_project_repository_names_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {
                "data": {
                    "node": {
                        "repositories": {
                            "nodes": [{"nameWithOwner": "basefoundry/base"}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "page-2"},
                        }
                    }
                }
            },
            {
                "data": {
                    "node": {
                        "repositories": {
                            "nodes": [{"nameWithOwner": "basefoundry/base-cli"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
        ],
    )

    assert engine.fetch_project_repository_names("project-id") == {
        "basefoundry/base",
        "basefoundry/base-cli",
    }
    assert [variables["cursor"] for _, variables in calls] == [None, "page-2"]


def test_fetch_repository_and_project_issues_paginate_and_skip_nonissues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {
                "data": {
                    "repository": {
                        "issues": {
                            "nodes": [{"id": "issue-1", "number": 1}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "issues-2"},
                        }
                    }
                }
            },
            {
                "data": {
                    "repository": {
                        "issues": {
                            "nodes": [{"id": "issue-2", "number": 2}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
            {
                "data": {
                    "node": {
                        "items": {
                            "nodes": [
                                {"content": {"id": "issue-1"}},
                                {"content": {}},
                                {},
                            ],
                            "pageInfo": {"hasNextPage": True, "endCursor": "items-2"},
                        }
                    }
                }
            },
            {
                "data": {
                    "node": {
                        "items": {
                            "nodes": [{"content": {"id": "issue-2"}}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
        ],
    )

    assert engine.fetch_repository_issues("basefoundry/base") == (("issue-1", 1), ("issue-2", 2))
    assert engine.fetch_project_issue_content_ids("project-id") == {"issue-1", "issue-2"}
    assert [variables["cursor"] for _, variables in calls] == [None, "issues-2", None, "items-2"]


@pytest.mark.parametrize(
    ("function", "response", "message"),
    [
        (
            lambda: engine.fetch_repository_id("basefoundry/missing"),
            {"data": {"repository": None}},
            "Repository 'basefoundry/missing' was not found",
        ),
        (
            lambda: engine.fetch_repository_issues("basefoundry/missing"),
            {"data": {"repository": None}},
            "Repository 'basefoundry/missing' was not found",
        ),
        (
            lambda: engine.fetch_project_repository_names("missing"),
            {"data": {"node": None}},
            "GitHub Project was not found",
        ),
        (
            lambda: engine.fetch_project_issue_content_ids("missing"),
            {"data": {"node": None}},
            "GitHub Project was not found",
        ),
    ],
)
def test_graphql_lookup_helpers_report_missing_resources(
    monkeypatch: pytest.MonkeyPatch,
    function: object,
    response: dict[str, object],
    message: str,
) -> None:
    graphql_responses(monkeypatch, [response])

    with pytest.raises(engine.ProjectError, match=message):
        function()  # type: ignore[operator]


def test_issue_and_item_mutations_use_exact_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {"data": {"repository": {"issue": {"id": "issue-id"}}}},
            {
                "data": {
                    "node": {
                        "items": {
                            "nodes": [
                                {"id": "other-item", "content": {"id": "other-issue"}},
                                {"id": "item-id", "content": {"id": "issue-id"}},
                            ]
                        }
                    }
                }
            },
            {"data": {"addProjectV2ItemById": {"item": {"id": "new-item"}}}},
            {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "item-id"}}}},
        ],
    )

    assert engine.fetch_issue_id("basefoundry", "base", 2049) == "issue-id"
    assert engine.find_project_item_id("project-id", "issue-id") == "item-id"
    assert engine.add_project_item("project-id", "issue-id") == "new-item"
    engine.update_item_field(
        "project-id",
        "item-id",
        engine.FieldUpdate("status-field", "in-review", "Status", "In Review"),
    )

    assert calls == [
        (
            queries.FETCH_ISSUE_ID,
            {"owner": "basefoundry", "name": "base", "number": 2049},
        ),
        (queries.FIND_PROJECT_ITEM_ID, {"projectId": "project-id"}),
        (queries.ADD_PROJECT_ITEM, {"projectId": "project-id", "contentId": "issue-id"}),
        (
            queries.UPDATE_ITEM_FIELD,
            {
                "projectId": "project-id",
                "itemId": "item-id",
                "fieldId": "status-field",
                "optionId": "in-review",
            },
        ),
    ]


def test_missing_issue_and_project_item_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {"data": {"repository": {"issue": None}}},
            {"data": {"node": {"items": {"nodes": [{"content": {}}]}}}},
        ],
    )

    with pytest.raises(engine.ProjectError, match="Issue #999 was not found"):
        engine.fetch_issue_id("basefoundry", "base", 999)
    assert engine.find_project_item_id("project-id", "missing-issue") is None
    assert len(calls) == 2


def test_find_project_item_state_reads_existing_single_select_values(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(
        monkeypatch,
        [
            {
                "data": {
                    "node": {
                        "items": {
                            "nodes": [
                                {
                                    "id": "item-id",
                                    "content": {"id": "issue-id"},
                                    "fieldValues": {
                                        "nodes": [
                                            {
                                                "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                                "name": "In Progress",
                                                "field": {"name": "Status"},
                                            },
                                            {
                                                "__typename": "ProjectV2ItemFieldTextValue",
                                                "text": "ignored",
                                            },
                                        ]
                                    },
                                }
                            ]
                        }
                    }
                }
            }
        ],
    )

    assert engine.find_project_item_state("project-id", "issue-id") == engine.ProjectItemState(
        item_id="item-id",
        values={"Status": "In Progress"},
    )
    assert calls == [(queries.FIND_PROJECT_ITEM_WITH_FIELDS, {"projectId": "project-id"})]


def test_single_select_field_mutations_build_option_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = graphql_responses(monkeypatch, [{"data": {}}, {"data": {}}])
    spec = engine.SelectFieldSpec(
        "Priority",
        (engine.SelectOption("P2", "YELLOW", "Normal"),),
    )
    field = engine.ProjectField(
        "priority-field",
        "Priority",
        "SINGLE_SELECT",
        (engine.SelectOption("P1", "ORANGE", "High", "p1"),),
    )

    engine.create_single_select_field("project-id", spec)
    engine.update_single_select_field(field, spec)

    assert calls == [
        (
            queries.CREATE_SINGLE_SELECT_FIELD,
            {
                "projectId": "project-id",
                "name": "Priority",
                "options": [{"name": "P2", "color": "YELLOW", "description": "Normal"}],
            },
        ),
        (
            queries.UPDATE_SINGLE_SELECT_FIELD,
            {
                "fieldId": "priority-field",
                "options": [
                    {"name": "P1", "color": "ORANGE", "description": "High", "id": "p1"},
                    {"name": "P2", "color": "YELLOW", "description": "Normal"},
                ],
            },
        ),
    ]
