from __future__ import annotations

import json

import pytest

from base_projects.workspace_manifest import WorkspaceManifestError, read_workspace_manifest
from base_projects.tests.test_workspace_checks import invoke_engine, write_default_manifest
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError, read_manifest_mapping


PROJECT = "project:\n  name: demo\nartifacts: []\n"
WORKSPACE = "schema_version: 1\nworkspace:\n  name: demo\nrepos: []\n"


@pytest.mark.parametrize("content,location", [
    (PROJECT + "42: true\n", "manifest"),
    (PROJECT + "false: true\n", "manifest"),
    (PROJECT + "unknown: true\n42: true\n", "manifest"),
    ("project:\n  name: demo\n  42: value\n", "manifest.project"),
    (PROJECT + "commands:\n  false:\n    command: 'true'\n", "manifest.commands"),
    (PROJECT + "health:\n  ports:\n    - 42: value\n", "manifest.health.ports[0]"),
])
def test_project_non_string_keys_raise_domain_error(tmp_path, content, location):
    manifest = tmp_path / "base_manifest.yaml"
    manifest.write_text(content, encoding="utf-8")

    with pytest.raises(ManifestError, match="mapping keys must be strings") as error:
        read_manifest(manifest)

    assert str(manifest) in str(error.value)
    assert location in str(error.value)


@pytest.mark.parametrize("content,location", [
    (WORKSPACE + "42: true\n", "manifest"),
    (WORKSPACE + "false: true\n", "manifest"),
    (WORKSPACE + "unknown: true\n42: true\n", "manifest"),
    ("schema_version: 1\nworkspace:\n  name: demo\n  42: true\nrepos: []\n", "manifest.workspace"),
    ("schema_version: 1\nworkspace:\n  name: demo\nrepos:\n  - name: demo\n    42: true\n", "manifest.repos[0]"),
])
def test_workspace_non_string_keys_raise_domain_error(tmp_path, content, location):
    manifest = tmp_path / "workspace.yaml"
    manifest.write_text(content, encoding="utf-8")

    with pytest.raises(WorkspaceManifestError, match="mapping keys must be strings") as error:
        read_workspace_manifest(manifest)

    assert str(manifest) in str(error.value)
    assert location in str(error.value)


@pytest.mark.parametrize("loader,error_type", [
    (read_manifest, ManifestError), (read_workspace_manifest, WorkspaceManifestError),
])
def test_invalid_utf8_raises_domain_error(tmp_path, loader, error_type):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_bytes(b"name: \xff\n")

    with pytest.raises(error_type, match="UTF-8") as error:
        loader(manifest)

    assert str(manifest) in str(error.value)


@pytest.mark.parametrize("bad_content", [b"42: true\n", b"name: \xff\n"])
@pytest.mark.parametrize("command", ["status", "check", "doctor"])
def test_workspace_reports_bad_member_and_continues(tmp_path, bad_content, command):
    home = tmp_path / "home"
    base = tmp_path / "base"
    workspace = tmp_path / "workspace"
    home.mkdir()
    write_default_manifest(base)
    for name, content in (("bad", bad_content), ("good", PROJECT.replace("demo", "good").encode())):
        project = workspace / name
        project.mkdir(parents=True)
        (project / "base_manifest.yaml").write_bytes(content)

    result, stdout, stderr = invoke_engine([command, "--workspace", str(workspace), "--format", "json"], base, home)

    assert result == 1
    assert "Traceback" not in stderr
    report = json.loads(stdout)
    assert '"good"' in json.dumps(report)
    assert '"bad"' in json.dumps(report)
    assert "mapping keys" in stdout or "UTF-8" in stdout


def test_workspace_cli_returns_controlled_error_for_bad_encoding(tmp_path):
    manifest = tmp_path / "workspace.yaml"
    manifest.write_bytes(b"\xff")
    home, base = tmp_path / "home", tmp_path / "base"
    home.mkdir()
    write_default_manifest(base)

    result, _stdout, stderr = invoke_engine(
        ["status", "--manifest", str(manifest), "--workspace", str(tmp_path)], base, home,
    )

    assert result == 1
    assert "UTF-8" in stderr
    assert "Traceback" not in stderr


def test_mapping_key_validation_handles_shared_and_cyclic_yaml_aliases(tmp_path):
    manifest = tmp_path / "base_manifest.yaml"
    manifest.write_text("project: &project\n  name: demo\n  self: *project\n", encoding="utf-8")

    mapping = read_manifest_mapping(manifest)

    assert mapping["project"]["self"] is mapping["project"]
    manifest.write_text("project: &project\n  name: demo\n  self: *project\n  42: true\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="manifest.project mapping keys"):
        read_manifest_mapping(manifest)
