from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from base_github_projects import engine, project_schema
from base_github_projects import project_config_resolution, project_rest
from base_github_projects.project_configure import ConfigureDryRunPlan, render_dry_run_configure


def schema_fields(legacy: tuple[str, ...] = ()) -> tuple[engine.ProjectField, ...]:
    return tuple(
        engine.ProjectField(
            field_id=spec.name,
            name={"Priority": "Legacy priority", "Size": "Legacy size"}.get(spec.name, spec.name)
            if spec.name in legacy else spec.name,
            data_type="SINGLE_SELECT",
            options=spec.options,
        )
        for spec in engine.BASE_PROJECT_SCHEMA.fields
    )


@pytest.fixture(name="planning_schema", params=["no-config", None, "project_fields"])
def planning_schema_fixture(tmp_path: Path, request: pytest.FixtureRequest) -> engine.ProjectSchema:
    source = request.param
    config_path = tmp_path / "config.yml"
    config_path.write_text(f"project:\n  field_source: {source}\n" if source else "project: {}\n")
    args = engine.ProjectArguments(
        area="project", command="doctor", config_path=None if source == "no-config" else str(config_path)
    )
    return project_schema.schema_for_args(args)


@pytest.mark.parametrize("legacy", [("Priority",), ("Size",), ("Priority", "Size"), ()])
def test_legacy_guard_preserves_each_existing_planning_field(
    planning_schema: engine.ProjectSchema, legacy: tuple[str, ...]
) -> None:
    fields = schema_fields(legacy)

    assert not project_schema.compare_schema(fields, planning_schema)
    assert not project_schema.configuration_plan(project_exists=True, fields=fields, schema=planning_schema)


def test_absent_fields_still_report_missing_and_standard_wins_over_legacy(
    planning_schema: engine.ProjectSchema,
) -> None:
    fields = tuple(field for field in schema_fields() if field.name not in {"Priority", "Size"})
    assert {finding.name for finding in project_schema.compare_schema(fields, planning_schema)} == {
        "Priority", "Size"
    }
    assert {action.name for action in project_schema.configuration_plan(
        project_exists=True, fields=fields, schema=planning_schema
    )} == {"Priority", "Size"}
    # A malformed standard field must still be diagnosed even beside a valid Legacy field.
    fields = schema_fields(("Priority", "Size")) + (
        engine.ProjectField(field_id="standard", name="Priority", data_type="TEXT", options=()),
    )
    assert [(finding.name, finding.status) for finding in project_schema.compare_schema(
        fields, planning_schema
    )] == [("Priority", "error")]
    assert [(action.name, action.action) for action in project_schema.configuration_plan(
        project_exists=True, fields=fields, schema=planning_schema
    )] == [("Priority", "error")]


@pytest.fixture(name="checkout")
def checkout_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "checkout"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "git@github.com:basefoundry/base.git"],
                   check=True)
    config = root / ".github" / "base-project.yml"
    config.parent.mkdir()
    config.write_text("project:\n  field_source: issue_fields\n  issue_defaults:\n    priority: Medium\n")
    monkeypatch.chdir(root)
    return config


@pytest.mark.parametrize("command", ["doctor", "configure"])
@pytest.mark.parametrize("explicit", [True, False])
@pytest.mark.parametrize("bad_config", ["project: [\n", "project:\n  field_source: invalid\n"])
def test_invalid_config_precedes_every_project_call(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, command: str, explicit: bool, bad_config: str
) -> None:
    checkout.write_text(bad_config)
    monkeypatch.setattr(engine, "find_owner_and_project", lambda *_args: pytest.fail("Project API read"))
    args = engine.ProjectArguments(
        area="project", command=command, project_title="base", owner="basefoundry",
        config_path=str(checkout) if explicit else None,
    )
    with pytest.raises(engine.ProjectUsageError, match=str(checkout)):
        engine.run_command(args)


@pytest.fixture(name="project_calls")
def project_calls_fixture(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    calls: dict[str, list] = {"reads": [], "creates": [], "updates": [], "defaults": []}

    def find_project(owner: str, title: str) -> engine.OwnerInfo:
        calls["reads"].append((owner, title))
        return engine.OwnerInfo("owner-id", owner, engine.ProjectInfo("project-id", title))

    monkeypatch.setattr(engine, "find_owner_and_project", find_project)
    monkeypatch.setattr(engine, "fetch_project_fields", lambda _project: schema_fields())
    monkeypatch.setattr(engine, "create_single_select_field", lambda _project, spec: calls["creates"].append(spec))
    monkeypatch.setattr(engine, "update_single_select_field", lambda actual, _spec: calls["updates"].append(actual))
    monkeypatch.setattr(engine, "link_project_to_repository", lambda *_args: None)
    monkeypatch.setattr(engine, "backfill_repository_issues", lambda *_args: ())
    monkeypatch.setattr(
        engine, "apply_missing_project_item_defaults",
        lambda _project, _fields, defaults: calls["defaults"].append(defaults) or engine.FieldCopySummary(0, ()),
    )
    return calls


@pytest.mark.parametrize("target", [
    (command, resolution) for command in ("doctor", "configure")
    for resolution in ("explicit", "discovered", "no-checkout", "no-file")
])
def test_commands_resolve_and_report_config(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    project_calls: dict[str, list], target: tuple[str, str],
) -> None:
    command, resolution = target
    # Exercise root discovery from a subdirectory, as well as inferred owners.
    nested = checkout.parent.parent / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)
    explicit_path = checkout.parent.parent.parent / "explicit.yml"
    if resolution == "explicit":
        explicit_path.write_text("project: {}\n")
        checkout.write_text("invalid: [\n")  # Explicit config must win over an invalid discovered file.
    elif resolution == "no-checkout":
        monkeypatch.chdir(checkout.parent.parent.parent)
    elif resolution == "no-file":
        checkout.unlink()
    args = engine.ProjectArguments(
        area="project", command=command, project_title="base",
        owner="basefoundry" if resolution == "no-checkout" else None,
        config_path=str(explicit_path) if resolution == "explicit" else None,
    )
    assert engine.run_command(args) == 0
    output = capsys.readouterr().out
    if resolution in {"explicit", "discovered"}:
        assert f"Config: {explicit_path if resolution == 'explicit' else checkout}" in output
        assert resolution in output
    else:
        assert "Config: no config" in output
        assert ("no checkout" if resolution == "no-checkout" else "no file") in output
    assert project_calls["reads"] == [("basefoundry", "base")]
    assert project_calls["defaults"] == []


@pytest.mark.parametrize(
    "target",
    [
        ("configure", "basefoundry", "base-demo", "basefoundry/base-demo", ("Project title", "--repo")),
        ("configure", "basefoundry", "base-demo", "basefoundry/base", ("Project title",)),
        ("configure", "someone-else", "base", "basefoundry/base", ("Project owner",)),
        ("configure", "basefoundry", "base", "basefoundry/base-demo", ("--repo",)),
        ("doctor", "basefoundry", "base-demo", None, ("Project title",)),
    ],
)
def test_mismatched_target_never_uses_checkout_settings(
    checkout: Path, capsys: pytest.CaptureFixture[str], project_calls: dict[str, list],
    target: tuple[str, str, str, str | None, tuple[str, ...]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    command, owner, title, repo, mismatches = target
    checkout.write_text("project:\n  field_source: issue_fields\n  areas: [CheckoutOnly]\n"
                        "  issue_defaults:\n    area: CheckoutOnly\n")
    fields = tuple(field for field in schema_fields() if field.name not in {"Priority", "Size"})
    monkeypatch.setattr(engine, "fetch_project_fields", lambda _project: fields)
    args = engine.ProjectArguments(area="project", command=command, project_title=title, owner=owner, repo=repo)
    assert engine.run_command(args) == (1 if command == "doctor" else 0)
    output = capsys.readouterr().out
    assert "Config: no config" in output
    assert "--config <path>" in output
    assert "defaults apply only with explicit --config" in output
    for mismatch in mismatches:
        assert mismatch in output
    assert project_calls["updates"] == []  # The checkout-only Area option was not planned or applied.
    assert project_calls["defaults"] == []
    if command == "doctor":
        assert "Priority field is missing" in output
        assert "Size field is missing" in output
    else:
        assert [spec.name for spec in project_calls["creates"]] == ["Priority", "Size"]


@pytest.mark.parametrize("config_case", [
    (source, selection) for source in (None, "project_fields", "issue_fields")
    for selection in ("explicit", "discovered", "none")
])
def test_preview_defaults_and_schema_match_real_configure(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    project_calls: dict[str, list], config_case: tuple[str | None, str],
) -> None:
    source, selection = config_case
    source_line = f"  field_source: {source}\n" if source else ""
    checkout.write_text(
        f"project:\n{source_line}  areas: [LocalArea]\n  initiatives: [LocalInitiative]\n"
        "  issue_defaults:\n    status: Backlog\n    priority: P2\n    effort: Small\n    area: LocalArea\n"
    )
    args = engine.ProjectArguments(
        area="project", command="configure", project_title="base", owner="basefoundry",
        config_path=str(checkout) if selection == "explicit" else None,
    )
    if selection == "none":
        monkeypatch.chdir(checkout.parent.parent.parent)
    resolved = project_config_resolution.resolve_project_config(args, "basefoundry")
    schema = project_schema.schema_for_config(args, resolved.config)
    render_dry_run_configure(args, ConfigureDryRunPlan((), resolved_config=resolved, schema=schema))
    preview = capsys.readouterr().out
    assert engine.configure_command(args) == 0
    capsys.readouterr()
    defaults = project_schema.project_field_defaults_for_config(resolved.config) if selection == "explicit" else {}
    assert project_calls["defaults"] == ([defaults] if defaults else [])
    default_lines = [line for line in preview.splitlines() if "Would apply issue defaults" in line]
    if defaults:
        assert default_lines == [
            "[DRY-RUN] Would apply issue defaults to missing Project item fields: "
            + ", ".join(f"{key}={value}" for key, value in defaults.items()) + "."
        ]
    else:
        assert default_lines == []
    names = "Status, Area, Initiative" if source == "issue_fields" and selection != "none" else (
        "Status, Priority, Area, Size, Initiative"
    )
    assert f"[DRY-RUN] Fields: {names}\n" in preview
    assert f"Config: {checkout}" in preview if selection != "none" else "Config: no config" in preview
    if selection == "discovered":
        assert "defaults apply only with explicit --config" in preview
    # The command passes the same resolution and effective schema to the renderer.
    assert engine.configure_command(replace(args, dry_run=True)) == 0
    command_preview = capsys.readouterr().out
    assert preview == command_preview[:len(preview)]


@pytest.mark.parametrize("command", ["doctor", "configure"])
@pytest.mark.parametrize("source", [None, "project_fields", "issue_fields"])
def test_explicit_config_compatibility(
    checkout: Path, capsys: pytest.CaptureFixture[str], project_calls: dict[str, list],
    command: str, source: str | None,
) -> None:
    checkout.write_text(f"project:\n  field_source: {source}\n" if source else "project: {}\n")
    args = engine.ProjectArguments(
        area="project", command=command, project_title="another-project", owner="someone-else",
        config_path=str(checkout),
    )
    assert engine.run_command(args) == 0
    assert f"Config: {checkout} (explicit --config)" in capsys.readouterr().out
    assert project_calls["creates"] == []


@pytest.mark.parametrize("target", [
    (command, legacy) for command in ("doctor", "configure")
    for legacy in (("Priority",), ("Size",), ("Priority", "Size"))
])
def test_commands_name_legacy_fields_and_never_write_them(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    project_calls: dict[str, list], target: tuple[str, tuple[str, ...]],
) -> None:
    command, legacy = target
    checkout.unlink()
    fields = schema_fields(legacy)
    # Archived fields can have old options; the guard must preserve them unchanged.
    fields = tuple(replace(field, options=()) if field.name.startswith("Legacy ") else field for field in fields)
    monkeypatch.setattr(engine, "fetch_project_fields", lambda _project: fields)
    assert engine.run_command(engine.ProjectArguments(
        area="project", command=command, project_title="base", owner="basefoundry"
    )) == 0
    output = capsys.readouterr().out
    for name in legacy:
        assert f"Using Legacy {name.lower()} for {name}" in output
    assert project_calls["creates"] == project_calls["updates"] == []


@pytest.mark.parametrize("selection", [
    "explicit", "discovered", "mismatch", "owner-mismatch", "no-file", "invalid", "invalid-explicit"
])
def test_rest_doctor_resolution_guard_and_validation(
    checkout: Path, capsys: pytest.CaptureFixture[str], selection: str,
) -> None:
    fields = schema_fields(("Priority", "Size"))
    reads: list[str] = []

    def find_project(owner: str, title: str) -> engine.OwnerInfo:
        reads.append(title)
        return engine.OwnerInfo("owner-id", owner, engine.ProjectInfo("project-id", title))

    transport = SimpleNamespace(find_owner_and_project=find_project, fetch_project_fields=lambda _project: fields)
    args = engine.ProjectArguments(
        area="project", command="doctor", owner="other" if selection == "owner-mismatch" else None,
        project_title="other" if selection == "mismatch" else "base",
        config_path=str(checkout) if selection in {"explicit", "invalid-explicit"} else None,
    )
    if selection.startswith("invalid"):
        checkout.write_text("project: [\n")
        with pytest.raises(engine.ProjectUsageError, match=str(checkout)):
            project_rest.rest_doctor_command(args, transport=transport, compare_schema=project_schema.compare_schema)
        assert not reads
        return
    if selection == "no-file":
        checkout.unlink()
    assert project_rest.rest_doctor_command(
        args, transport=transport, compare_schema=project_schema.compare_schema
    ) == 0
    output = capsys.readouterr().out
    if selection in {"explicit", "discovered"}:
        assert f"Config: {checkout}" in output
        assert selection in output
        assert "Using Legacy" not in output  # issue_fields schema excludes Priority/Size.
    else:
        assert "Config: no config" in output
        reason = {"mismatch": "Project title", "owner-mismatch": "Project owner"}.get(selection, "no file")
        assert reason in output
        assert "Using Legacy priority" in output
        assert "Using Legacy size" in output


def test_graphql_fallback_reuses_one_validated_resolution(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    reads: list[Path] = []
    read_config = project_config_resolution.read_project_config

    def record_read(path: Path) -> project_schema.ProjectConfig:
        reads.append(path)
        return read_config(path)

    def unavailable(*_args: object) -> None:
        raise engine.ProjectTransportError("unavailable")

    monkeypatch.setattr(project_config_resolution, "read_project_config", record_read)
    monkeypatch.setattr(engine, "find_owner_and_project", unavailable)
    monkeypatch.setattr(engine, "RestProjectTransport", lambda: SimpleNamespace(
        find_owner_and_project=lambda owner, title: engine.OwnerInfo(
            "owner-id", owner, engine.ProjectInfo("project-id", title)
        ), fetch_project_fields=lambda _project: schema_fields(),
    ))
    assert engine.doctor_command(engine.ProjectArguments(
        area="project", command="doctor", project_title="base", owner="basefoundry"
    )) == 0
    assert reads == [checkout]
    output = capsys.readouterr().out
    assert output.count("Config:") == 1
    assert "(REST fallback)" in output
