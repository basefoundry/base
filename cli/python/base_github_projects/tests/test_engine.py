from __future__ import annotations

from pathlib import Path

import pytest

from base_github_projects import engine, project_model


def test_parse_project_configure_arguments() -> None:
    args = engine.parse_args(
        (
            "project",
            "configure",
            "--project",
            "BankBuddy Roadmap",
            "--owner",
            "codeforester",
            "--repo",
            "codeforester/bankbuddy",
            "--schema",
            "base-project",
            "--initiative-option",
            "MVP",
            "--initiative-option",
            "Imports",
            "--dry-run",
        )
    )

    assert args.area == "project"
    assert args.command == "configure"
    assert args.project_title == "BankBuddy Roadmap"
    assert args.owner == "codeforester"
    assert args.repo == "codeforester/bankbuddy"
    assert args.schema == "base-project"
    assert args.initiative_options == ("MVP", "Imports")
    assert args.dry_run is True


def test_parse_project_configure_accepts_config_path() -> None:
    args = engine.parse_args(
        (
            "project",
            "configure",
            "--project",
            "base-demo",
            "--owner",
            "codeforester",
            "--repo",
            "codeforester/base-demo",
            "--config",
            ".github/base-project.yml",
        )
    )

    assert args.config_path == ".github/base-project.yml"


def test_parse_project_configure_accepts_copy_fields_from_project() -> None:
    args = engine.parse_args(
        (
            "project",
            "configure",
            "--project",
            "base",
            "--owner",
            "codeforester",
            "--repo",
            "codeforester/base",
            "--copy-fields-from",
            "Base Roadmap",
        )
    )

    assert args.copy_fields_from_project == "Base Roadmap"


def test_parse_project_arguments_accept_equals_options() -> None:
    args = engine.parse_args(
        (
            "project",
            "issue",
            "set-fields",
            "604",
            "--project=Base Roadmap",
            "--repo=codeforester/base",
            "--status=Backlog",
            "--priority=P2",
            "--area=CLI",
            "--initiative=v1.0 Readiness",
            "--size=M",
            "--dry-run",
        )
    )

    assert args.command == "issue-set-fields"
    assert args.project_title == "Base Roadmap"
    assert args.repo == "codeforester/base"
    assert args.issue_number == 604
    assert args.field_values == {
        "status": "Backlog",
        "priority": "P2",
        "area": "CLI",
        "initiative": "v1.0 Readiness",
        "size": "M",
    }
    assert args.dry_run is True


def test_read_project_config_loads_repo_taxonomy(tmp_path: Path) -> None:
    config_path = tmp_path / "base-project.yml"
    config_path.write_text(
        "\n".join(
            (
                "project:",
                "  areas:",
                "    - Demo App",
                "    - Documentation",
                "  initiatives:",
                "    - Demo Polish",
                "    - Portfolio Dashboard",
                "  issue_defaults:",
                "    status: Backlog",
                "    priority: P2",
                "    size: S",
            )
        ),
        encoding="utf-8",
    )

    config = engine.read_project_config(config_path)

    assert config.areas == ("Demo App", "Documentation")
    assert config.initiatives == ("Demo Polish", "Portfolio Dashboard")
    assert config.issue_defaults == {"status": "Backlog", "priority": "P2", "size": "S"}


def test_read_project_config_rejects_non_string_options(tmp_path: Path) -> None:
    config_path = tmp_path / "base-project.yml"
    config_path.write_text("project:\n  areas:\n    - Demo App\n    - 42\n", encoding="utf-8")

    with pytest.raises(engine.ProjectUsageError) as excinfo:
        engine.read_project_config(config_path)

    assert str(excinfo.value) == f"{config_path}: project.areas[1] must be a non-empty string."


def test_issue_field_values_use_config_defaults_and_explicit_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "base-project.yml"
    config_path.write_text(
        "project:\n"
        "  areas: []\n"
        "  initiatives: []\n"
        "  issue_defaults:\n"
        "    status: Backlog\n"
        "    priority: P2\n"
        "    size: S\n"
        "    area: CLI\n",
        encoding="utf-8",
    )

    values = engine.issue_field_values_for_args(
        engine.ProjectArguments(
            area="project",
            command="issue-set-fields",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
            config_path=str(config_path),
            issue_number=604,
            field_values={"priority": "P1"},
        )
    )

    assert values == {
        "status": "Backlog",
        "priority": "P1",
        "size": "S",
        "area": "CLI",
    }


def test_schema_for_args_adds_repo_project_config_options(tmp_path: Path) -> None:
    config_path = tmp_path / "base-project.yml"
    config_path.write_text(
        "project:\n"
        "  areas:\n"
        "    - Demo App\n"
        "  initiatives:\n"
        "    - Demo Polish\n",
        encoding="utf-8",
    )

    schema = engine.schema_for_args(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
            config_path=str(config_path),
        )
    )

    assert "Demo App" in {option.name for option in schema.field_by_name("Area").options}
    assert "Demo Polish" in {option.name for option in schema.field_by_name("Initiative").options}


def test_base_project_schema_includes_tiny_size_before_small() -> None:
    size_options = engine.BASE_PROJECT_SCHEMA.field_by_name("Size").options

    assert [option.name for option in size_options] == ["T", "S", "M", "L"]
    assert size_options[0].description == "Tiny, obvious change with no cross-module behavior."


def test_compare_schema_reports_missing_fields_wrong_types_and_missing_options() -> None:
    fields = (
        engine.ProjectField(field_id="status", name="Status", data_type="TEXT"),
        engine.ProjectField(
            field_id="priority",
            name="Priority",
            data_type="SINGLE_SELECT",
            options=(
                engine.SelectOption(name="P1", color="ORANGE", description="High priority", option_id="priority-p1"),
            ),
        ),
    )

    findings = engine.compare_schema(fields, engine.BASE_PROJECT_SCHEMA)

    assert engine.Finding("error", "Status", "Status exists with type TEXT; expected SINGLE_SELECT.") in findings
    assert engine.Finding("missing", "Area", "Area field is missing.") in findings
    assert engine.Finding("missing-option", "Priority", "Priority option P0 is missing.") in findings


def test_configuration_plan_preserves_extra_options_and_adds_required_options() -> None:
    field = engine.ProjectField(
        field_id="priority",
        name="Priority",
        data_type="SINGLE_SELECT",
        options=(
            engine.SelectOption(name="P1", color="ORANGE", description="High priority", option_id="priority-p1"),
            engine.SelectOption(name="Later", color="GRAY", description="Manual option", option_id="manual-later"),
        ),
    )

    actions = engine.configuration_plan(
        project_exists=True,
        fields=(field,),
        schema=engine.ProjectSchema(fields=(engine.BASE_PROJECT_SCHEMA.field_by_name("Priority"),)),
    )

    assert actions == (
        engine.ConfigureAction("update-field", "Priority", "Add missing options: P0, P2, P3."),
    )
    updated = engine.merged_options(field, engine.BASE_PROJECT_SCHEMA.field_by_name("Priority"))
    assert [option.name for option in updated] == ["P1", "Later", "P0", "P2", "P3"]
    assert updated[0].option_id == "priority-p1"
    assert updated[1].option_id == "manual-later"


def test_configuration_plan_adds_tiny_size_to_existing_standard_size_field() -> None:
    field = engine.ProjectField(
        field_id="size",
        name="Size",
        data_type="SINGLE_SELECT",
        options=(
            engine.SelectOption(name="S", color="GREEN", description="Small", option_id="size-s"),
            engine.SelectOption(name="M", color="YELLOW", description="Medium", option_id="size-m"),
            engine.SelectOption(name="L", color="ORANGE", description="Large", option_id="size-l"),
        ),
    )

    actions = engine.configuration_plan(
        project_exists=True,
        fields=(field,),
        schema=engine.ProjectSchema(fields=(engine.BASE_PROJECT_SCHEMA.field_by_name("Size"),)),
    )

    assert actions == (engine.ConfigureAction("update-field", "Size", "Add missing options: T."),)
    updated = engine.merged_options(field, engine.BASE_PROJECT_SCHEMA.field_by_name("Size"))
    assert [option.name for option in updated] == ["S", "M", "L", "T"]
    assert [option.option_id for option in updated[:3]] == ["size-s", "size-m", "size-l"]


def test_resolve_issue_field_updates_returns_only_explicit_fields() -> None:
    fields = (
        engine.ProjectField(
            field_id="status-field",
            name="Status",
            data_type="SINGLE_SELECT",
            options=(
                engine.SelectOption(name="Backlog", color="BLUE", description="Accepted", option_id="status-backlog"),
            ),
        ),
        engine.ProjectField(
            field_id="priority-field",
            name="Priority",
            data_type="SINGLE_SELECT",
            options=(
                engine.SelectOption(name="P2", color="YELLOW", description="Normal", option_id="priority-p2"),
            ),
        ),
        engine.ProjectField(
            field_id="area-field",
            name="Area",
            data_type="SINGLE_SELECT",
            options=(
                engine.SelectOption(name="CLI", color="GRAY", description="Command surface", option_id="area-cli"),
            ),
        ),
    )

    updates = engine.resolve_issue_field_updates(
        fields,
        {"status": "Backlog", "priority": "P2"},
        project_title="Base Roadmap",
    )

    assert updates == (
        engine.FieldUpdate("status-field", "status-backlog", "Status", "Backlog"),
        engine.FieldUpdate("priority-field", "priority-p2", "Priority", "P2"),
    )


def test_resolve_issue_field_updates_reports_missing_initiative_option() -> None:
    fields = (
        engine.ProjectField(
            field_id="initiative-field",
            name="Initiative",
            data_type="SINGLE_SELECT",
            options=(),
        ),
    )

    with pytest.raises(engine.ProjectUsageError) as excinfo:
        engine.resolve_issue_field_updates(
            fields,
            {"initiative": "New Theme"},
            project_title="Base Roadmap",
        )

    assert str(excinfo.value) == (
        "Initiative option 'New Theme' was not found in Project 'Base Roadmap'. "
        'Run `basectl gh project configure --project "Base Roadmap" '
        '--initiative-option "New Theme"` first.'
    )


def test_resolve_issue_field_updates_reports_missing_size_option() -> None:
    fields = (
        engine.ProjectField(
            field_id="size-field",
            name="Size",
            data_type="SINGLE_SELECT",
            options=(
                engine.SelectOption(name="S", color="GREEN", description="Small", option_id="size-s"),
                engine.SelectOption(name="M", color="YELLOW", description="Medium", option_id="size-m"),
                engine.SelectOption(name="L", color="ORANGE", description="Large", option_id="size-l"),
            ),
        ),
    )

    with pytest.raises(engine.ProjectUsageError) as excinfo:
        engine.resolve_issue_field_updates(
            fields,
            {"size": "T"},
            project_title="base",
        )

    assert str(excinfo.value) == (
        "Size option 'T' was not found in Project 'base'. "
        'Run `basectl gh project configure --project "base"` first.'
    )


def test_doctor_command_fails_when_schema_is_incomplete(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
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
    monkeypatch.setattr(engine, "fetch_project_fields", lambda project_id: ())

    status = engine.doctor_command(
        engine.ProjectArguments(
            area="project",
            command="doctor",
            project_title="Base Roadmap",
            owner="codeforester",
        )
    )

    assert status == 1
    assert "MISSING Status" in capsys.readouterr().out


def test_configure_command_refetches_default_fields_after_project_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_status_field = engine.ProjectField(
        field_id="status-field",
        name="Status",
        data_type="SINGLE_SELECT",
        options=(
            engine.SelectOption(name="Todo", color="GRAY", description="", option_id="status-todo"),
            engine.SelectOption(
                name="In Progress",
                color="YELLOW",
                description="",
                option_id="status-in-progress",
            ),
            engine.SelectOption(name="Done", color="PURPLE", description="", option_id="status-done"),
        ),
    )
    created_fields: list[str] = []
    updated_fields: list[str] = []

    monkeypatch.setattr(
        engine,
        "find_owner_and_project",
        lambda owner, title: engine.OwnerInfo(owner_id="owner-id", login=owner, project=None),
    )
    monkeypatch.setattr(
        engine,
        "create_project",
        lambda owner_id, title: engine.ProjectInfo(project_id="project-id", title=title),
    )
    monkeypatch.setattr(engine, "fetch_project_fields", lambda project_id: (default_status_field,))
    monkeypatch.setattr(
        engine,
        "create_single_select_field",
        lambda project_id, spec: created_fields.append(spec.name),
    )
    monkeypatch.setattr(
        engine,
        "update_single_select_field",
        lambda field, spec: updated_fields.append(field.name),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="Base Demo Roadmap",
            owner="codeforester",
        )
    )

    assert status == 0
    assert "Status" not in created_fields
    assert "Status" in updated_fields
    assert created_fields == ["Priority", "Area", "Size", "Initiative"]


def test_configure_command_copies_template_for_repo_project_and_backfills_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_field = engine.ProjectField(
        field_id="status-field",
        name="Status",
        data_type="SINGLE_SELECT",
        options=engine.BASE_PROJECT_SCHEMA.field_by_name("Status").options,
    )
    priority_field = engine.ProjectField(
        field_id="priority-field",
        name="Priority",
        data_type="SINGLE_SELECT",
        options=engine.BASE_PROJECT_SCHEMA.field_by_name("Priority").options,
    )
    area_field = engine.ProjectField(
        field_id="area-field",
        name="Area",
        data_type="SINGLE_SELECT",
        options=engine.BASE_PROJECT_SCHEMA.field_by_name("Area").options,
    )
    size_field = engine.ProjectField(
        field_id="size-field",
        name="Size",
        data_type="SINGLE_SELECT",
        options=engine.BASE_PROJECT_SCHEMA.field_by_name("Size").options,
    )
    initiative_field = engine.ProjectField(
        field_id="initiative-field",
        name="Initiative",
        data_type="SINGLE_SELECT",
        options=engine.BASE_PROJECT_SCHEMA.field_by_name("Initiative").options,
    )
    calls: list[tuple[str, str]] = []
    linked: list[tuple[str, str]] = []
    backfilled: list[tuple[str, str]] = []

    def fake_find_owner_and_project(owner: str, title: str) -> engine.OwnerInfo:
        calls.append((owner, title))
        if title == "base-demo":
            return engine.OwnerInfo(owner_id="owner-id", login=owner, project=None)
        if title == engine.DEFAULT_TEMPLATE_PROJECT:
            return engine.OwnerInfo(
                owner_id="owner-id",
                login=owner,
                project=engine.ProjectInfo(project_id="template-id", title=title),
            )
        raise AssertionError(f"unexpected project lookup: {title}")

    monkeypatch.setattr(engine, "find_owner_and_project", fake_find_owner_and_project)
    monkeypatch.setattr(
        engine,
        "copy_project",
        lambda template_id, owner_id, title: engine.ProjectInfo(project_id="project-id", title=title),
    )
    monkeypatch.setattr(
        engine,
        "fetch_project_fields",
        lambda project_id: (status_field, priority_field, area_field, size_field, initiative_field),
    )
    monkeypatch.setattr(engine, "create_single_select_field", lambda project_id, spec: None)
    monkeypatch.setattr(engine, "update_single_select_field", lambda field, spec: None)
    monkeypatch.setattr(engine, "fetch_project_views", lambda project_id: project_model.STANDARD_TEMPLATE_VIEWS)
    monkeypatch.setattr(
        engine,
        "link_project_to_repository",
        lambda project_id, repo: linked.append((project_id, repo)),
    )
    monkeypatch.setattr(
        engine,
        "backfill_repository_issues",
        lambda project_id, repo: backfilled.append((project_id, repo)),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
        )
    )

    assert status == 0
    assert calls == [
        ("codeforester", "base-demo"),
        ("codeforester", engine.DEFAULT_TEMPLATE_PROJECT),
    ]
    assert linked == [("project-id", "codeforester/base-demo")]
    assert backfilled == [("project-id", "codeforester/base-demo")]


def test_configure_command_copies_missing_project_fields_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied: list[tuple[str, str]] = []

    def fake_find_owner_and_project(owner: str, title: str) -> engine.OwnerInfo:
        if title == "base":
            return engine.OwnerInfo(
                owner_id="owner-id",
                login=owner,
                project=engine.ProjectInfo(project_id="target-project", title=title),
            )
        if title == "Base Roadmap":
            return engine.OwnerInfo(
                owner_id="owner-id",
                login=owner,
                project=engine.ProjectInfo(project_id="source-project", title=title),
            )
        raise AssertionError(f"unexpected project lookup: {title}")

    monkeypatch.setattr(engine, "find_owner_and_project", fake_find_owner_and_project)
    monkeypatch.setattr(engine, "fetch_project_fields", lambda project_id: ())
    monkeypatch.setattr(engine, "create_single_select_field", lambda project_id, spec: None)
    monkeypatch.setattr(engine, "update_single_select_field", lambda field, spec: None)
    monkeypatch.setattr(engine, "fetch_project_views", lambda project_id: project_model.STANDARD_TEMPLATE_VIEWS)
    monkeypatch.setattr(engine, "link_project_to_repository", lambda project_id, repo: None)
    monkeypatch.setattr(engine, "backfill_repository_issues", lambda project_id, repo: 0)
    monkeypatch.setattr(
        engine,
        "copy_missing_project_item_fields",
        lambda source_id, target_id: copied.append((source_id, target_id)) or engine.FieldCopySummary(3, ()),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base",
            owner="codeforester",
            repo="codeforester/base",
            copy_fields_from_project="Base Roadmap",
        )
    )

    assert status == 0
    assert copied == [("source-project", "target-project")]


def test_configure_command_applies_issue_defaults_from_project_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "base-project.yml"
    config_path.write_text(
        "project:\n"
        "  areas:\n"
        "    - Product\n"
        "  initiatives:\n"
        "    - Adoption Polish\n"
        "  issue_defaults:\n"
        "    status: Backlog\n"
        "    priority: P2\n"
        "    area: Product\n"
        "    initiative: Adoption Polish\n"
        "    size: S\n",
        encoding="utf-8",
    )
    fields = (
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
            field_id="initiative-field",
            name="Initiative",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Initiative").options,
        ),
        engine.ProjectField(
            field_id="size-field",
            name="Size",
            data_type="SINGLE_SELECT",
            options=engine.BASE_PROJECT_SCHEMA.field_by_name("Size").options,
        ),
    )
    applied: list[tuple[str, dict[str, str]]] = []

    def fake_find_owner_and_project(owner: str, title: str) -> engine.OwnerInfo:
        return engine.OwnerInfo(
            owner_id="owner-id",
            login=owner,
            project=engine.ProjectInfo(project_id="target-project", title=title),
        )

    monkeypatch.setattr(engine, "find_owner_and_project", fake_find_owner_and_project)
    monkeypatch.setattr(engine, "fetch_project_fields", lambda project_id: fields)
    monkeypatch.setattr(engine, "create_single_select_field", lambda project_id, spec: None)
    monkeypatch.setattr(engine, "update_single_select_field", lambda field, spec: None)
    monkeypatch.setattr(engine, "link_project_to_repository", lambda project_id, repo: None)
    monkeypatch.setattr(engine, "backfill_repository_issues", lambda project_id, repo: 0)
    monkeypatch.setattr(
        engine,
        "apply_missing_project_item_defaults",
        lambda project_id, target_fields, defaults: applied.append((project_id, defaults))
        or engine.FieldCopySummary(5, ()),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base",
            owner="codeforester",
            repo="codeforester/base",
            config_path=str(config_path),
        )
    )

    assert status == 0
    assert applied == [
        (
            "target-project",
            {
                "Status": "Backlog",
                "Priority": "P2",
                "Area": "Product",
                "Initiative": "Adoption Polish",
                "Size": "S",
            },
        )
    ]


def test_configure_command_dry_run_reports_template_copy_link_and_backfill(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        engine,
        "find_owner_and_project",
        lambda owner, title: engine.OwnerInfo(owner_id="owner-id", login=owner, project=None),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base-demo",
            owner="codeforester",
            repo="codeforester/base-demo",
            dry_run=True,
        )
    )

    assert status == 0
    output = capsys.readouterr().out
    assert "Would copy GitHub Project 'base-project-template' to 'base-demo'." in output
    assert "Would link GitHub Project 'base-demo' to repository 'codeforester/base-demo'." in output
    assert "Would backfill issues from 'codeforester/base-demo' into GitHub Project 'base-demo'." in output


def test_configure_command_dry_run_reports_field_copy_source(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        engine,
        "find_owner_and_project",
        lambda owner, title: engine.OwnerInfo(owner_id="owner-id", login=owner, project=None),
    )

    status = engine.configure_command(
        engine.ProjectArguments(
            area="project",
            command="configure",
            project_title="base",
            owner="codeforester",
            repo="codeforester/base",
            copy_fields_from_project="Base Roadmap",
            dry_run=True,
        )
    )

    assert status == 0
    output = capsys.readouterr().out
    assert "Would copy missing item field values from GitHub Project 'Base Roadmap'." in output


def test_plan_project_item_field_copies_skips_existing_values_and_missing_options() -> None:
    from base_github_projects import project_item_fields

    source_items = {
        "issue-1": project_item_fields.ProjectIssueItem(
            item_id="source-item-1",
            issue_id="issue-1",
            issue_number=1,
            title="one",
            values={"Priority": "P1", "Size": "M", "Area": "CLI"},
        ),
        "issue-2": project_item_fields.ProjectIssueItem(
            item_id="source-item-2",
            issue_id="issue-2",
            issue_number=2,
            title="two",
            values={"Priority": "P2"},
        ),
    }
    target_items = {
        "issue-1": project_item_fields.ProjectIssueItem(
            item_id="target-item-1",
            issue_id="issue-1",
            issue_number=1,
            title="one",
            values={"Priority": "P0"},
        ),
        "issue-2": project_item_fields.ProjectIssueItem(
            item_id="target-item-2",
            issue_id="issue-2",
            issue_number=2,
            title="two",
            values={},
        ),
    }
    target_fields = {
        "Priority": project_item_fields.ProjectSelectField(
            field_id="priority-field",
            options={"P1": "priority-p1", "P2": "priority-p2"},
        ),
        "Size": project_item_fields.ProjectSelectField(field_id="size-field", options={"S": "size-s"}),
    }

    plan = project_item_fields.plan_missing_field_copies(
        source_items=source_items,
        target_items=target_items,
        target_fields=target_fields,
        field_names=("Priority", "Size", "Area"),
    )

    assert plan.updates == (
        project_item_fields.ProjectFieldCopy(
            item_id="target-item-2",
            issue_number=2,
            field_name="Priority",
            option_name="P2",
            field_id="priority-field",
            option_id="priority-p2",
        ),
    )
    assert plan.skipped == (
        project_item_fields.ProjectFieldCopySkip(1, "Size", "M", "target option is missing"),
        project_item_fields.ProjectFieldCopySkip(1, "Area", "CLI", "target field is missing"),
    )


def test_plan_project_item_field_defaults_skips_existing_values_and_missing_options() -> None:
    from base_github_projects import project_item_fields

    target_items = {
        "issue-1": project_item_fields.ProjectIssueItem(
            item_id="target-item-1",
            issue_id="issue-1",
            issue_number=1,
            title="one",
            values={"Priority": "P1"},
        ),
        "issue-2": project_item_fields.ProjectIssueItem(
            item_id="target-item-2",
            issue_id="issue-2",
            issue_number=2,
            title="two",
            values={},
        ),
    }
    target_fields = {
        "Priority": project_item_fields.ProjectSelectField(
            field_id="priority-field",
            options={"P2": "priority-p2"},
        ),
        "Size": project_item_fields.ProjectSelectField(field_id="size-field", options={}),
    }

    plan = project_item_fields.plan_missing_field_defaults(
        target_items=target_items,
        target_fields=target_fields,
        field_defaults={"Priority": "P2", "Size": "S", "Area": "CLI"},
    )

    assert plan.updates == (
        project_item_fields.ProjectFieldCopy(
            item_id="target-item-2",
            issue_number=2,
            field_name="Priority",
            option_name="P2",
            field_id="priority-field",
            option_id="priority-p2",
        ),
    )
    assert plan.skipped == (
        project_item_fields.ProjectFieldCopySkip(1, "Size", "S", "target option is missing"),
        project_item_fields.ProjectFieldCopySkip(1, "Area", "CLI", "target field is missing"),
        project_item_fields.ProjectFieldCopySkip(2, "Size", "S", "target option is missing"),
        project_item_fields.ProjectFieldCopySkip(2, "Area", "CLI", "target field is missing"),
    )


def test_backfill_repository_issues_adds_only_missing_project_items(monkeypatch: pytest.MonkeyPatch) -> None:
    added: list[tuple[str, str]] = []

    monkeypatch.setattr(engine, "fetch_repository_issue_ids", lambda repo: ("issue-1", "issue-2", "issue-3"))
    monkeypatch.setattr(engine, "fetch_project_issue_content_ids", lambda project_id: {"issue-2"})
    monkeypatch.setattr(
        engine,
        "add_project_item",
        lambda project_id, issue_id: added.append((project_id, issue_id)) or f"item-{issue_id}",
    )

    engine.backfill_repository_issues("project-id", "codeforester/base-demo")

    assert added == [("project-id", "issue-1"), ("project-id", "issue-3")]


def test_link_project_to_repository_skips_existing_link(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(message: str) -> None:
        raise AssertionError(message)

    monkeypatch.setattr(
        engine,
        "fetch_project_repository_names",
        lambda project_id: {"codeforester/base-demo"},
    )
    monkeypatch.setattr(
        engine,
        "fetch_repository_id",
        lambda repo: fail("repository id should not be fetched"),
    )
    monkeypatch.setattr(
        engine,
        "run_graphql",
        lambda query, variables: fail("mutation should not run"),
    )

    engine.link_project_to_repository("project-id", "codeforester/base-demo")


def test_find_owner_and_project_uses_user_lookup_without_organization_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
        assert "user(login:" in query
        assert "organization(login:" not in query
        assert variables == {"login": "codeforester"}
        return {
            "data": {
                "user": {
                    "id": "owner-id",
                    "login": "codeforester",
                    "projectsV2": {"nodes": [{"id": "project-id", "title": "Base Roadmap"}]},
                }
            }
        }

    monkeypatch.setattr(engine, "run_graphql", fake_run_graphql)

    owner = engine.find_owner_and_project("codeforester", "Base Roadmap")

    assert owner == engine.OwnerInfo(
        owner_id="owner-id",
        login="codeforester",
        project=engine.ProjectInfo(project_id="project-id", title="Base Roadmap"),
    )


def test_find_owner_and_project_falls_back_to_organization_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_run_graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
        assert variables == {"login": "example-org"}
        if "user(login:" in query:
            calls.append("user")
            raise engine.ProjectError("Could not resolve to a User with the login of 'example-org'.")
        if "organization(login:" in query:
            calls.append("organization")
            return {
                "data": {
                    "organization": {
                        "id": "owner-id",
                        "login": "example-org",
                        "projectsV2": {"nodes": []},
                    }
                }
            }
        raise AssertionError("unexpected GraphQL query")

    monkeypatch.setattr(engine, "run_graphql", fake_run_graphql)

    owner = engine.find_owner_and_project("example-org", "Roadmap")

    assert calls == ["user", "organization"]
    assert owner == engine.OwnerInfo(owner_id="owner-id", login="example-org", project=None)
