from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_maintainer_continuity_doc_is_explicit_and_linked() -> None:
    governance = (REPO_ROOT / "docs" / "governance.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assessment = (REPO_ROOT / "docs" / "product-assessment.md").read_text(encoding="utf-8")

    for required in (
        "one primary maintainer",
        "four consecutive weeks",
        "shadow a bounded release",
        "two successful review cycles",
        "not a claim that a second maintainer",
    ):
        assert required in governance
    assert "docs/governance.md" in readme
    assert "governance.md" in assessment


def test_review_governance_points_to_the_executable_follow_up() -> None:
    text = (REPO_ROOT / "docs" / "review-governance.md").read_text(encoding="utf-8")

    assert "#2107" in text
    assert "must never silently lower" in text
