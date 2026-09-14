"""Every read-only workspace consumer must share logical names and containment."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from base_projects.tests.test_workspace_checks import invoke_engine
from base_projects.tests.test_workspace_checks import write_default_manifest, write_shell_manifest


REPORTS = ("status", "check", "doctor", "onboarding", "agent-brief")


def workspace_fixture(tmp_path, *, target_kind, required=True):
    workspace = tmp_path / "team's workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    base_home = tmp_path / "base"
    write_default_manifest(base_home)
    if target_kind == "outside":
        physical = tmp_path / "outside-private-project"
    elif target_kind == "nested":
        physical = workspace / "storage" / "physical"
    else:
        physical = workspace / "physical"
    write_shell_manifest(physical, "api")
    (physical / ".git").mkdir()
    alias = workspace / "api"
    alias.symlink_to(physical, target_is_directory=True)
    manifest = tmp_path / "workspace.yaml"
    manifest.write_text(
        "schema_version: 1\nworkspace:\n  name: boundary-suite\nrepos:\n"
        f"  - name: api\n    required: {str(required).lower()}\n"
        "    url: https://example.invalid/api.git\n",
        encoding="utf-8",
    )
    return workspace, home, base_home, manifest, physical, alias


def report_args(report, workspace, manifest, output_format):
    return [report, "--workspace", str(workspace), "--manifest", str(manifest), "--format", output_format]


def payload_items(payload, report):
    return payload["projects" if report in {"status", "check", "doctor"} else "repositories"]


@pytest.mark.parametrize("report", REPORTS)
@pytest.mark.parametrize("output_format", ["json", "text"])
@pytest.mark.parametrize("target_kind", ["direct", "nested"])
def test_in_root_alias_is_one_logically_named_repository(tmp_path, report, output_format, target_kind):
    workspace, home, base_home, manifest, physical, _ = workspace_fixture(tmp_path, target_kind=target_kind)
    status, stdout, stderr = invoke_engine(report_args(report, workspace, manifest, output_format), base_home, home)
    assert status == 0, stderr + stdout
    assert not stderr
    if output_format == "json":
        payload = json.loads(stdout)
        items = payload_items(payload, report)
        assert payload["repository_count"] == 1
        assert [item["repository"] for item in items] == ["api"]
        assert items[0]["manifest"] == "valid"
        assert items[0]["path"] == str(physical.resolve())
    elif report in {"check", "doctor"}:
        assert stdout.count("Repository: api [") == 1
        assert "Repository: physical [" not in stdout
        assert "(1 repositories)" in stdout
    else:
        rows = [line.split() for line in stdout.splitlines() if line.startswith(("api ", "physical "))]
        assert [row[0] for row in rows] == ["api"]


def forbid_outside_inspection(monkeypatch, outside):
    """Catch manifest reads and the agent-brief's otherwise silent file probes."""
    outside = outside.resolve()
    for method in ("read_bytes", "read_text", "is_file"):
        original = getattr(Path, method)

        def guarded(path, *args, _original=original, **kwargs):
            assert not path.resolve().is_relative_to(outside), f"inspected outside repository: {path}"
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(Path, method, guarded)


@pytest.mark.parametrize("report", REPORTS)
@pytest.mark.parametrize("output_format", ["json", "text"])
@pytest.mark.parametrize("required", [True, False])
def test_outside_alias_is_invalid_without_inspection_or_unsafe_guidance(
    tmp_path, monkeypatch, report, output_format, required,
):
    workspace, home, base_home, manifest, outside, alias = workspace_fixture(
        tmp_path, target_kind="outside", required=required,
    )
    forbid_outside_inspection(monkeypatch, outside)
    args = report_args(report, workspace, manifest, output_format)
    if report in {"check", "doctor"}:
        args.append("--verify-project-runtime")
    status, stdout, stderr = invoke_engine(args, base_home, home)
    # Onboarding and handoff remain report-only, including for unhealthy repos.
    assert status == (1 if report in {"status", "check", "doctor"} else 0), stderr + stdout
    if output_format == "json" or report != "doctor":
        assert not stderr
    combined = stdout + stderr
    assert str(outside) not in combined
    if output_format == "json":
        payload = json.loads(stdout)
        items = payload_items(payload, report)
        assert payload["repository_count"] == 1
        assert [item["repository"] for item in items] == ["api"]
        item = items[0]
        assert item["path"] == str(alias)
        assert item["manifest"] == "unknown"
        assert item["manifest_path"] is None
        if report in {"status", "check", "doctor"}:
            assert item["repo"] == "invalid"
            assert item["status"] == "error"
            if report != "status":
                assert [check["id"] for check in item["checks"]] == ["BASE-W014"]
        elif report == "onboarding":
            assert item["status"] == "invalid_path"
            assert item["discovery_status"] == "invalid"
            assert "outside workspace root" in item["next_action"]
            for key in ("setup_command", "validation_command", "test_command", "clone_command", "trust_command"):
                assert item[key] is None
        else:
            assert item["handoff_status"] == "invalid_path"
            assert item["discovery_status"] == "invalid"
            assert not item["base_managed"]
            assert "outside workspace root" in " ".join(item["next_actions"])
            assert all(signal["status"] == "unavailable" for signal in item["signals"].values())
            schema = Path(__file__).resolve().parents[4] / "docs/schemas/workspace-agent-brief.json"
            Draft202012Validator(json.loads(schema.read_text(encoding="utf-8"))).validate(payload)
    elif report == "status":
        assert any(line.startswith("api ") and "invalid" in line.split() for line in stdout.splitlines())
    else:
        assert "outside workspace root" in combined
        assert "git clone " not in combined
        assert "&& basectl setup" not in combined
        if report in {"onboarding", "agent-brief"}:
            assert any("invalid_path" in line.split() for line in stdout.splitlines())


@pytest.mark.parametrize("report", REPORTS)
def test_undeclared_outside_alias_is_not_an_extra(tmp_path, monkeypatch, report):
    workspace, home, base_home, manifest, _, _ = workspace_fixture(tmp_path, target_kind="nested")
    outside = tmp_path / "outside-extra"
    write_shell_manifest(outside, "private-extra")
    (workspace / "outside-alias").symlink_to(outside, target_is_directory=True)
    forbid_outside_inspection(monkeypatch, outside)
    status, stdout, stderr = invoke_engine(report_args(report, workspace, manifest, "json"), base_home, home)
    assert status == 0, stderr + stdout
    assert [item["repository"] for item in payload_items(json.loads(stdout), report)] == ["api"]


@pytest.mark.parametrize("report", REPORTS)
def test_explicitly_declared_aliases_remain_distinct_inventory_entries(tmp_path, report):
    workspace, home, base_home, manifest, _, _ = workspace_fixture(tmp_path, target_kind="direct")
    manifest.write_text(manifest.read_text(encoding="utf-8") + "  - name: physical\n", encoding="utf-8")
    status, stdout, stderr = invoke_engine(report_args(report, workspace, manifest, "json"), base_home, home)
    assert status == 0, stderr + stdout
    assert [item["repository"] for item in payload_items(json.loads(stdout), report)] == ["api", "physical"]
