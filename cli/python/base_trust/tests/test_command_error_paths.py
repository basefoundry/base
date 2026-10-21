from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from base_cli.testing import invoke
from base_trust import engine


@pytest.mark.parametrize("output_format", ["yaml", "csv", "tsv"])
def test_project_status_supports_documented_output_formats(
    tmp_path: Path,
    manifest_factory,
    output_format: str,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "demo")

    result = invoke(
        engine.app,
        ["status", "demo", "--workspace", str(workspace), "--format", output_format],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    assert result.exit_code == 0, result.output
    if output_format == "yaml":
        payload = yaml.safe_load(result.stdout)
        assert payload["project"]["name"] == "demo"
        assert payload["status"] == "blocked"
    else:
        delimiter = "," if output_format == "csv" else "\t"
        assert result.stdout.splitlines() == [delimiter.join(("demo", "blocked", "not_allowed"))]


def test_workspace_status_supports_yaml_and_empty_terminal_output(
    tmp_path: Path,
    manifest_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "demo")
    yaml_result = invoke(
        engine.app,
        ["status", "--workspace", str(workspace), "--format", "yaml"],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    empty_workspace = tmp_path / "empty"
    empty_workspace.mkdir()
    monkeypatch.setattr(engine.base_cli, "is_terminal", lambda: True)
    text_result = invoke(
        engine.app,
        ["status", "--workspace", str(empty_workspace)],
        home=home,
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert yaml.safe_load(yaml_result.stdout)["projects"][0]["project"]["name"] == "demo"
    assert text_result.exit_code == 0, text_result.output
    assert text_result.stdout == (
        f"Workspace trust status: {empty_workspace.resolve()} (0 command-bearing projects)\n"
        "\nNo command-bearing projects require manifest command trust.\n"
        "Summary: 0 blocked, 0 allowed.\n"
    )


def test_workspace_status_text_shows_allowed_projects_compactly(
    tmp_path: Path,
    manifest_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifests = [
        manifest_factory.write(workspace / name, name=name)
        for name in ("zeta", "alpha")
    ]
    store = engine.ManifestCommandTrustStore(home=home)
    for manifest_path in manifests:
        store.allow(engine.compute_trust_identity_for_manifest(manifest_path), base_version="1.10.5")

    monkeypatch.setattr(engine.base_cli, "is_terminal", lambda: True)
    result = invoke(
        engine.app,
        ["status", "--workspace", str(workspace)],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    assert result.exit_code == 0, result.output
    assert f"Workspace trust status: {workspace.resolve()} (2 command-bearing projects)" in result.stdout
    assert "PROJECT  STATUS   REASON" in result.stdout
    assert "alpha    Allowed  Approved" in result.stdout
    assert "zeta     Allowed  Approved" in result.stdout
    assert "Summary: 0 blocked, 2 allowed." in result.stdout
    assert result.stdout.count("Trust scope:") == 1
    assert "Details: basectl trust status <project>" in result.stdout
    assert "SHA-256" not in result.stdout
    assert "Allow after review" not in result.stdout


def test_workspace_status_text_summarizes_blocked_reasons_before_allowed_projects(
    tmp_path: Path,
    manifest_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    allowed_manifest = manifest_factory.write(workspace / "allowed", name="allowed")
    changed_manifest = manifest_factory.write(workspace / "changed-manifest", name="changed-manifest")
    requirements_manifest = manifest_factory.write(workspace / "changed-requirements", name="changed-requirements")
    requirements_manifest.write_text(
        requirements_manifest.read_text(encoding="utf-8").replace(
            "  command: pytest tests/\n",
            "  command: pytest tests/\n  requirements: requirements-dev.txt\n",
        ),
        encoding="utf-8",
    )
    requirements_path = requirements_manifest.parent / "requirements-dev.txt"
    requirements_path.write_text("jsonschema==4.25.1\n", encoding="utf-8")

    store = engine.ManifestCommandTrustStore(home=home)
    store.allow(engine.compute_trust_identity_for_manifest(allowed_manifest), base_version="1.10.5")
    store.allow(engine.compute_trust_identity_for_manifest(changed_manifest), base_version="1.10.5")
    changed_manifest.write_text(
        changed_manifest.read_text(encoding="utf-8").replace("pytest tests/", "pytest -q"),
        encoding="utf-8",
    )
    store.allow(engine.compute_trust_identity_for_manifest(requirements_manifest), base_version="1.10.5")
    requirements_path.write_text("jsonschema==4.25.2\n", encoding="utf-8")
    manifest_factory.write(workspace / "fresh", name="fresh")

    monkeypatch.setattr(engine.base_cli, "is_terminal", lambda: True)
    result = invoke(
        engine.app,
        ["status", "--workspace", str(workspace)],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    assert result.exit_code == 0, result.output
    assert "changed-manifest      Blocked  Manifest changed" in result.stdout
    assert "changed-requirements  Blocked  Test requirements changed" in result.stdout
    assert "fresh                 Blocked  Not approved" in result.stdout
    assert "allowed               Allowed  Approved" in result.stdout
    assert result.stdout.index("changed-manifest      Blocked") < result.stdout.index("allowed               Allowed")
    assert "Summary: 3 blocked, 1 allowed." in result.stdout
    assert result.stdout.count("Trust scope:") == 1
    assert "Details: basectl trust status <project>" in result.stdout
    assert "SHA-256" not in result.stdout
    assert "Allow after review" not in result.stdout


def test_workspace_status_text_summarizes_all_blocked_projects(
    tmp_path: Path,
    manifest_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "zeta", name="zeta")
    manifest_factory.write(workspace / "alpha", name="alpha")

    monkeypatch.setattr(engine.base_cli, "is_terminal", lambda: True)
    result = invoke(
        engine.app,
        ["status", "--workspace", str(workspace)],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    assert result.exit_code == 0, result.output
    assert "alpha    Blocked  Not approved" in result.stdout
    assert "zeta     Blocked  Not approved" in result.stdout
    assert "Summary: 2 blocked, 0 allowed." in result.stdout
    assert result.stdout.count("Trust scope:") == 1


def test_invalid_status_format_is_a_usage_error(tmp_path: Path) -> None:
    result = invoke(
        engine.app,
        ["status", "--format", "toml"],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 2
    assert "Unsupported output format 'toml'" in result.stderr


@pytest.mark.parametrize("command", ["status", "require", "allow", "revoke"])
def test_project_commands_report_resolution_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    monkeypatch.setattr(
        engine,
        "resolve_trust_identity" if command != "require" else "resolve_trust_identity_for_require",
        lambda *args, **kwargs: (_ for _ in ()).throw(engine.TrustError("identity failed")),
    )

    result = invoke(
        engine.app,
        [command, "demo"],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 1
    assert "identity failed" in result.stderr


def test_workspace_status_reports_discovery_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        engine,
        "workspace_status_projects",
        lambda *args: (_ for _ in ()).throw(engine.TrustError("workspace failed")),
    )

    result = invoke(
        engine.app,
        ["status"],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 1
    assert "workspace failed" in result.stderr


def test_require_rejects_manifest_declaring_a_different_project(
    tmp_path: Path,
    manifest_factory,
) -> None:
    manifest_path = manifest_factory.write(tmp_path / "work" / "actual", name="actual")

    result = invoke(
        engine.app,
        ["require", "expected", "--manifest", str(manifest_path)],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 1
    assert "declares project 'actual', not 'expected'" in result.stderr


def test_active_project_name_mismatch_is_reported(
    tmp_path: Path,
    manifest_factory,
) -> None:
    manifest_path = manifest_factory.write(tmp_path / "active", name="actual")

    result = invoke(
        engine.app,
        ["status"],
        home=tmp_path / "home",
        env={
            "BASE_HOME": str(tmp_path / "base"),
            "BASE_TRUST_ACTIVE_PROJECT": "expected",
            "BASE_TRUST_ACTIVE_PROJECT_MANIFEST": str(manifest_path),
        },
    )

    assert result.exit_code == 1
    assert "Active project is 'expected' but its manifest declares project 'actual'" in result.stderr


def test_revoke_without_record_reports_noop(
    tmp_path: Path,
    manifest_factory,
) -> None:
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "demo")

    result = invoke(
        engine.app,
        ["revoke", "demo", "--workspace", str(workspace)],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 0, result.output
    assert result.stdout == "No manifest command trust record found for project 'demo'.\n"


def test_status_payload_ignores_malformed_changed_record(tmp_path: Path, manifest_factory) -> None:
    manifest_path = manifest_factory.write(tmp_path / "demo")
    identity = engine.compute_trust_identity_for_manifest(manifest_path)
    status = engine.TrustStatus(
        status="blocked",
        reason="manifest_changed",
        identity=identity,
        record=None,
        changed_record={"project": {"manifest_sha256": 42}},
    )

    payload = engine.status_payload(status)

    assert "recorded_manifest_sha256" not in payload
    assert json.loads(json.dumps(payload))["reason"] == "manifest_changed"
