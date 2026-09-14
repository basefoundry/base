from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "first-run-troubleshooting.md"
DOCS_README = ROOT / "docs" / "README.md"


def test_first_run_troubleshooting_is_linked_from_the_docs_map() -> None:
    assert "first-run-troubleshooting.md" in DOCS_README.read_text(encoding="utf-8")


def test_first_run_troubleshooting_keeps_the_decision_tree_actionable() -> None:
    text = DOC.read_text(encoding="utf-8")

    for required in (
        "./bin/basectl check",
        "./bin/basectl doctor",
        "./bin/basectl setup --dry-run",
        "doctor-findings.md",
        "runtime-environment.md",
        "cache-ownership-and-layout.md",
        "../SUPPORT.md",
        "../SECURITY.md",
    ):
        assert required in text
