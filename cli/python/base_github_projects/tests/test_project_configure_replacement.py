from __future__ import annotations

import pytest

from base_github_projects import engine, project_model


def complete_project_fields() -> tuple[engine.ProjectField, ...]:
    return (
        engine.ProjectField(
            field_id="status-field",
            name="Status",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Status").options,
        ),
        engine.ProjectField(
            field_id="priority-field",
            name="Priority",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Priority").options,
        ),
        engine.ProjectField(
            field_id="area-field",
            name="Area",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Area").options,
        ),
        engine.ProjectField(
            field_id="size-field",
            name="Size",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Size").options,
        ),
        engine.ProjectField(
            field_id="initiative-field",
            name="Initiative",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Initiative").options,
        ),
    )


def test_parse_project_configure_accepts_replace_project() -> None:
    args = engine.parse_args(
        (
            "project",
            "configure",
            "--project",
            "base-bash-libs",
            "--owner",
            "basefoundry",
            "--repo",
            "basefoundry/base-bash-libs",
            "--replace-project",
        )
    )

    assert args.replace_project is True


def test_configure_command_replace_project_requires_repo() -> None:
    with pytest.raises(engine.ProjectUsageError) as excinfo:
        engine.configure_command(
            engine.ProjectArguments(
                area="project",
                command="configure",
                project_title="base-demo",
                owner="codeforester",
                replace_project=True,
            )
        )

    assert str(excinfo.value) == "--replace-project requires --repo."


def test_configure_command_replace_project_skips_replacement_for_standard_views(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    linked: list[tuple[str, str]] = []
    backfilled: list[tuple[str, str]] = []

    monkeypatch.setattr(
        engine,
        "find_owner_and_project",
        lambda owner, title: engine.OwnerInfo(
            owner_id="owner-id",
            login=owner,
            project=engine.ProjectInfo(project_id="project-id", title=title),
        ),
    )
    monkeypatch.setattr(
        engine,
        "fetch_project_views",
        lambda project_id: project_model.STANDARD_TEMPLATE_VIEWS,
    )
    monkeypatch.setattr(engine, "fetch_project_fields", lambda project_id: complete_project_fields())
    monkeypatch.setattr(engine, "create_single_select_field", lambda project_id, spec: None)
    monkeypatch.setattr(engine, "update_single_select_field", lambda field, spec: None)
    monkeypatch.setattr(
        engine,
        "link_project_to_repository",
        lambda project_id, repo: linked.append((project_id, repo)),
    )
    monkeypatch.setattr(
        engine,
        "backfill_repository_issues",
        lambda project_id, repo: backfilled.append((project_id, repo)) or 3,
    )
    monkeypatch.setattr(
        engine,
        "update_project",
        lambda project_id, title=None, closed=None: pytest.fail("standard project must not be renamed or closed"),
    )
    monkeypatch.setattr(
        engine,
        "copy_project",
        lambda template_project_id, owner_id, title: pytest.fail("standard project must not be replaced"),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
            replace_project=True,
        )
    )

    assert status == 0
    assert linked == [("project-id", "codeforester/base-demo")]
    assert backfilled == [("project-id", "codeforester/base-demo")]
    output = capsys.readouterr().out
    assert "INFO: Project 'base-demo' already has standard Base views; skipping replacement." in output
    assert "Configured GitHub Project base-demo" in output


def test_configure_command_replace_project_dry_run_reports_cutover_plan(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        engine,
        "find_owner_and_project",
        lambda owner, title: engine.OwnerInfo(
            owner_id="owner-id",
            login=owner,
            project=engine.ProjectInfo(project_id="project-id", title=title),
        ),
    )
    monkeypatch.setattr(
        engine,
        "fetch_project_views",
        lambda project_id: (engine.ProjectView("View 1", "TABLE_LAYOUT"),),
    )
    monkeypatch.setattr(
        engine,
        "legacy_project_title",
        lambda title: "base-demo-legacy-20260619-120000",
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
            replace_project=True,
            dry_run=True,
        )
    )

    assert status == 0
    output = capsys.readouterr().out
    assert "Would replace existing GitHub Project 'base-demo'." in output
    assert "Existing Project view mismatch: Backlog view is missing." in output
    assert "Would rename existing GitHub Project 'base-demo' to 'base-demo-legacy-20260619-120000'." in output
    assert "Would copy GitHub Project 'base-project-template' to 'base-demo'." in output
    assert (
        "Would copy missing item field values from legacy GitHub Project "
        "'base-demo-legacy-20260619-120000' into 'base-demo'."
    ) in output
    assert "Would close legacy GitHub Project 'base-demo-legacy-20260619-120000' after replacement succeeds." in output


def test_configure_command_replace_project_renames_copies_backfills_and_closes_legacy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    updates: list[tuple[str, str | None, bool | None]] = []
    copies: list[tuple[str, str, str]] = []
    linked: list[tuple[str, str]] = []
    backfilled: list[tuple[str, str]] = []
    field_copies: list[tuple[str, str]] = []

    def fake_find_owner_and_project(owner: str, title: str) -> engine.OwnerInfo:
        if title == "base-demo":
            return engine.OwnerInfo(
                owner_id="owner-id",
                login=owner,
                project=engine.ProjectInfo(project_id="legacy-project", title=title),
            )
        if title == engine.DEFAULT_TEMPLATE_PROJECT:
            return engine.OwnerInfo(
                owner_id="owner-id",
                login=owner,
                project=engine.ProjectInfo(project_id="template-project", title=title),
            )
        raise AssertionError(f"unexpected project lookup: {title}")

    def fake_copy_project(template_project_id: str, owner_id: str, title: str) -> engine.ProjectInfo:
        copies.append((template_project_id, owner_id, title))
        return engine.ProjectInfo(project_id="new-project", title=title)

    def fake_fetch_views(project_id: str) -> tuple[engine.ProjectView, ...]:
        if project_id == "legacy-project":
            return (engine.ProjectView("View 1", "TABLE_LAYOUT"),)
        if project_id == "new-project":
            return project_model.STANDARD_TEMPLATE_VIEWS
        raise AssertionError(f"unexpected view lookup: {project_id}")

    monkeypatch.setattr(engine, "find_owner_and_project", fake_find_owner_and_project)
    monkeypatch.setattr(
        engine,
        "legacy_project_title",
        lambda title: "base-demo-legacy-20260619-120000",
    )
    monkeypatch.setattr(
        engine,
        "update_project",
        lambda project_id, title=None, closed=None: updates.append((project_id, title, closed)),
    )
    monkeypatch.setattr(engine, "copy_project", fake_copy_project)
    monkeypatch.setattr(engine, "fetch_project_views", fake_fetch_views)
    monkeypatch.setattr(engine, "fetch_project_fields", lambda project_id: complete_project_fields())
    monkeypatch.setattr(engine, "create_single_select_field", lambda project_id, spec: None)
    monkeypatch.setattr(engine, "update_single_select_field", lambda field, spec: None)
    monkeypatch.setattr(
        engine,
        "link_project_to_repository",
        lambda project_id, repo: linked.append((project_id, repo)),
    )
    monkeypatch.setattr(
        engine,
        "backfill_repository_issues",
        lambda project_id, repo: backfilled.append((project_id, repo)) or 7,
    )
    monkeypatch.setattr(
        engine,
        "copy_missing_project_item_fields",
        lambda source_id, target_id: field_copies.append((source_id, target_id))
        or engine.FieldCopySummary(12, ()),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
            replace_project=True,
        )
    )

    assert status == 0
    assert updates == [
        ("legacy-project", "base-demo-legacy-20260619-120000", None),
        ("legacy-project", None, True),
    ]
    assert copies == [("template-project", "owner-id", "base-demo")]
    assert linked == [("new-project", "codeforester/base-demo")]
    assert backfilled == [("new-project", "codeforester/base-demo")]
    assert field_copies == [("legacy-project", "new-project")]
    output = capsys.readouterr().out
    assert "Renamed existing Project base-demo to base-demo-legacy-20260619-120000" in output
    assert "Backfilled 7 issue(s) from codeforester/base-demo" in output
    assert "Copied 12 Project item field value(s) from base-demo-legacy-20260619-120000" in output
    assert "Closed legacy GitHub Project base-demo-legacy-20260619-120000" in output
