from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_first_external_change_covers_three_paths_and_boundaries() -> None:
    text = (ROOT / "docs" / "contributor-first-change.md").read_text()

    for phrase in (
        "documentation-only",
        "focused component change",
        "full Base change",
        "BASE_CLI_SOURCE_DIR",
        "BASE_BASH_LIBS_DIR",
        "Native Windows is not yet a supported",
        "git diff --check",
    ):
        assert phrase in text


def test_contributor_entry_points_link_to_public_guide() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text()
    docs_readme = (ROOT / "docs" / "README.md").read_text()

    assert "docs/contributor-first-change.md" in contributing
    assert "contributor-first-change.md" in docs_readme
