"""Reconcile actual Git layouts with Base manifests before reports are persisted."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from base_projects.tests.test_workspace_checks import invoke_engine, write_default_manifest


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, text=True)


def create_git_repository(root: Path, *, linked_worktree: bool = False) -> None:
    if linked_worktree:
        donor = root.parent.parent / "worktree-source"
        git("init", "--quiet", str(donor))
        git(
            "-C", str(donor), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "commit", "--allow-empty", "--quiet", "-m", "Fixture commit",
        )
        git("-C", str(donor), "worktree", "add", "--detach", str(root), "HEAD")
    else:
        git("init", "--quiet", str(root))
    git("-C", str(root), "remote", "add", "origin", "https://example.invalid/fixture.git")


@pytest.mark.parametrize("linked_worktree", [False, True], ids=["git-directory", "git-file"])
@pytest.mark.parametrize("report", ["check", "doctor"])
@pytest.mark.parametrize("output_format", ["json", "text"])
def test_mixed_inventory_reports_once_and_preserves_saved_identity(
    tmp_path, manifest_factory, linked_worktree, report, output_format,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    base_home = tmp_path / "base"
    write_default_manifest(base_home)
    manifest = tmp_path / "workspace.yaml"
    manifest.write_text(
        "schema_version: 1\nworkspace:\n  name: inventory\nrepos:\n  - name: declared\n",
        encoding="utf-8",
    )
    declared = workspace / "declared"
    create_git_repository(declared)
    manifest_factory.write_shell(declared, "declared")
    extra = workspace / "extra"
    create_git_repository(extra, linked_worktree=linked_worktree)
    extra_manifest = manifest_factory.write_shell(extra, "extra")
    create_git_repository(workspace / "unmanaged")
    git("init", "--quiet", "--bare", str(workspace / "bare"))

    status, stdout, stderr = invoke_engine(
        [report, "--workspace", str(workspace), "--manifest", str(manifest), "--format", output_format],
        base_home, home,
    )
    assert status == 0, stdout + stderr
    if output_format == "json":
        assert not stderr
        payload = json.loads(stdout)
        assert payload["repository_count"] == 4
        assert payload["project_count"] == 2
        items = payload["projects"]
        assert [item["repository"] for item in items] == ["declared", "extra", "bare", "unmanaged"]
        extra_result = items[1]
        assert extra_result["manifest"] == "valid"
        assert extra_result["path"] == str(extra.resolve())
        assert extra_result["checks"][0]["id"] == "BASE-W011"
        assert "BASE-W013" not in {check["id"] for check in extra_result["checks"]}
        for item in items[2:]:
            assert item["manifest"] == "missing"
            assert [check["id"] for check in item["checks"]] == ["BASE-W013"]
    else:
        output = stdout + stderr
        assert "(4 repositories)" in output
        for name in ("declared", "extra", "bare", "unmanaged"):
            assert output.count(f"Repository: {name} [") == 1

    if report == "check":
        record = json.loads((home / ".base.d/extra/checks/last.json").read_text(encoding="utf-8"))
        assert record["schema_version"] == 2
        assert record["identity"] == {
            "project_root": str(extra.resolve()),
            "manifest_path": str(extra_manifest.resolve()),
            "manifest_sha256": hashlib.sha256(extra_manifest.read_bytes()).hexdigest(),
        }
