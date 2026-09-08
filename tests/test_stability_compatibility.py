from __future__ import annotations

import copy
import json
from pathlib import Path

from tests import stability_compatibility as compatibility

# pylint: disable=protected-access


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_FIXTURE = REPO_ROOT / "docs" / "stability-baseline" / "current.json"
INITIAL_FIXTURE = REPO_ROOT / "docs" / "stability-baseline" / "v1.8.0.json"


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_fixture_matches_the_repository_contract() -> None:
    assert not compatibility.run_check(REPO_ROOT, runtime=True)


def test_runtime_diagnostic_output_matches_the_published_contract() -> None:
    reference = load_fixture(CURRENT_FIXTURE)["json_contracts"]["diagnostic-v1"]
    observed = compatibility.runtime_contracts(REPO_ROOT)["diagnostic-v1"]
    errors: list[str] = []

    compatibility.validate_runtime_shape(reference, observed, "runtime.diagnostic-v1", errors, reference)

    assert not errors


def test_fixtures_retain_v1_8_provenance() -> None:
    assert load_fixture(CURRENT_FIXTURE)["baseline_version"] == "1.8.0"
    assert load_fixture(INITIAL_FIXTURE)["baseline_version"] == "1.8.0"


def test_current_fixture_changes_are_explicitly_compatible_with_v1_8() -> None:
    current = load_fixture(CURRENT_FIXTURE)
    provenance = load_fixture(INITIAL_FIXTURE)

    assert not compatibility.compare_provenance(provenance, current)


def test_unapproved_v1_8_change_is_breaking() -> None:
    current = load_fixture(CURRENT_FIXTURE)
    provenance = load_fixture(INITIAL_FIXTURE)
    current["findings"]["BASE-D001"] = "A changed meaning"

    errors = compatibility.compare_provenance(provenance, current)

    assert any("unapproved compatibility change" in error for error in errors)


def test_additive_contract_changes_are_compatible() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    actual["commands"]["basectl synthetic"] = {"flags": {"--new": {"takes_value": False}}}
    actual["findings"]["BASE-X999"] = "New finding"
    actual["json_contracts"]["inspection-v1"]["properties"]["new_key"] = {"type": "string"}

    assert not compatibility.compare_snapshots(reference, actual)


def test_removed_flag_is_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    del actual["commands"]["basectl check [project]"]["flags"]["--format"]

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("removed stable option '--format'" in error for error in errors)


def test_enum_removal_and_type_change_are_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    actual["commands"]["basectl check [project]"]["flags"]["--format"]["enum"].remove("json")
    actual["json_contracts"]["inspection-v1"]["properties"]["data"]["type"] = "array"

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("removed enum values ['json']" in error for error in errors)
    assert any("json_contracts.inspection-v1.data.type" in error for error in errors)


def test_finding_id_reuse_is_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    actual["findings"]["BASE-D001"] = "A different diagnostic"

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("reused or changed meaning for BASE-D001" in error for error in errors)


def test_schema_field_removal_is_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    del actual["schemas"]["workspace-update.json"]["properties"]["counts"]

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("schemas.workspace-update.json.properties" in error for error in errors)


def test_schema_additional_properties_tightening_is_breaking() -> None:
    reference = {"type": "object", "additionalProperties": True}
    actual = {"type": "object", "additionalProperties": False}

    errors: list[str] = []
    compatibility._compare_schema(reference, actual, "schema", errors)

    assert any("additionalProperties" in error for error in errors)


def test_schema_ref_retargeting_is_breaking() -> None:
    reference = {"$ref": "#/$defs/stable"}
    actual = {"$ref": "#/$defs/other"}

    errors: list[str] = []
    compatibility._compare_schema(reference, actual, "schema", errors)

    assert any("$ref" in error for error in errors)


def test_schema_order_normalization_ignores_unordered_lists() -> None:
    reference = {
        "type": ["null", "string"],
        "oneOf": [{"type": "string"}, {"type": "integer"}],
    }
    actual = {
        "oneOf": [{"type": "integer"}, {"type": "string"}],
        "type": ["string", "null"],
    }

    assert compatibility._normalize_schema(reference) == compatibility._normalize_schema(actual)


def test_const_runtime_shape_uses_const_value_type() -> None:
    errors: list[str] = []
    reference = {"const": 1}
    observed = {"type": "integer"}

    compatibility.validate_runtime_shape(reference, observed, "value", errors, reference)

    assert not errors


def test_findings_parser_respects_escaped_pipes(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "doctor-findings.md").write_text(
        "| ID | Meaning |\n| --- | --- |\n| `BASE-D001` | A\\|B |\n", encoding="utf-8"
    )

    assert compatibility.extract_findings(tmp_path) == {"BASE-D001": "A|B"}


def test_fixture_update_requires_changelog_marker(monkeypatch, tmp_path: Path) -> None:
    diffs = {
        "docs/stability-baseline/current.json": "diff --git ...",
        "CHANGELOG.md": "+- Other change\n",
    }
    monkeypatch.setattr(compatibility, "_git_diff", lambda _root, _base, path: diffs[path])

    errors = compatibility.require_changelog_for_fixture_change(tmp_path, "base")

    assert errors and "Stability compatibility:" in errors[0]


def test_fixture_update_accepts_changelog_marker(monkeypatch, tmp_path: Path) -> None:
    diffs = {
        "docs/stability-baseline/current.json": "diff --git ...",
        "CHANGELOG.md": "+- Stability compatibility: document the migration.\n",
    }
    monkeypatch.setattr(compatibility, "_git_diff", lambda _root, _base, path: diffs[path])

    assert not compatibility.require_changelog_for_fixture_change(tmp_path, "base")


def test_fixture_update_rejects_placeholder_changelog_marker(monkeypatch, tmp_path: Path) -> None:
    diffs = {
        "docs/stability-baseline/current.json": "diff --git ...",
        "CHANGELOG.md": "+- stability compatibility: n/a\n",
    }
    monkeypatch.setattr(compatibility, "_git_diff", lambda _root, _base, path: diffs[path])

    errors = compatibility.require_changelog_for_fixture_change(tmp_path, "base")

    assert errors
