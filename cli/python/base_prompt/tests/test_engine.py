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


def invoke_without_base_home(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(os.environ, {"HOME": home_dir}, clear=True):
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

    def test_product_self_review_prompt_can_write_to_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "product-self-review.md"

            status, stdout, stderr = invoke(["product-self-review", "--output", str(output_path)])

            self.assertEqual(status, 0, stderr)
            self.assertEqual(stderr, "")
            self.assertEqual(stdout, f"Wrote prompt 'product-self-review' to {output_path}\n")
            written = output_path.read_text(encoding="utf-8")
            self.assertIn("# Base Product Self-Review", written)
            self.assertIn("Project: base", written)
            self.assertIn("Do not update files unless explicitly asked.", written)

    def test_product_self_review_prompt_requires_base_home(self) -> None:
        status, stdout, stderr = invoke_without_base_home(["product-self-review"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("ERROR: Base home is unavailable.", stderr)
        self.assertIn("basectl prompt", stderr)

    def test_unknown_prompt_reports_usage_error(self) -> None:
        status, stdout, stderr = invoke(["missing-prompt"])

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Usage:", stderr)
        self.assertIn("ERROR: Unknown prompt 'missing-prompt'.", stderr)

    def test_output_is_not_allowed_for_prompt_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "prompts.md"

            status, stdout, stderr = invoke(["list", "--output", str(output_path)])

            self.assertEqual(status, 2)
            self.assertEqual(stdout, "")
            self.assertIn("ERROR: Option '--output' can only be used with a prompt name.", stderr)
            self.assertFalse(output_path.exists())

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
