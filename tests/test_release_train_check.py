from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

# pylint: disable=wrong-import-position
import release_train_check as checker


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "release_train_check.py"


def valid_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "candidate": {
            "repository": "basefoundry/base",
            "target_version": "1.10.1",
            "current_version": "1.10.0",
            "milestone": "v1.10.1",
        },
        "participants": [
            {
                "repository": "basefoundry/base-cli",
                "version": "0.5.1",
                "milestone": "v0.5.1",
                "resolved_ref": "a" * 40,
            }
        ],
        "gates": {
            "empty_milestones": True,
            "immutable_releases": True,
            "public_readback": True,
            "release_bom": {
                "workflow": "ecosystem-release-bom.yml",
                "platforms": ["ubuntu-24.04", "macos-14"],
                "inputs": {"base_version": "1.10.1", "base_cli_version": "0.5.1"},
            },
        },
    }


def create_fixture(tmp_path: Path) -> Path:
    (tmp_path / ".ai-context").mkdir()
    (tmp_path / "VERSION").write_text("1.10.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "![Version](https://img.shields.io/badge/version-1.10.0-blue)\n"
        "Base `1.10.0` is the current release.\n",
        encoding="utf-8",
    )
    (tmp_path / ".ai-context" / "PROJECT.md").write_text("Current release: `1.10.0`\n", encoding="utf-8")
    (tmp_path / ".ai-context" / "STATUS.md").write_text("Base `1.10.0` is the current release.\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("## [Unreleased]\n\n## [1.10.0]\n", encoding="utf-8")
    (tmp_path / "requirements-dev.txt").write_text("base-cli==0.5.1\n", encoding="utf-8")
    (tmp_path / ".release").mkdir()
    (tmp_path / ".release" / "version-consistency.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "authority": {"path": "VERSION"},
                "surfaces": [
                    {
                        "name": "readme",
                        "path": "README.md",
                        "must_contain": ["version-{version}-blue", "Base `{version}` is the current release."],
                    },
                    {
                        "name": "project",
                        "path": ".ai-context/PROJECT.md",
                        "must_contain": ["Current release: `{version}`"],
                    },
                    {
                        "name": "status",
                        "path": ".ai-context/STATUS.md",
                        "must_contain": ["Base `{version}` is the current release."],
                    },
                    {"name": "changelog", "path": "CHANGELOG.md", "must_contain": ["## [{version}]"]},
                ],
                "exceptions": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ecosystem-release-bom.yml").write_text(
        "on:\n  workflow_dispatch:\n    inputs:\n      base_version:\n        default: \"1.10.1\"\n      base_cli_version:\n        default: \"0.5.1\"\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "train.json"
    manifest.write_text(json.dumps(valid_manifest()), encoding="utf-8")
    return manifest


def run_checker(
    root: Path, manifest: Path, *, release_prep: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), "--root", str(root), "--manifest", str(manifest), "--no-git"]
    if release_prep:
        command.append("--release-prep")
    command.append("--format")
    command.append("json")
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def test_planning_manifest_passes_local_preflight(tmp_path: Path) -> None:
    manifest = create_fixture(tmp_path)
    result = run_checker(tmp_path, manifest)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "ok"


def test_short_component_ref_is_a_blocker(tmp_path: Path) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["participants"][0]["resolved_ref"] = "short"
    manifest.write_text(json.dumps(data), encoding="utf-8")

    result = run_checker(tmp_path, manifest)

    assert result.returncode == 1
    assert "resolved_ref must be a full lowercase 40-character SHA" in result.stdout


def test_missing_candidate_repository_returns_structured_json_error(tmp_path: Path) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    del data["candidate"]["repository"]
    manifest.write_text(json.dumps(data), encoding="utf-8")

    result = run_checker(tmp_path, manifest)

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["status"] == "error"
    assert any(item["name"] == "candidate_repository" for item in payload["findings"])
    assert "Traceback" not in result.stderr


def test_missing_candidate_milestone_returns_structured_json_error(tmp_path: Path) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    del data["candidate"]["milestone"]
    manifest.write_text(json.dumps(data), encoding="utf-8")

    result = run_checker(tmp_path, manifest)

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["status"] == "error"
    assert any(item["name"] == "candidate_milestone" for item in payload["findings"])
    assert "Traceback" not in result.stderr


def test_release_prep_requires_target_version_surfaces(tmp_path: Path) -> None:
    manifest = create_fixture(tmp_path)
    for path in (
        tmp_path / "VERSION",
        tmp_path / "README.md",
        tmp_path / ".ai-context" / "PROJECT.md",
        tmp_path / ".ai-context" / "STATUS.md",
        tmp_path / "CHANGELOG.md",
    ):
        path.write_text(path.read_text(encoding="utf-8").replace("1.10.0", "1.10.1"), encoding="utf-8")

    result = run_checker(tmp_path, manifest, release_prep=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "ok"


def test_release_train_rejects_base_cli_requirement_drift(tmp_path: Path) -> None:
    manifest = create_fixture(tmp_path)
    (tmp_path / "requirements-dev.txt").write_text("base-cli==0.5.0\n", encoding="utf-8")

    result = run_checker(tmp_path, manifest)

    assert result.returncode == 1
    assert "release-train BOM expects 0.5.1" in result.stdout


def remote_api(*, immutable: bool = True, tag_sha: str = "a" * 40):
    def fake(path: str):
        if path == "repos/basefoundry/base/milestones?state=all&per_page=100":
            return [{"title": "v1.10.1", "open_issues": 0}], None
        if path == "repos/basefoundry/base-cli/milestones?state=all&per_page=100":
            return [{"title": "v0.5.1", "open_issues": 0}], None
        if path == "repos/basefoundry/base-cli/immutable-releases":
            return {"enabled": True}, None
        if path == "repos/basefoundry/base-cli/releases/tags/v0.5.1":
            return {"draft": False, "prerelease": False, "immutable": immutable}, None
        if path == "repos/basefoundry/base-cli/git/ref/tags/v0.5.1":
            return {"object": {"type": "tag", "sha": "b" * 40}}, None
        if path == f"repos/basefoundry/base-cli/git/tags/{'b' * 40}":
            return {"object": {"type": "commit", "sha": tag_sha}}, None
        raise AssertionError(f"unexpected gh api path: {path}")

    return fake


def test_remote_gates_pass_with_immutable_release_and_peeled_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    monkeypatch.setattr(checker, "gh_api", remote_api())

    findings = checker.check_remote_state(tmp_path, data)

    assert all(item.status == "ok" for item in findings), findings


def test_remote_mutable_release_is_a_blocker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    monkeypatch.setattr(checker, "gh_api", remote_api(immutable=False))

    findings = checker.check_remote_state(tmp_path, data)

    assert any(item.name == "release_basefoundry/base-cli" and item.status == "error" for item in findings)


def test_remote_tag_peel_mismatch_is_a_blocker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    monkeypatch.setattr(checker, "gh_api", remote_api(tag_sha="c" * 40))

    findings = checker.check_remote_state(tmp_path, data)

    assert any(item.name == "tag_basefoundry/base-cli" and item.status == "error" for item in findings)


def test_remote_bom_default_mismatch_is_a_blocker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = create_fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    workflow = tmp_path / ".github" / "workflows" / "ecosystem-release-bom.yml"
    workflow.write_text(workflow.read_text(encoding="utf-8").replace("1.10.1", "1.10.0"), encoding="utf-8")
    monkeypatch.setattr(checker, "gh_api", remote_api())

    findings = checker.check_remote_state(tmp_path, data)

    assert any(item.name == "bom_default_base_version" and item.status == "error" for item in findings)
