from __future__ import annotations

import json

import pytest

from base_projects.workspace_checks import WorkspaceProjectCheckResult, persist_workspace_check_records
from base_projects.workspace_scanner import workspace_manifest_entries
from base_projects.workspace_statuses import workspace_project_status


@pytest.fixture(name="check_projects")
def check_projects_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    roots = (tmp_path / "first" / "shared", tmp_path / "second" / "shared")
    for root in roots:
        root.mkdir(parents=True)
        (root / "base_manifest.yaml").write_text("project:\n  name: shared\nartifacts: []\n", encoding="utf-8")
    entries = tuple(workspace_manifest_entries(root.parent)[0] for root in roots)
    record = tmp_path / "home" / ".base.d" / "shared" / "checks" / "last.json"
    return roots, entries, record


def persist_result(root):
    result = WorkspaceProjectCheckResult(
        name="shared", root=root.resolve(), manifest_path=(root / "base_manifest.yaml").resolve(),
        manifest="valid", status="ok", checks=(),
    )
    assert not persist_workspace_check_records((result,))


def test_saved_check_is_only_available_for_its_checkout(check_projects):
    roots, entries, _record = check_projects
    persist_result(roots[0])

    assert workspace_project_status(entries[0]).last_check is not None
    assert workspace_project_status(entries[1]).last_check is None


def test_manifest_change_invalidates_saved_check(check_projects):
    roots, entries, _record = check_projects
    persist_result(roots[0])
    with (roots[0] / "base_manifest.yaml").open("a", encoding="utf-8") as stream:
        stream.write("# A changed manifest needs a new check.\n")

    assert workspace_project_status(entries[0]).last_check is None


def test_legacy_check_is_unavailable_until_a_new_check(check_projects):
    roots, entries, record = check_projects
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({
        "schema_version": 1, "project": "shared", "status": "ok", "checked_at": "2026-09-12T10:00:00Z",
    }), encoding="utf-8")

    assert workspace_project_status(entries[0]).last_check is None
    persist_result(roots[0])
    assert workspace_project_status(entries[0]).last_check is not None


def test_canonical_checkout_alias_matches_saved_check(check_projects, tmp_path):
    roots, entries, record = check_projects
    alias = tmp_path / "alias"
    alias.symlink_to(roots[0], target_is_directory=True)
    persist_result(alias)

    assert workspace_project_status(entries[0]).last_check is not None
    identity = json.loads(record.read_text(encoding="utf-8"))["identity"]
    assert identity["project_root"] == str(roots[0].resolve())
    assert identity["manifest_path"] == str(entries[0].path.resolve())


@pytest.mark.parametrize("identity", [None, [], {}, {"project_root": []}, {"manifest_sha256": "invalid"}])
def test_malformed_check_identity_is_unavailable(check_projects, identity):
    roots, entries, record = check_projects
    persist_result(roots[0])
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["identity"] = identity
    record.write_text(json.dumps(payload), encoding="utf-8")

    assert workspace_project_status(entries[0]).last_check is None
