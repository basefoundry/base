from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
                "inputs": {},
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
    manifest = tmp_path / "train.json"
    manifest.write_text(json.dumps(valid_manifest()), encoding="utf-8")
    return manifest


def run_checker(root: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--manifest", str(manifest), "--no-git", "--format", "json"],
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
