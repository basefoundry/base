import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCTOR_FINDINGS_DOC = REPO_ROOT / "docs" / "doctor-findings.md"


def json_examples() -> list[dict]:
    text = DOCTOR_FINDINGS_DOC.read_text(encoding="utf-8")
    examples: list[dict] = []
    for match in re.finditer(r"```json\n(.*?)\n```", text, re.DOTALL):
        examples.append(json.loads(match.group(1)))
    return examples


def test_top_level_diagnostic_json_example_includes_profiles() -> None:
    example = json_examples()[0]

    assert example == {
        "schema_version": 1,
        "status": "ok",
        "profiles": [],
        "checks": [],
    }
