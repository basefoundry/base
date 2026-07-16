from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STABILITY_DOC = REPO_ROOT / "docs" / "stability-tiers.md"
COMMAND_REFERENCE = REPO_ROOT / "docs" / "command-reference.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
CONTRACTS_DOC = REPO_ROOT / "docs" / "contracts.md"
INSPECTION_JSON_DOC = REPO_ROOT / "docs" / "inspection-json.md"


def test_stability_tiers_doc_defines_public_tiers() -> None:
    text = STABILITY_DOC.read_text(encoding="utf-8")

    assert "| Stable |" in text
    assert "| Experimental |" in text
    assert "| Internal |" in text
    assert "schema_version" in text
    assert "BASE-D001" in text
    assert "Finding IDs](doctor-findings.md)" in text


def test_command_reference_and_docs_map_link_stability_tiers() -> None:
    assert "stability-tiers.md" in COMMAND_REFERENCE.read_text(encoding="utf-8")
    assert "[Stability Tiers](stability-tiers.md)" in DOCS_README.read_text(encoding="utf-8")


def test_contract_registry_tracks_stability_tiers() -> None:
    text = CONTRACTS_DOC.read_text(encoding="utf-8")

    assert "Public command and JSON stability tiers" in text
    assert "tests/test_stability_tiers_docs.py" in text


def test_inspection_json_contract_is_registered_and_stable() -> None:
    contract = INSPECTION_JSON_DOC.read_text(encoding="utf-8")
    registry = CONTRACTS_DOC.read_text(encoding="utf-8")
    stability = STABILITY_DOC.read_text(encoding="utf-8")

    assert '"schema_version": 1' in contract
    assert '"command": "repo check"' in contract
    assert '"command": "release check"' in contract
    assert '"command": "gh issue readiness"' in contract
    assert '"command": "gh branch stale"' in contract
    assert "usage_error" in contract
    assert "inspection-json.md" in registry
    assert "Inspection JSON" in stability
