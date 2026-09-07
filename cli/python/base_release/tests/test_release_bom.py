from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from base_release.release_bom import ReleaseBomError, bom_digest, validate_bom
from base_release.release_bom import load_bom, validate_bom_file


SHA = "a" * 40
BASE_SHA = "b" * 40


def valid_bom() -> dict:
    return {
        "schema_version": 1,
        "release": {
            "repository": "basefoundry/base-bash-libs",
            "version": "2.1.0",
            "tag": "v2.1.0",
            "commit": SHA,
        },
        "components": [
            {
                "repository": "basefoundry/base-bash-libs",
                "version": "2.1.0",
                "tag": "v2.1.0",
                "commit": SHA,
                "source_mode": "release",
                "api_schema_version": "2",
                "platforms": ["macos-14", "ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": "run://tests/validate.sh",
            },
            {
                "repository": "basefoundry/base",
                "version": "1.8.0",
                "tag": "v1.8.0",
                "commit": BASE_SHA,
                "source_mode": "release",
                "api_schema_version": "manifest-1",
                "platforms": ["macos-14", "ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": "run://base-release-check",
            },
            {
                "repository": "basefoundry/base-cli",
                "version": "0.4.3",
                "commit": "c" * 40,
                "source_mode": "moving",
                "api_schema_version": "0.4",
                "platforms": ["python-3.12"],
                "required": False,
                "result": "not_tested",
                "evidence": "advisory://moving-source",
            },
        ],
        "combinations": [
            {
                "name": "released-base-bash-libs-with-base",
                "participants": ["basefoundry/base-bash-libs", "basefoundry/base"],
                "platform": "ubuntu-24.04",
                "required": True,
                "result": "passed",
                "evidence": "run://ecosystem-release-train/123",
            }
        ],
    }


def test_valid_bom_accepts_required_releases_and_advisory_moving_rows() -> None:
    validate_bom(valid_bom(), expected_repository="basefoundry/base-bash-libs", expected_version="2.1.0")


def test_required_moving_source_is_rejected() -> None:
    document = valid_bom()
    document["components"][2]["required"] = True
    with pytest.raises(ReleaseBomError, match="cannot require a moving source"):
        validate_bom(document)


def test_required_failed_combination_is_rejected() -> None:
    document = valid_bom()
    document["combinations"][0]["result"] = "failed"
    with pytest.raises(ReleaseBomError, match="required but result is 'failed'"):
        validate_bom(document)


def test_commit_and_version_mismatch_are_rejected() -> None:
    document = valid_bom()
    with pytest.raises(ReleaseBomError, match="does not match '2.2.0'"):
        validate_bom(document, expected_version="2.2.0")
    with pytest.raises(ReleaseBomError, match="reviewed release commit"):
        validate_bom(document, expected_commit="d" * 40)


def test_digest_is_stable_for_mapping_order() -> None:
    document = valid_bom()
    reordered = json.loads(json.dumps(document))
    reordered["release"] = {key: document["release"][key] for key in reversed(document["release"])}
    assert bom_digest(document) == bom_digest(reordered)


def test_duplicate_component_and_unknown_participant_are_rejected() -> None:
    duplicate = valid_bom()
    duplicate["components"].append(copy.deepcopy(duplicate["components"][0]))
    with pytest.raises(ReleaseBomError, match="duplicated"):
        validate_bom(duplicate)

    unknown = valid_bom()
    unknown["combinations"][0]["participants"].append("basefoundry/unknown")
    with pytest.raises(ReleaseBomError, match="unknown components"):
        validate_bom(unknown)


def test_checked_in_fixtures_cover_valid_and_mutable_documents() -> None:
    fixture_root = Path(__file__).resolve().parents[4] / "tests" / "fixtures"
    validate_bom_file(
        fixture_root / "release-bom-valid.json",
        expected_repository="basefoundry/base-bash-libs",
        expected_version="2.1.0",
    )
    with pytest.raises(ReleaseBomError, match="release.tag must be v<release.version>"):
        validate_bom(load_bom(fixture_root / "release-bom-invalid-mutable.json"))
