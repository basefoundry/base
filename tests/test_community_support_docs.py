from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_community_support_names_canonical_forum_and_boundaries() -> None:
    text = (ROOT / "docs" / "community-support.md").read_text()

    assert "https://github.com/orgs/basefoundry/discussions" in text
    assert "Issues remain for scoped, actionable work" in text
    assert "Private security advisory" in text
    assert "discussion in the issue body" in text
    assert "Empty space is" in text
    assert "manufactured engagement" in text


def test_public_front_door_is_linked_from_readme_and_docs_index() -> None:
    readme = (ROOT / "README.md").read_text()
    docs_readme = (ROOT / "docs" / "README.md").read_text()

    assert "docs/community-support.md" in readme
    assert "community-support.md" in docs_readme
