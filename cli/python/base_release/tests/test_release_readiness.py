from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from base_release.release_bom import canonical_bom_bytes
from base_release.release_readiness import bom_finding


COMMIT = "a" * 40


def valid_bom() -> dict:
    return {
        "schema_version": 1,
        "release": {
            "repository": "basefoundry/base",
            "version": "1.9.0",
            "tag": "v1.9.0",
            "commit": COMMIT,
        },
        "components": [
            {
                "repository": "basefoundry/base",
                "version": "1.9.0",
                "tag": "v1.9.0",
                "commit": COMMIT,
                "source_mode": "release",
                "api_schema_version": "manifest-1",
                "platforms": ["ubuntu-24.04"],
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
                "platforms": ["ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": "run://base-cli/123",
            },
        ],
        "combinations": [
            {
                "name": "base-release-stack-ubuntu-24.04",
                "participants": ["basefoundry/base", "basefoundry/base-cli"],
                "platform": "ubuntu-24.04",
                "required": True,
                "result": "passed",
                "evidence": "run://base/123",
            }
        ],
    }


def context(path: Path):
    return SimpleNamespace(
        bom_path=path,
        release=SimpleNamespace(github=SimpleNamespace(repository="basefoundry/base")),
        version="1.9.0",
    )


def test_bom_finding_accepts_canonical_bom_bytes(tmp_path: Path) -> None:
    path = tmp_path / "release-bom.json"
    path.write_bytes(canonical_bom_bytes(valid_bom()))

    finding = bom_finding(context(path), COMMIT)

    assert finding.status == "ok"


def test_bom_finding_rejects_valid_but_noncanonical_bom_bytes(tmp_path: Path) -> None:
    path = tmp_path / "release-bom.json"
    path.write_text(json.dumps(valid_bom(), indent=2) + "\n", encoding="utf-8")

    finding = bom_finding(context(path), COMMIT)

    assert finding.status == "error"
    assert finding.name == "bom"
    assert "canonical form" in finding.message
    assert "base-release-bom assemble" in finding.message
