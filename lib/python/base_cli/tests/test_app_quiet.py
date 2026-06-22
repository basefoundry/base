from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import base_cli
from base_cli.testing import invoke


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class AppQuietTests(unittest.TestCase):
    def test_quiet_suppresses_info_but_keeps_warning_and_error_output(self) -> None:
        app = base_cli.App(name="quiet-demo", log_to_file=False)

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            ctx.log.info("info hidden")
            ctx.log.warning("warning visible")
            ctx.log.error("error visible")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--quiet"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("info hidden", result.stderr)
        self.assertIn("warning visible", result.stderr)
        self.assertIn("error visible", result.stderr)

    def test_quiet_keeps_debug_detail_in_persistent_log_file(self) -> None:
        app = base_cli.App(name="quiet-file-demo")

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            ctx.log.debug("debug in file")
            ctx.log.info("info in file")
            ctx.log.warning("warning visible")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_file = home / "logs" / "quiet.log"

            result = invoke(app, ["--quiet", "--log-file", str(log_file)], home=home)

            log_text = log_file.read_text(encoding="utf-8")

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("debug in file", result.stderr)
        self.assertNotIn("info in file", result.stderr)
        self.assertIn("warning visible", result.stderr)
        self.assertIn("debug in file", log_text)
        self.assertIn("info in file", log_text)
        self.assertIn("warning visible", log_text)

    def test_debug_and_quiet_conflict(self) -> None:
        app = base_cli.App(name="quiet-conflict", log_to_file=False)

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            del ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--debug", "--quiet"], home=home)

        self.assertEqual(result.exit_code, 2, result.output)
        self.assertIn("--debug and --quiet cannot be used together", result.output)

    def test_quiet_before_subcommand_uses_warning_user_stream(self) -> None:
        app = base_cli.App(name="quiet-subcommand", log_to_file=False)

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            ctx.log.info("info hidden")
            ctx.log.warning("warning visible")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--quiet", "status"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("info hidden", result.stderr)
        self.assertIn("warning visible", result.stderr)
