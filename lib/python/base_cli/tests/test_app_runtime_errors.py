from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import base_cli
from base_cli.testing import invoke


class AppRuntimeErrorTests(unittest.TestCase):
    def test_missing_click_error_recommends_pip_install(self) -> None:
        with mock.patch.dict(sys.modules, {"click": None}):
            with self.assertRaisesRegex(RuntimeError, r"Install it with 'pip install click'"):
                base_cli.app._require_click()

    def test_testing_missing_click_error_recommends_pip_install(self) -> None:
        app = base_cli.App(name="missing-click")

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            del ctx

        with mock.patch.dict(sys.modules, {"click": None}):
            with self.assertRaisesRegex(RuntimeError, r"Install it with 'pip install click'"):
                invoke(app, [])

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_run_app_reports_unwritable_cache_root_without_traceback(self) -> None:
        app = base_cli.App(name="cache-failure", version="0.1.0")

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            del ctx
            self.fail("command body should not run when context creation fails")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            cache_root = root / "cache-root"
            home.mkdir()
            cache_root.mkdir()
            cache_root.chmod(0o500)
            stderr = io.StringIO()
            try:
                with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": str(cache_root)}):
                    with redirect_stderr(stderr):
                        try:
                            exit_code = base_cli.run_app(app, [])
                        except PermissionError as exc:
                            self.fail(f"run_app should handle context creation permission errors: {exc}")
            finally:
                cache_root.chmod(0o700)

        error = stderr.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("Error:", error)
        self.assertIn("Unable to create Base runtime directory", error)
        self.assertIn(str(cache_root / "base" / "runs"), error)
        self.assertIn("BASE_CACHE_DIR", error)
        self.assertNotIn("Traceback", error)
