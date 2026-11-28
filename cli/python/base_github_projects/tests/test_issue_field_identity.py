"""Issue #2713: role precedence and value identity regressions (recorded API shapes)."""

from __future__ import annotations

from dataclasses import replace

# The parser functions are intentional test entry points.
# pylint: disable=protected-access,use-implicit-booleaness-not-comparison,too-many-statements

import pytest

from base_github_projects import engine, graphql_queries, project_schema, project_rest
from base_github_projects.project_field_resolution import resolve_project_field

CASES = ("A1", "A2", "A2-synthetic", "B1", "B2", "C", "D1", "D2", "M")


def fields_for(case):
    fields = []
    for spec in engine.BASE_PROJECT_SCHEMA.fields:
        if spec.name in {"Priority", "Size"}:
            if case in {"C", "D1", "D2"}:
                continue
            if case in {"B1", "B2"} or (case == "M" and spec.name == "Size"):
                name = {"Priority": "Legacy priority", "Size": "Legacy size"}[spec.name]
            else:
                name = spec.name
        else:
            name = spec.name
        options = tuple(replace(o, option_id=f"{name}-{o.name}") for o in spec.options)
        fields.append(engine.ProjectField(name, name, "SINGLE_SELECT", options))
        if case.startswith("A2") and spec.name in {"Priority", "Size"}:
            fields.append(replace(fields[-1], field_id=f"Legacy {name.lower()}", name=f"Legacy {name.lower()}"))
    if case in {"A2-synthetic", "B1", "C", "D1"}:
        fields.append(engine.ProjectField("ISSUE_PRIORITY", "Priority", "SINGLE_SELECT", (), True))
    return tuple(fields)


@pytest.mark.parametrize("case", CASES)
def test_role_resolution_and_schema_clash(case):
    fields = fields_for(case)
    for role in ("Priority", "Size"):
        field = resolve_project_field(fields, role)
        if case in {"C", "D1", "D2"}:
            assert field is None
        else:
            legacy = case in {"B1", "B2"} or (case == "M" and role == "Size")
            assert field.field_id == (f"Legacy {role.lower()}" if legacy else role)
    findings = project_schema.compare_schema(fields, engine.BASE_PROJECT_SCHEMA)
    if case in {"C", "D1"}:
        assert [(f.name, f.status) for f in findings] == [("Priority", "conflict"), ("Size", "missing")]
    elif case == "D2":
        assert {f.status for f in findings} == {"missing"}
    else:
        assert not findings


def test_both_metadata_parsers_keep_marker(monkeypatch):
    raw = {
        "__typename": "ProjectV2SingleSelectField",
        "id": "issue",
        "name": "Priority",
        "dataType": "SINGLE_SELECT",
        "isIssueField": True,
        "options": [],
    }
    monkeypatch.setattr(engine, "run_graphql", lambda *_: {"data": {"node": {"fields": {"nodes": [raw]}}}})
    assert engine.fetch_project_fields("P")[0].is_issue_field
    assert project_rest._parse_project_field({"id": 1, "name": "Priority", "issue_field_id": 43373537}).is_issue_field
    assert not project_rest._parse_project_field({"id": 2, "name": "Priority"}).is_issue_field
    assert "isIssueField" in graphql_queries.FETCH_PROJECT_FIELDS


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("source", [None, "project_fields"])
def test_command_matrix(case, source, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from base_github_projects import project_configure_command, project_doctor_command
    from base_github_projects import project_issue_fields_command, project_issue_field_copy_command

    fields = fields_for(case)
    config = tmp_path / "project.yml"
    config.write_text("project: {}\n" if source is None else "project:\n  field_source: project_fields\n")
    args = engine.ProjectArguments(
        area="project",
        command="configure",
        project_title="fixture",
        owner="basefoundry",
        repo="basefoundry/fixture",
        config_path=str(config),
        field_values={"priority": "P2", "size": "S"},
        issue_number=1,
    )
    project = engine.ProjectInfo("PROJECT", "fixture", 10, "basefoundry", "Organization")
    owner = engine.OwnerInfo("OWNER", "basefoundry", project)
    events = []
    ops = replace(
        engine.project_operations(),
        find_owner_and_project=lambda *_: owner,
        fetch_project_fields=lambda *_: fields,
        fetch_project_repository_names=lambda *_: {"basefoundry/fixture"},
        fetch_issue_id=lambda *_: "ISSUE",
        find_project_item_state=lambda *_: engine.ProjectItemState("ITEM", {}),
        update_item_field=lambda _p, _i, u: events.append(("write", u.field_id)),
        create_single_select_field=lambda _p, s: events.append(("create", s.name)),
        update_single_select_field=lambda *_: events.append(("options",)),
        link_project_to_repository=lambda *_: None,
        backfill_repository_issues=lambda *_: (),
    )
    assert project_doctor_command.doctor_command(args, ops) == (1 if case in {"C", "D1", "D2"} else 0)
    rest = SimpleNamespace(find_owner_and_project=lambda *_: owner, fetch_project_fields=lambda *_: fields)
    assert project_rest.rest_doctor_command(args, transport=rest, compare_schema=project_schema.compare_schema) == (
        1 if case in {"C", "D1", "D2"} else 0
    )
    assert project_configure_command.configure_command(args, ops) == (1 if case in {"C", "D1"} else 0)
    if case in {"C", "D1"}:
        assert not events
    if case == "D2":
        assert events == [("create", "Priority"), ("create", "Size")]
    events.clear()
    if case in {"C", "D1", "D2"}:
        with pytest.raises(engine.ProjectUsageError, match="conflicts|was not found"):
            project_issue_fields_command.issue_set_fields_command(args, ops)
    else:
        assert project_issue_fields_command.issue_set_fields_command(args, ops) == 0
        assert [e[1] for e in events] == [resolve_project_field(fields, r).field_id for r in ("Priority", "Size")]
    # Actual REST reconciliation, including value suppression/readback, with recorded responses.
    transport = project_rest.RestProjectTransport()
    monkeypatch.setattr(transport, "find_owner_and_project", lambda *_: owner)
    monkeypatch.setattr(transport, "fetch_project_fields", lambda *_: fields)
    monkeypatch.setattr(transport, "fetch_issue", lambda *_: {"id": 1})
    state = {}

    def item(_lookup):
        return {
            "id": "ITEM",
            "fields": [
                {"id": f.field_id, "name": f.name, "value": {"name": {"raw": state.get(f.field_id, "")}}}
                for f in fields
            ],
        }

    monkeypatch.setattr(transport, "find_project_item", item)

    def update(_p, _i, updates):
        for u in updates:
            assert u.field_id != "ISSUE_PRIORITY"
            state[u.field_id] = u.option_name

    monkeypatch.setattr(transport, "update_project_item", update)
    request = project_rest.RestIssueFieldRequest(
        owner="basefoundry",
        project_title="fixture",
        repo_owner="basefoundry",
        repo_name="fixture",
        issue_number=1,
        field_values={"priority": "P2", "size": "S"},
        dry_run=False,
        allow_cross_repo=False,
        resolve_updates=lambda fs, vs: project_schema.resolve_issue_field_updates(fs, vs, project_title="fixture"),
    )
    if case in {"C", "D1", "D2"}:
        with pytest.raises(engine.ProjectUsageError, match="conflicts|was not found"):
            transport.reconcile_issue_fields(request)
    else:
        assert transport.reconcile_issue_fields(request) == 0
        assert set(state) == {resolve_project_field(fields, r).field_id for r in ("Priority", "Size")}
    # Both copy directions retain the same selected Project field IDs in every source mode.
    for direction in ("project-to-issue", "issue-to-project"):
        item = engine.ProjectIssueData(
            "ITEM", "ISSUE", "basefoundry/fixture", 1, "fixture", {}, {"Priority": "Medium", "Effort": "Small"}
        )
        if case in {"C", "D1", "D2"}:
            with pytest.raises(ValueError, match="conflicts|missing"):
                project_issue_field_copy_command.make_copy_plan((item,), fields, direction, project_title="fixture")
        else:
            rows = project_issue_field_copy_command.make_copy_plan((item,), fields, direction, project_title="fixture")
            if direction == "issue-to-project":
                assert {u.field_id for u in rows[0]["changes"]} == {
                    resolve_project_field(fields, r).field_id for r in ("Priority", "Size")
                }


@pytest.mark.parametrize("path", ["existing", "template", "replacement"])
@pytest.mark.parametrize("dry_run", [False, True])
def test_clash_preflight_precedes_every_write(path, dry_run, tmp_path):
    from base_github_projects import project_configure_command, project_model

    config = tmp_path / "project.yml"
    config.write_text("project: {}\n")
    project = engine.ProjectInfo("EXISTING", "fixture")
    template = engine.ProjectInfo("TEMPLATE", engine.DEFAULT_TEMPLATE_PROJECT)

    def find(_owner, title):
        target = template if title == engine.DEFAULT_TEMPLATE_PROJECT else (None if path == "template" else project)
        return engine.OwnerInfo("OWNER", "basefoundry", target)

    def forbidden(*_a, **_k):
        pytest.fail("write before clash preflight")

    ops = replace(
        engine.project_operations(),
        find_owner_and_project=find,
        fetch_project_fields=lambda _: fields_for("C"),
        fetch_project_views=lambda _: (project_model.ProjectView("old", "TABLE_LAYOUT"),),
        copy_template_project=forbidden,
        create_project=forbidden,
        update_project=forbidden,
        create_single_select_field=forbidden,
        update_single_select_field=forbidden,
        link_project_to_repository=forbidden,
        backfill_repository_issues=forbidden,
        apply_missing_project_item_defaults=forbidden,
        copy_missing_project_item_fields=forbidden,
    )
    args = engine.ProjectArguments(
        "project",
        "configure",
        project_title="fixture",
        owner="basefoundry",
        repo="basefoundry/fixture",
        config_path=str(config),
        replace_project=path == "replacement",
        dry_run=dry_run,
    )
    assert project_configure_command.configure_command(args, ops) == 1


def test_all_item_value_adapters_exclude_issue_fields(monkeypatch):
    from base_github_projects import project_item_fields

    raw = {
        "__typename": "ProjectV2ItemFieldSingleSelectValue",
        "name": "P2",
        "field": {"id": "ISSUE_PRIORITY", "name": "Priority", "isIssueField": True},
    }
    assert project_item_fields.single_select_values({"fieldValues": {"nodes": [raw]}}) == {}
    assert (
        project_rest._item_field_values(
            {"fields": [{"id": 900, "name": "Priority", "issue_field_id": 43373537, "value": {"name": "P2"}}]}
        )
        == {}
    )
    assert (
        project_rest._item_field_values({"fields": [{"id": 900, "name": "Priority", "value": {"name": "P2"}}]}, ("11",))
        == {}
    )
    payload = {
        "data": {
            "node": {
                "items": {
                    "nodes": [
                        {
                            "id": "ITEM",
                            "content": {
                                "id": "ISSUE",
                                "number": 1,
                                "repository": {"nameWithOwner": "basefoundry/fixture"},
                            },
                            "fieldValues": {"nodes": [raw]},
                        }
                    ],
                    "pageInfo": {"hasNextPage": False},
                }
            }
        }
    }
    monkeypatch.setattr(engine, "run_graphql", lambda *_: payload)
    assert engine.find_project_item_state("P", "ISSUE").values == {}
    assert engine.fetch_project_issue_items("P")[0].project_values == {}
    assert "isIssueField" in graphql_queries.FIND_PROJECT_ITEM_WITH_FIELDS
    assert "isIssueField" in graphql_queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_FIELDS
    assert "isIssueField" in graphql_queries.FETCH_PROJECT_ISSUE_ITEMS_WITH_ISSUE_FIELDS


@pytest.mark.parametrize("case", CASES)
def test_copy_and_default_adapters_resolve_each_role(case):
    from base_github_projects import project_item_fields

    fields = fields_for(case)
    selected = project_item_fields.select_fields_by_name(fields)
    for role in ("Priority", "Size"):
        expected = resolve_project_field(fields, role)
        if expected is None:
            assert role not in selected
        else:
            assert selected[role].field_id == expected.field_id
    if case not in {"C", "D1", "D2"}:
        target = project_item_fields.ProjectIssueItem("ITEM", "ISSUE", 1, "fixture", {})
        plan = project_item_fields.plan_missing_field_defaults(
            target_items={"ISSUE": target}, target_fields=selected, field_defaults={"Priority": "P2", "Size": "S"}
        )
        assert {u.field_id for u in plan.updates} == {
            resolve_project_field(fields, r).field_id for r in ("Priority", "Size")
        }


def test_standard_empty_value_is_not_replaced_with_legacy_value():
    from base_github_projects import project_item_fields

    raw = {
        "fieldValues": {
            "nodes": [
                {
                    "__typename": "ProjectV2ItemFieldSingleSelectValue",
                    "name": "P1",
                    "field": {"id": "Legacy priority", "name": "Legacy priority", "isIssueField": False},
                }
            ]
        }
    }
    assert "Priority" not in project_item_fields.single_select_values(raw, fields=fields_for("A2"))
    assert project_item_fields.single_select_values(raw, fields=fields_for("B2"))["Priority"] == "P1"


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("source", [None, "project_fields", "issue_fields"])
@pytest.mark.parametrize("direction", ["project-to-issue", "issue-to-project"])
def test_copy_command_is_independent_of_field_source(case, source, direction, tmp_path):
    from base_github_projects import project_issue_field_copy_command as command

    fields = fields_for(case)
    config = tmp_path / "project.yml"
    config.write_text("project: {}\n" if source is None else f"project:\n  field_source: {source}\n")
    item = engine.ProjectIssueData(
        "ITEM", "ISSUE", "basefoundry/fixture", 1, "fixture", {}, {"Priority": "Medium", "Effort": "Small"}
    )
    ops = replace(
        engine.project_operations(),
        require_owner=lambda _: "basefoundry",
        find_owner_and_project=lambda *_: engine.OwnerInfo(
            "OWNER", "basefoundry", engine.ProjectInfo("PROJECT", "fixture")
        ),
        fetch_project_fields=lambda _: fields,
        fetch_project_issue_items=lambda _: (item,),
    )
    args = engine.ProjectArguments(
        "project",
        "issue-copy-fields",
        project_title="fixture",
        owner="basefoundry",
        copy_direction=direction,
        config_path=str(config),
    )
    if case in {"C", "D1", "D2"}:
        with pytest.raises(engine.ProjectUsageError, match="conflicts|missing"):
            command.copy_issue_fields_command(args, ops)
    else:
        assert command.copy_issue_fields_command(args, ops) == 0


@pytest.mark.parametrize("case", ["A2-synthetic", "B1"])
def test_rest_issue_only_readback_cannot_verify_project_update(case, monkeypatch):
    fields = fields_for(case)
    transport = project_rest.RestProjectTransport()
    owner = engine.OwnerInfo(
        "OWNER", "basefoundry", engine.ProjectInfo("PROJECT", "fixture", 10, "basefoundry", "Organization")
    )
    monkeypatch.setattr(transport, "find_owner_and_project", lambda *_: owner)
    monkeypatch.setattr(transport, "fetch_project_fields", lambda *_: fields)
    monkeypatch.setattr(transport, "fetch_issue", lambda *_: {"id": 1})
    monkeypatch.setattr(
        transport,
        "find_project_item",
        lambda _: {
            "id": "ITEM",
            "fields": [{"id": "ISSUE_PRIORITY", "name": "Priority", "value": {"name": {"raw": "P2"}}}],
        },
    )
    writes = []
    monkeypatch.setattr(transport, "update_project_item", lambda _p, _i, updates: writes.extend(updates))
    request = project_rest.RestIssueFieldRequest(
        owner="basefoundry",
        project_title="fixture",
        repo_owner="basefoundry",
        repo_name="fixture",
        issue_number=1,
        field_values={"priority": "P2"},
        dry_run=False,
        allow_cross_repo=False,
        resolve_updates=lambda fs, vs: project_schema.resolve_issue_field_updates(fs, vs, project_title="fixture"),
    )
    with pytest.raises(engine.ProjectError, match="validation failed"):
        transport.reconcile_issue_fields(request)
    assert [u.field_id for u in writes] == [resolve_project_field(fields, "Priority").field_id]
