from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "docs" / "adopter-golden-path.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
README = REPO_ROOT / "README.md"
CONTRACTS = REPO_ROOT / "docs" / "contracts.md"


def test_golden_path_documents_the_required_journey() -> None:
    text = GOLDEN_PATH.read_text(encoding="utf-8")

    for command in (
        "basectl setup --dry-run",
        "basectl update-profile",
        "basectl check",
        "basectl doctor",
        "basectl trust status",
        "basectl trust allow",
        "basectl repo check .",
        "basectl test",
        "basectl gh issue start",
        "basectl gh pr create",
        "basectl gh pr checks",
    ):
        assert command in text
    assert "macOS" in text
    assert "Ubuntu/Debian" in text
    assert "Native Windows" in text
    assert "Duplicate project names" in text
    assert "authentication and runtime-verification warnings" in text


def test_golden_path_is_linked_and_registered() -> None:
    assert "adopter-golden-path.md" in DOCS_README.read_text(encoding="utf-8")
    assert "docs/adopter-golden-path.md" in README.read_text(encoding="utf-8")
    assert "| Adopter golden path |" in CONTRACTS.read_text(encoding="utf-8")
