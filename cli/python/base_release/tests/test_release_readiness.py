from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from base_release.release_bom import canonical_bom_bytes
from base_release.release_readiness import bom_finding
from base_release.tests._bom_fixtures import BASE_COMMIT, valid_bom


def write_bom(path: Path, document: dict) -> Path:
    path.write_bytes(canonical_bom_bytes(document))
    return path


def release_context(bom_path: Path | None, *, bom_required: bool = False):
    return SimpleNamespace(
        bom_path=bom_path,
        release=SimpleNamespace(
            github=SimpleNamespace(repository="basefoundry/base"),
            bom=SimpleNamespace(required=bom_required),
        ),
        version="1.9.0",
    )


def test_bom_finding_accepts_canonical_bom_bytes(tmp_path: Path) -> None:
    path = tmp_path / "release-bom.json"
    path.write_bytes(canonical_bom_bytes(valid_bom()))

    finding = bom_finding(release_context(path), BASE_COMMIT)

    assert finding.status == "ok"
    assert finding.name == "bom"


def test_bom_finding_rejects_valid_but_noncanonical_bom_bytes(tmp_path: Path) -> None:
    path = tmp_path / "release-bom.json"
    path.write_text(json.dumps(valid_bom(), indent=2) + "\n", encoding="utf-8")

    finding = bom_finding(release_context(path), BASE_COMMIT)

    assert finding.status == "error"
    assert finding.name == "bom"
    assert "canonical form" in finding.message
    assert "base-release-bom assemble" in finding.message


def test_bom_finding_accepts_an_unrequested_bom() -> None:
    finding = bom_finding(release_context(None), None)

    assert finding.status == "ok"
    assert "No release BOM was requested" in finding.message


def test_bom_finding_requires_bom_when_manifest_opts_in() -> None:
    finding = bom_finding(release_context(None, bom_required=True), None)

    assert finding.status == "error"
    assert finding.name == "bom"
    assert "release.bom.required" in finding.message
    assert "--bom" in finding.message


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
