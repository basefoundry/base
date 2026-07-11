from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STABILITY_DOC = REPO_ROOT / "docs" / "stability-tiers.md"
COMMAND_REFERENCE = REPO_ROOT / "docs" / "command-reference.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
CONTRACTS_DOC = REPO_ROOT / "docs" / "contracts.md"


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
