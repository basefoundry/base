from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

from base_version.report import bash_component, build_report, component, git_identity, main, python_component, render_component, render_text


def source(tmp_path, name, layout, version="7.8.9"):
    root = tmp_path / name
    path = root / layout
    path.mkdir(parents=True)
    (root / "VERSION").write_text(version)
    return root, path


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def test_source_version_does_not_use_installed_metadata(tmp_path):
    root, path = source(tmp_path, "base-cli", "lib/python")
    (path / "base_cli").mkdir()
    # Inspection must not execute this provider.
    (path / "base_cli/__init__.py").write_text("raise RuntimeError('broken provider')")
    item = python_component(tmp_path, "/missing/python", "explicit", str(path), "")
    assert item["version"] == "7.8.9"
    assert item["status"] == "available"
    (root / "VERSION").unlink()
    item = python_component(tmp_path, sys.executable, "explicit", str(path), "")
    assert item["version"] is None
    assert item["status"] == "unknown"


def test_missing_providers_give_partial_json(tmp_path):
    report = build_report([
        str(tmp_path), "1.2.3", "json", "/missing/python", "pip", "", "", "unavailable", "", "not found",
    ])
    assert report["status"] == "warn"
    assert report["error"] is None
    assert [item["status"] for item in report["data"]["components"]] == ["available", "unavailable", "unavailable"]
    assert json.loads(json.dumps(report)) == report
    assert "base: 1.2.3" in render_text(report)


def test_render_component_includes_revision_and_dirty_state():
    item = component("base", "checkout", "/tmp/base", "1.2.3")
    item.update(revision="abcdef1234567890", dirty=True)

    assert "base: 1.2.3 (git abcdef123456, dirty)" in render_component(item)


def test_git_identity_swallows_subprocess_failures(tmp_path, monkeypatch):
    monkeypatch.setattr("base_version.report.git_checkout_marker", lambda _root: True)
    with mock.patch(
        "base_version.report.subprocess.run",
        side_effect=subprocess.TimeoutExpired(["git"], 5),
    ):
        assert git_identity(tmp_path) == {"revision": None, "dirty": None}


def test_git_revision_dirty_and_no_parent_leak(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    (tmp_path / "VERSION").write_text("1.0.0")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "fixture")
    assert git_identity(tmp_path) == {"revision": git(tmp_path, "rev-parse", "HEAD"), "dirty": False}
    nested = tmp_path / "nested"
    nested.mkdir()
    assert git_identity(nested) == {"revision": None, "dirty": None}
    (nested / "untracked").touch()
    assert git_identity(tmp_path)["dirty"] is True


def test_bash_embedded_metadata_and_symlink(tmp_path):
    root, path = source(tmp_path, "libs", "lib/bash/std")
    (path / "lib_std.sh").write_text("exit 99")
    (root / "VERSION").unlink()
    (path.parent / "base-bash-libs.release").write_text("version=2.1.0\ncommit=" + "a" * 40 + "\ndirty_state=clean\n")
    link = tmp_path / "linked"
    link.symlink_to(path.parent, target_is_directory=True)
    item = bash_component("homebrew", str(link), "")
    assert item["version"] == "2.1.0"
    assert item["revision"] == "a" * 40
    assert item["dirty"] is False
    assert item["path"] == str(path.parent)


def test_invalid_override_is_not_replaced(tmp_path):
    item = python_component(tmp_path, sys.executable, "unavailable", "", "invalid explicit root")
    assert item["status"] == "unavailable"
    assert item["detail"] == "invalid explicit root"
    assert item["version"] is None


def test_python_component_reports_uninspectable_selected_python(tmp_path):
    with mock.patch(
        "base_version.report.subprocess.run",
        return_value=subprocess.CompletedProcess(["python"], 7, "", ""),
    ):
        item = python_component(tmp_path, "/missing/python", "pip", "", "")

    assert item["status"] == "unavailable"
    assert item["detail"] == "Selected Python could not inspect base-cli."


def test_python_component_reports_unrecognized_source_layout(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    item = python_component(tmp_path, sys.executable, "explicit", str(source_root), "")

    assert item["status"] == "unknown"
    assert item["detail"] == "Selected source has no recognized package metadata layout."


def test_installed_probe_uses_selected_environment_without_import(tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    python = venv / "bin/python"
    site = Path(subprocess.check_output(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True,
    ).strip())
    (site / "base_cli").mkdir()
    (site / "base_cli/__init__.py").write_text("raise RuntimeError('must not import')")
    metadata = site / "base_cli-9.8.7.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: base-cli\nVersion: 9.8.7\n")
    item = python_component(tmp_path, str(python), "pip", "", "")
    assert item["version"] == "9.8.7"
    assert item["path"] == str(site / "base_cli/__init__.py")
    assert item["status"] == "available"
    # A .pth source override in the selected interpreter must not inherit wheel metadata.
    _, path = source(tmp_path, "editable", "lib/python", "3.2.1")
    (path / "base_cli").mkdir()
    (path / "base_cli/__init__.py").write_text("raise RuntimeError('must not import')")
    (site / "override.pth").write_text(f"import sys; sys.path.insert(0, {str(path)!r})\n")
    item = python_component(tmp_path, str(python), "pip", "", "")
    assert item["version"] == "3.2.1"
    assert item["source"] == "installed-editable"


def test_git_absent_preserves_version(tmp_path, monkeypatch):
    _, path = source(tmp_path, "libs", "lib/bash/std")
    (path / "lib_std.sh").touch()
    monkeypatch.setenv("PATH", "/nonexistent")
    assert bash_component("explicit", str(path.parent), "")["version"] == "7.8.9"


def test_empty_version_does_not_claim_embedded_release(tmp_path):
    _, path = source(tmp_path, "libs", "lib/bash/std", "\n9.9.9")
    (path / "lib_std.sh").touch()
    (path.parent / "base-bash-libs.release").write_text("version=2.1.0\n")
    item = bash_component("explicit", str(path.parent), "")
    assert item["version"] is None
    assert item["status"] == "unknown"


def test_bash_component_reports_short_provider_layout(tmp_path):
    item = bash_component("explicit", "/", "")

    assert item["status"] == "unknown"
    assert item["detail"] == "Selected stdlib has no package root metadata layout."


def test_bash_component_strips_error_prefix():
    item = bash_component("unavailable", "", "ERROR: first\nERROR: second")

    assert item["detail"] == "first\nsecond"


def test_bash_summary_fits_the_single_line_check_protocol(tmp_path, capsys):
    _, path = source(tmp_path, "libs", "lib/bash/std")
    (path / "lib_std.sh").touch()
    assert main(["--bash-summary", "explicit", str(path.parent)]) == 0
    assert capsys.readouterr().out == "base-bash-libs: 7.8.9\n"
