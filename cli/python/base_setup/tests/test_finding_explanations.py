from __future__ import annotations

import io
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from base_setup import finding_explanations


REPO_ROOT = Path(__file__).resolve().parents[4]
DOCTOR_FINDINGS_DOC = REPO_ROOT / "docs" / "doctor-findings.md"


def invoke(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = finding_explanations.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class FindingExplanationTests(unittest.TestCase):
    def test_known_id_renders_local_text_explanation(self) -> None:
        status, stdout, stderr = invoke(["base-p050"])

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("BASE-P050 - Project virtual environment readiness", stdout)
        self.assertIn("Why it matters:", stdout)
        self.assertIn("Fix steps:", stdout)
        self.assertIn("basectl setup <project> --dry-run", stdout)
        self.assertIn("docs/python-manifest.md", stdout)

    def test_known_id_renders_stable_json_shape(self) -> None:
        status, stdout, stderr = invoke(["BASE-D001", "--format", "json"])

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["id"], "BASE-D001")
        self.assertEqual(payload["title"], "Homebrew availability and PATH refresh")
        self.assertGreaterEqual(len(payload["likely_causes"]), 1)
        self.assertGreaterEqual(len(payload["fix_steps"]), 1)
        self.assertGreaterEqual(len(payload["related_commands"]), 1)
        self.assertEqual(payload["docs"][0]["path"], "docs/doctor-findings.md#base-runtime-findings")

    def test_unknown_id_fails_with_clear_text_guidance(self) -> None:
        status, stdout, stderr = invoke(["BASE-X999"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No local explanation is available for BASE-X999", stderr)
        self.assertIn("docs/doctor-findings.md", stderr)

    def test_unknown_id_json_is_machine_readable(self) -> None:
        status, stdout, stderr = invoke(["BASE-X999", "--format", "json"])

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertFalse(payload["found"])
        self.assertEqual(payload["id"], "BASE-X999")
        self.assertIn("BASE-D001", payload["known_ids"])
        self.assertEqual(payload["docs"], "docs/doctor-findings.md")

    def test_catalog_entries_are_documented_finding_ids(self) -> None:
        doc_text = DOCTOR_FINDINGS_DOC.read_text(encoding="utf-8")
        documented_ids = set(re.findall(r"`(BASE-[DPHW][0-9]{3})`", doc_text))

        self.assertTrue(set(finding_explanations.CATALOG).issubset(documented_ids))

    def test_catalog_entries_have_actionable_sections(self) -> None:
        for explanation in finding_explanations.CATALOG.values():
            with self.subTest(finding_id=explanation.finding_id):
                self.assertEqual(
                    explanation.finding_id,
                    finding_explanations.normalize_finding_id(explanation.finding_id),
                )
                self.assertTrue(explanation.summary)
                self.assertTrue(explanation.why_it_matters)
                self.assertTrue(explanation.likely_causes)
                self.assertTrue(explanation.fix_steps)
                self.assertTrue(explanation.related_commands)
                self.assertTrue(explanation.docs)


if __name__ == "__main__":
    unittest.main()
