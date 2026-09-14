from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ecosystem_map_is_linked_and_keeps_support_boundaries_explicit() -> None:
    map_text = (REPO_ROOT / "docs" / "ecosystem-map.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required in (
        "Which project should I start with?",
        "Support matrix",
        "not independent adoption evidence",
        "Native Windows",
        "v1.11.0 Windows milestone",
        "moving sibling checkout",
        "Homebrew",
    ):
        assert required in map_text
    assert "docs/ecosystem-map.md" in readme
    assert "ecosystem-map.md" in docs_readme
