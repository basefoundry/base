from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OBSERVABILITY_DOC = REPO_ROOT / "docs" / "observability.md"


def implementation_split_section() -> str:
    text = OBSERVABILITY_DOC.read_text(encoding="utf-8")
    start = text.index("## Implementation Split")
    end = text.index("## First Slice Decisions")
    return text[start:end]


def test_unscheduled_observability_work_is_not_numbered_as_active_steps() -> None:
    section = implementation_split_section()

    assert "Unscheduled Future Work" in section
    assert "2. Add `basectl explain last-error`" not in section
    assert "3. Add `basectl report`" not in section
    assert "4. Extend `basectl clean`" not in section
