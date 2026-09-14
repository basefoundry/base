from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "json-output-quickstart.md"
DOCS_README = ROOT / "docs" / "README.md"


def test_json_output_quickstart_is_linked_from_the_docs_map() -> None:
    assert "json-output-quickstart.md" in DOCS_README.read_text(encoding="utf-8")


def test_json_output_quickstart_uses_the_documented_diagnostic_contract() -> None:
    text = DOC.read_text(encoding="utf-8")

    for required in (
        "./bin/basectl check --format json",
        "jq -r '.status",
        "checks[]?",
        "output-formats.md",
        "doctor-findings.md",
        "stable `id`",
        "stderr",
    ):
        assert required in text
