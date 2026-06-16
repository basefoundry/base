from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import base_cli
from base_cli.config import user_config_path


class RunAppTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_run_app_reports_config_errors_without_traceback(self) -> None:
        app = base_cli.App(name="bad-config", log_to_file=False)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["called"] = True
            del ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            config_path = user_config_path(home)
            config_path.parent.mkdir(parents=True)
            config_path.write_text("workspace: [not-a-mapping]\n", encoding="utf-8")
            stderr = io.StringIO()
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "BASE_CACHE_DIR": str(home / ".cache" / "base"),
                    "BASE_HOME": str(Path(__file__).resolve().parents[4]),
                },
            ), redirect_stderr(stderr):
                status = base_cli.run_app(app, [])

        self.assertEqual(status, 1)
        self.assertEqual(seen, {})
        self.assertIn("workspace must be a mapping", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_run_app_preserves_unexpected_command_exceptions(self) -> None:
        app = base_cli.App(name="boom", log_to_file=False)

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            del ctx
            raise RuntimeError("boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "BASE_CACHE_DIR": str(home / ".cache" / "base"),
                    "BASE_HOME": str(Path(__file__).resolve().parents[4]),
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    base_cli.run_app(app, [])


if __name__ == "__main__":
    unittest.main()
