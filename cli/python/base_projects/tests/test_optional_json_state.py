from __future__ import annotations

import copy
import json

import pytest

from base_projects import project_discovery as discovery
from base_projects.workspace_report_common import project_last_check
from base_projects.workspace_scanner import workspace_manifest_entries, ProjectDiscoveryError
from base_projects.tests.test_workspace_checks import invoke_engine, write_default_manifest
from base_setup.tests.helpers import fake_context


INVALID_JSON = [b"[]", b"null", b"42", b'"value"', b"false", b"{", b"\xff"]


@pytest.fixture(name="local_state")
def local_state_fixture(tmp_path, monkeypatch):
    home, base, workspace = tmp_path / "home", tmp_path / "base", tmp_path / "workspace"
    home.mkdir()
    write_default_manifest(base)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("BASE_CACHE_DIR", str(tmp_path / "cache"))
    project = workspace / "demo"
    project.mkdir(parents=True)
    (project / "base_manifest.yaml").write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
    entries = workspace_manifest_entries(workspace)
    ctx = fake_context()
    projects = (discovery.read_project(entries[0].path),)
    discovery.write_project_cache(workspace, entries, projects, ctx)
    cache = discovery.project_cache_path(workspace)
    record = home / ".base.d" / "demo" / "checks" / "last.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({
        "schema_version": 1, "project": "demo", "checked_at": "2026-09-12T10:00:00Z", "status": "ok",
    }), encoding="utf-8")
    return home, base, workspace, entries, cache, record


@pytest.mark.parametrize("raw", INVALID_JSON)
def test_optional_nonobject_and_unreadable_json_is_unavailable(local_state, raw):
    _home, _base, workspace, entries, cache, record = local_state
    cache.write_bytes(raw)
    record.write_bytes(raw)

    assert discovery.read_project_cache(workspace, entries) is None
    assert project_last_check("demo") is None


@pytest.mark.parametrize("field,value", [
    ("projects", None), ("projects", {}), ("projects", []), ("projects", [None]),
    ("projects", [{"name": [], "root": "/tmp", "manifest_path": "/tmp/base_manifest.yaml"}]),
    ("version", True),
])
def test_invalid_cache_members_fall_back(local_state, field, value):
    _home, _base, workspace, entries, cache, _record = local_state
    payload = json.loads(cache.read_text(encoding="utf-8"))
    payload[field] = value
    cache.write_text(json.dumps(payload), encoding="utf-8")

    assert discovery.read_project_cache(workspace, entries) is None


@pytest.mark.parametrize("field,value", [
    ("name", {}), ("name", ""), ("name", "../demo"), ("root", 42),
    ("root", ""), ("manifest_path", ""), ("manifest_path", "\0"),
])
def test_invalid_cached_project_fields_fall_back(local_state, field, value):
    _home, _base, workspace, entries, cache, _record = local_state
    payload = json.loads(cache.read_text(encoding="utf-8"))
    payload["projects"][0][field] = value
    cache.write_text(json.dumps(payload), encoding="utf-8")

    assert discovery.read_project_cache(workspace, entries) is None


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("project", []), ("checked_at", []), ("checked_at", ""),
    ("checked_at", "not-a-date"), ("checked_at", "2026-09-12"),
    ("status", []), ("status", ""), ("status", "success"),
])
def test_invalid_latest_check_members_are_unavailable(local_state, field, value):
    _home, _base, _workspace, _entries, _cache, record = local_state
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload[field] = value
    record.write_text(json.dumps(payload), encoding="utf-8")

    assert project_last_check("demo") is None


def test_duplicate_cache_records_trigger_fresh_discovery(local_state):
    _home, _base, workspace, _entries, cache, _record = local_state
    payload = json.loads(cache.read_text(encoding="utf-8"))
    payload["projects"].append(copy.deepcopy(payload["projects"][0]))
    cache.write_text(json.dumps(payload), encoding="utf-8")

    projects = discovery.discover_projects_cached(fake_context(), workspace)

    assert [project.name for project in projects] == ["demo"]


@pytest.mark.parametrize("raw", INVALID_JSON)
def test_public_listing_and_status_survive_invalid_optional_state(local_state, raw):
    home, base, workspace, _entries, cache, record = local_state
    cache.write_bytes(raw)
    record.write_bytes(raw)

    result, stdout, stderr = invoke_engine(["list", "--workspace", str(workspace), "--format", "json"], base, home)
    assert result == 0
    assert json.loads(stdout)[0]["name"] == "demo"
    assert "Traceback" not in stderr
    result, stdout, stderr = invoke_engine(["status", "--workspace", str(workspace), "--format", "json"], base, home)
    assert result == 0
    report = json.loads(stdout)
    assert report["projects"][0]["status"] == "ok"
    assert report["projects"][0]["last_check"] is None
    assert "Traceback" not in stderr


def test_invalid_cache_does_not_hide_manifest_errors(local_state):
    _home, _base, workspace, entries, cache, _record = local_state
    cache.write_text("[]", encoding="utf-8")
    entries[0].path.write_text("project: {}\n", encoding="utf-8")

    with pytest.raises(ProjectDiscoveryError, match="project.name"):
        discovery.discover_projects_cached(fake_context(), workspace)


def test_valid_optional_records_retain_existing_behavior(local_state):
    _home, _base, workspace, entries, _cache, _record = local_state

    projects = discovery.read_project_cache(workspace, entries)
    assert projects is not None
    assert [project.name for project in projects] == ["demo"]
    last_check = project_last_check("demo")
    assert last_check is not None
    assert last_check.status == "ok"
    assert last_check.checked_at == "2026-09-12T10:00:00Z"
