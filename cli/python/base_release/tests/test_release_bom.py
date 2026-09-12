from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from base_release.release_bom import (
    ReleaseBomError,
    bom_digest,
    bom_digest_sidecar_path,
    load_bom,
    read_bom_digest_sidecar,
    validate_bom,
    validate_bom_file,
    write_bom_digest_sidecar,
)
from base_release.release_bom_cli import main


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


def test_release_repository_must_be_a_declared_component() -> None:
    document = valid_bom()
    document["components"] = document["components"][1:]
    with pytest.raises(ReleaseBomError, match="release.repository must be declared"):
        validate_bom(document)


def test_required_combination_must_include_release_repository() -> None:
    document = valid_bom()
    document["combinations"][0]["participants"] = ["basefoundry/base"]
    with pytest.raises(ReleaseBomError, match="at least two repositories"):
        validate_bom(document)

    document["components"][2]["platforms"].append("ubuntu-24.04")
    document["combinations"][0]["participants"] = ["basefoundry/base", "basefoundry/base-cli"]
    with pytest.raises(ReleaseBomError, match="must include release.repository"):
        validate_bom(document)


def test_combinations_require_two_distinct_participants() -> None:
    document = valid_bom()
    document["combinations"][0]["participants"] = [
        "basefoundry/base-bash-libs",
        "basefoundry/base-bash-libs",
    ]
    with pytest.raises(ReleaseBomError, match="at least two repositories"):
        validate_bom(document)


def test_commit_and_version_mismatch_are_rejected() -> None:
    document = valid_bom()
    with pytest.raises(ReleaseBomError, match="does not match '2.2.0'"):
        validate_bom(document, expected_version="2.2.0")
    with pytest.raises(ReleaseBomError, match="reviewed release commit"):
        validate_bom(document, expected_commit="d" * 40)


def test_release_and_component_commits_must_be_lowercase() -> None:
    document = valid_bom()
    document["release"]["commit"] = SHA.upper()
    with pytest.raises(ReleaseBomError, match="lowercase full 40-character SHA"):
        validate_bom(document)

    document = valid_bom()
    document["components"][0]["commit"] = SHA.upper()
    with pytest.raises(ReleaseBomError, match="lowercase full 40-character SHA"):
        validate_bom(document)


def test_repository_identity_matching_is_case_insensitive() -> None:
    document = valid_bom()
    document["release"]["repository"] = "BaseFoundry/Base-Bash-Libs"
    document["components"][0]["repository"] = "BASEFOUNDRY/BASE-BASH-LIBS"
    document["combinations"][0]["participants"][0] = "basefoundry/BASE-BASH-LIBS"
    validate_bom(document, expected_repository="basefoundry/base-bash-libs")


def test_repository_identity_rejects_malformed_owner_name_values() -> None:
    for value in ("basefoundry/base/extra", "basefoundry/base libs", "/basefoundry/base"):
        document = valid_bom()
        document["components"][0]["repository"] = value
        with pytest.raises(ReleaseBomError, match="must use owner/name format"):
            validate_bom(document)


def test_repository_duplicates_are_case_insensitive() -> None:
    document = valid_bom()
    duplicate = copy.deepcopy(document["components"][0])
    duplicate["repository"] = duplicate["repository"].upper()
    document["components"].append(duplicate)
    with pytest.raises(ReleaseBomError, match="duplicated"):
        validate_bom(document)


def test_digest_is_stable_for_mapping_order() -> None:
    document = valid_bom()
    reordered = json.loads(json.dumps(document))
    reordered["release"] = {key: document["release"][key] for key in reversed(document["release"])}
    assert bom_digest(document) == bom_digest(reordered)


def test_assemble_writes_bytes_matching_reported_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    document = valid_bom()
    component_paths = []
    for index, component in enumerate(document["components"][:2]):
        component_path = tmp_path / f"component-{index}.json"
        component_path.write_text(json.dumps(component), encoding="utf-8")
        component_paths.append(component_path)
    output_path = tmp_path / "release-bom.json"
    arguments = [
        "base-release-bom",
        "assemble",
        "--repository",
        document["release"]["repository"],
        "--version",
        document["release"]["version"],
        "--commit",
        document["release"]["commit"],
    ]
    for component_path in component_paths:
        arguments.extend(("--component", str(component_path)))
    arguments.extend(
        (
            "--combination",
            json.dumps(document["combinations"][0]),
            "--output",
            str(output_path),
        )
    )
    monkeypatch.setattr(sys, "argv", arguments)
    assert main() == 0
    assert hashlib.sha256(output_path.read_bytes()).hexdigest() == bom_digest(load_bom(output_path))
    assert (tmp_path / "release-bom.sha256").read_text(encoding="utf-8") == (
        f"{bom_digest(load_bom(output_path))}  release-bom.json\n"
    )


def test_digest_sidecar_uses_unambiguous_path_and_rejects_mismatches(tmp_path: Path) -> None:
    output_path = tmp_path / "bom.tar.gz"
    output_path.write_bytes(b"canonical BOM bytes\n")

    sidecar_path = write_bom_digest_sidecar(output_path)

    assert sidecar_path == bom_digest_sidecar_path(output_path)
    assert sidecar_path.name == "bom.tar.gz.sha256"
    assert read_bom_digest_sidecar(output_path) == hashlib.sha256(output_path.read_bytes()).hexdigest()

    sidecar_path.write_text(f"{'0' * 64}  bom.tar.gz\n", encoding="utf-8")
    with pytest.raises(ReleaseBomError, match="does not match"):
        read_bom_digest_sidecar(output_path)


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


@pytest.mark.parametrize("source_mode", ["release", "tag"])
def test_component_tag_must_match_its_version(source_mode: str) -> None:
    document = valid_bom()
    document["components"][1].update(source_mode=source_mode, tag="v1.8.1")
    with pytest.raises(ReleaseBomError, match=r"components\[1\].tag must be v<.*version>"):
        validate_bom(document)


def test_release_component_commit_must_match_release_identity() -> None:
    document = valid_bom()
    document["components"][0].update(repository="BASEFOUNDRY/BASE-BASH-LIBS", commit="d" * 40)
    with pytest.raises(ReleaseBomError, match=r"components\[0\].commit must match release.commit"):
        validate_bom(document)


@pytest.mark.parametrize("participant", [0, 1])
@pytest.mark.parametrize("required", [True, False])
def test_combination_platform_must_be_declared_by_every_participant(participant: int, required: bool) -> None:
    document = valid_bom()
    document["components"][participant]["platforms"] = ["macos-14"]
    document["combinations"][0]["required"] = required
    with pytest.raises(ReleaseBomError, match=r"combinations\[0\].platform.*not declared by"):
        validate_bom(document)


@pytest.mark.parametrize("version", ["01.9.0", "1.09.0", "1.9.00", "1.9", "1.9.0-01", "1.9.0+", "1.9.0-", "1.9.0 dev"])
@pytest.mark.parametrize("target", ["release", "moving"])
def test_versions_must_be_strict_semver(version: str, target: str) -> None:
    document = valid_bom()
    row = document["release"] if target == "release" else document["components"][2]
    row["version"] = version
    if target == "release":
        row["tag"] = f"v{version}"
    with pytest.raises(ReleaseBomError, match="version must be a strict SemVer value"):
        validate_bom(document)


@pytest.mark.parametrize("version", ["0.0.0", "1.9.0-alpha.1", "1.9.0-0", "1.9.0+001", "1.9.0-01a+build.001"])
def test_moving_versions_accept_valid_semver_suffixes(version: str) -> None:
    document = valid_bom()
    document["components"][2]["version"] = version
    validate_bom(document)


@pytest.mark.parametrize("repository", ["../foo", "./foo", "owner/..", "owner/."])
@pytest.mark.parametrize("target", ["release", "component"])
def test_repository_dot_segments_are_rejected(repository: str, target: str) -> None:
    document = valid_bom()
    row = document["release"] if target == "release" else document["components"][2]
    row["repository"] = repository
    with pytest.raises(ReleaseBomError, match="must use owner/name format"):
        validate_bom(document)


def test_schema_patterns_match_bom_version_tag_and_repository_contracts() -> None:
    # Lexical constraints belong in the schema; cross-field relations need the validator.
    from jsonschema import Draft202012Validator  # pylint: disable=import-outside-toplevel

    schema_path = Path(__file__).resolve().parents[4] / "docs/schemas/release-bom.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(valid_bom())
    for field, value in (("repository", "../foo"), ("version", "01.9.0"), ("tag", "v01.9.0")):
        document = valid_bom()
        document["components"][0][field] = value
        assert not validator.is_valid(document), (field, value)
        document = valid_bom()
        document["release"][field] = value
        assert not validator.is_valid(document), (field, value)
    document = valid_bom()
    document["components"][2]["version"] = "1.9.0-alpha.1+001"
    validator.validate(document)
    validate_bom(document)
