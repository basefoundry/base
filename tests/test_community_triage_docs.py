from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_triage_policy_names_starter_queue_and_review_cadence() -> None:
    text = (ROOT / "docs" / "community-triage.md").read_text()

    for issue in ("#2278", "#2279", "#2280", "#344", "#345", "#346", "#491", "#492"):
        assert issue in text
    assert "2026-10-01" in text
    assert "good first issue" in text
    assert "Do not auto-close an issue" in text
    assert "solely because it is" in text
