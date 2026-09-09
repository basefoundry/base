from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from base_release.release_readiness import bom_finding


BASE_COMMIT = "a" * 40


def valid_bom(*, repository: str = "basefoundry/base", version: str = "1.9.0", commit: str = BASE_COMMIT) -> dict:
    return {
        "schema_version": 1,
        "release": {
            "repository": repository,
            "version": version,
            "tag": f"v{version}",
            "commit": commit,
        },
        "components": [
            {
                "repository": repository,
                "version": version,
                "tag": f"v{version}",
                "commit": commit,
                "source_mode": "release",
                "api_schema_version": "manifest-1",
                "platforms": ["macos-14", "ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": "run://base/123",
            },
            {
                "repository": "basefoundry/base-cli",
                "version": "0.4.3",
                "tag": "v0.4.3",
                "commit": "b" * 40,
                "source_mode": "release",
                "api_schema_version": "base-cli-api@0.4.3",
                "platforms": ["macos-14", "ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": "run://base-cli/123",
            },
        ],
        "combinations": [
            {
                "name": "base-release-stack-ubuntu-24.04",
                "participants": [repository, "basefoundry/base-cli"],
                "platform": "ubuntu-24.04",
                "required": True,
                "result": "passed",
                "evidence": "run://base/123",
            }
        ],
    }


def release_context(bom_path: Path | None):
    return SimpleNamespace(
        bom_path=bom_path,
        release=SimpleNamespace(github=SimpleNamespace(repository="basefoundry/base")),
        version="1.9.0",
    )


def write_bom(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_bom_finding_accepts_a_valid_reviewed_bom(tmp_path: Path) -> None:
    path = write_bom(tmp_path / "release-bom.json", valid_bom())

    finding = bom_finding(release_context(path), BASE_COMMIT)

    assert finding.status == "ok"
    assert finding.name == "bom"


def test_bom_finding_accepts_an_unrequested_bom() -> None:
    finding = bom_finding(release_context(None), None)

    assert finding.status == "ok"
    assert "No release BOM was requested" in finding.message


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (None, "missing"),
        ({}, "schema_version"),
        (valid_bom(repository="basefoundry/other"), "release.repository"),
        (valid_bom(version="1.8.0"), "release.version"),
        (valid_bom(commit="c" * 40), "release.commit"),
    ],
)
def test_bom_finding_reports_blocking_validation_errors(
    tmp_path: Path, document: object, expected: str
) -> None:
    path = tmp_path / "release-bom.json"
    if document is not None:
        write_bom(path, document)

    finding = bom_finding(release_context(path), BASE_COMMIT)

    assert finding.status == "error"
    assert finding.name == "bom"
    assert expected in finding.message


def test_bom_finding_reports_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "release-bom.json"
    path.write_text("{not-json}\n", encoding="utf-8")

    finding = bom_finding(release_context(path), BASE_COMMIT)

    assert finding.status == "error"
    assert "not valid JSON" in finding.message
