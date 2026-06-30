from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_prompt import engine


BASE_HOME = Path(__file__).resolve().parents[4]


def invoke(args: list[str], env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        patched_env = {"BASE_HOME": str(BASE_HOME), "HOME": home_dir, **(env or {})}
        with mock.patch.dict(os.environ, patched_env):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class BasePromptTests(unittest.TestCase):
    def test_list_includes_product_self_review_prompt(self) -> None:
        status, stdout, stderr = invoke(["list"])

        self.assertEqual(status, 0, stderr)
        self.assertEqual(stderr, "")
        self.assertIn("product-self-review", stdout)
        self.assertIn("Periodic Base product self-review", stdout)

    def test_product_self_review_prompt_includes_current_metadata_and_questions(self) -> None:
        version = (BASE_HOME / "VERSION").read_text(encoding="utf-8").strip()

        status, stdout, stderr = invoke(["product-self-review"])

        self.assertEqual(status, 0, stderr)
        self.assertEqual(stderr, "")
        self.assertIn("# Base Product Self-Review", stdout)
        self.assertIn("Generated:", stdout)
        self.assertIn("Project: base", stdout)
        self.assertIn(f"Version: {version}", stdout)
        self.assertIn("docs/product-assessment.md", stdout)
        self.assertIn("How original is Base?", stdout)
        self.assertIn("How useful is Base, and for whom?", stdout)
        self.assertIn("Do not update files unless explicitly asked.", stdout)

    def test_unknown_prompt_reports_usage_error(self) -> None:
        status, stdout, stderr = invoke(["missing-prompt"])

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Usage:", stderr)
        self.assertIn("ERROR: Unknown prompt 'missing-prompt'.", stderr)

    def test_usage_errors_use_delegated_display_command(self) -> None:
        status, stdout, stderr = invoke(
            ["missing-prompt"],
            env={"BASE_CLI_DISPLAY_COMMAND": "basectl prompt"},
        )

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("basectl prompt list", stderr)
        self.assertIn("basectl prompt <name>", stderr)
        self.assertNotIn("base_prompt", stderr)


if __name__ == "__main__":
    unittest.main()
