from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "version_consistency_check.py"


def contract(*, expires: str = "2099-01-01") -> dict[str, object]:
    return {
        "schema_version": 1,
        "authority": {"path": "VERSION"},
        "surfaces": [
            {
                "name": "readme",
                "path": "README.md",
                "must_contain": ["version-{version}-blue", "Release {version}"],
            },
            {
                "name": "historical",
                "path": "docs/example.md",
                "must_contain": ["v1.0.0"],
                "exception": "historical-fixture",
            },
        ],
        "exceptions": [
            {
                "name": "historical-fixture",
                "path": "docs/example.md",
                "reason": "Retained as a historical fixture.",
                "expires": expires,
            }
        ],
    }


def run_checker(root: Path, config: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--config",
            str(config),
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def create_fixture(tmp_path: Path, *, readme: str = "") -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "example.md").write_text("v1.0.0\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    config = tmp_path / "version-consistency.json"
    config.write_text(json.dumps(contract()), encoding="utf-8")
    return config


def test_matching_surfaces_and_allowlist_pass(tmp_path: Path) -> None:
    config = create_fixture(tmp_path, readme="version-1.2.3-blue\nRelease 1.2.3\n")

    result = run_checker(tmp_path, config)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "warn"


def test_stale_surface_reports_file_specific_finding(tmp_path: Path) -> None:
    config = create_fixture(tmp_path, readme="version-1.2.2-blue\nRelease 1.2.2\n")

    result = run_checker(tmp_path, config)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    readme_finding = next(item for item in payload["findings"] if item["name"] == "readme")
    assert "README.md is missing required version text" in readme_finding["message"]


def test_expired_allowlist_is_a_blocker(tmp_path: Path) -> None:
    config = create_fixture(tmp_path, readme="version-1.2.3-blue\nRelease 1.2.3\n")
    data = json.loads(config.read_text(encoding="utf-8"))
    data["exceptions"][0]["expires"] = "2000-01-01"
    config.write_text(json.dumps(data), encoding="utf-8")

    result = run_checker(tmp_path, config)

    assert result.returncode == 1
    assert "expired on 2000-01-01" in result.stdout


def test_allowlist_suppresses_stale_surface_until_expiry(tmp_path: Path) -> None:
    config = create_fixture(tmp_path, readme="version-1.2.3-blue\nRelease 1.2.3\n")
    (tmp_path / "docs" / "example.md").write_text("v0.1.0 historical fixture\n", encoding="utf-8")

    result = run_checker(tmp_path, config)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    historical = next(item for item in payload["findings"] if item["name"] == "historical")
    assert historical["status"] == "warn"
    assert "historical-fixture" in historical["message"]


def test_unsafe_paths_are_rejected(tmp_path: Path) -> None:
    config = create_fixture(tmp_path, readme="version-1.2.3-blue\nRelease 1.2.3\n")
    data = json.loads(config.read_text(encoding="utf-8"))
    data["authority"]["path"] = "../VERSION"
    data["surfaces"][0]["path"] = "/etc/hosts"
    config.write_text(json.dumps(data), encoding="utf-8")

    result = run_checker(tmp_path, config)

    assert result.returncode == 1
    assert "repository-relative" in result.stdout
    assert "surface.path must be a relative path" in result.stdout


def test_non_utf8_version_surface_is_a_finding(tmp_path: Path) -> None:
    config = create_fixture(tmp_path, readme="version-1.2.3-blue\nRelease 1.2.3\n")
    (tmp_path / "README.md").write_bytes(b"\xff")

    result = run_checker(tmp_path, config)

    assert result.returncode == 1
    assert "unable to read version surface" in result.stdout
