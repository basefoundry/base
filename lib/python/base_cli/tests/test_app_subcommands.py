from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import base_cli
from base_cli.testing import invoke


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class AppSubcommandTests(unittest.TestCase):
    def test_subcommand_group_help_includes_app_help_text(self) -> None:
        app = base_cli.App(name="multi-help", help="Manage workspace demo tasks.")

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            del ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--help"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Manage workspace demo tasks.", result.output)
        self.assertIn("status", result.output)

    def test_subcommand_group_help_without_app_help_keeps_command_listing(self) -> None:
        app = base_cli.App(name="multi-help-default")

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            del ctx

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--help"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Commands:", result.output)
        self.assertIn("status", result.output)

    def test_runs_multiple_subcommands_with_base_lifecycle(self) -> None:
        app = base_cli.App(name="multi-tool", version="0.1.0")
        seen = {}

        @app.subcommand()
        @base_cli.option("--name", required=True)
        def hello(ctx: base_cli.Context, name: str) -> None:
            seen["hello"] = {
                "name": name,
                "run_id": ctx.run_id,
                "temp_dir": ctx.temp_dir,
                "cache_dir": ctx.cache_dir,
                "log_file": ctx.log_file,
            }
            ctx.log.info("hello %s", name)

        @app.subcommand()
        @base_cli.argument("target")
        def clean(ctx: base_cli.Context, target: str) -> None:
            seen["clean"] = {
                "target": target,
                "run_id": ctx.run_id,
                "temp_dir": ctx.temp_dir,
                "cache_dir": ctx.cache_dir,
                "log_file": ctx.log_file,
            }
            ctx.log.info("clean %s", target)

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            hello_result = invoke(app, ["hello", "--name", "Ada"], home=home)
            clean_result = invoke(app, ["clean", "cache"], home=home)

            self.assertEqual(hello_result.exit_code, 0, hello_result.output)
            self.assertEqual(clean_result.exit_code, 0, clean_result.output)
            self.assertEqual(seen["hello"]["name"], "Ada")
            self.assertEqual(seen["clean"]["target"], "cache")
            self.assertNotEqual(seen["hello"]["run_id"], seen["clean"]["run_id"])
            self.assertFalse(seen["hello"]["temp_dir"].exists())
            self.assertFalse(seen["clean"]["temp_dir"].exists())
            self.assertTrue(seen["hello"]["cache_dir"].is_dir())
            self.assertTrue(seen["clean"]["cache_dir"].is_dir())
            self.assertTrue(seen["hello"]["log_file"].is_file())
            self.assertTrue(seen["clean"]["log_file"].is_file())
            self.assertIn("hello Ada", hello_result.stderr)
            self.assertIn("clean cache", clean_result.stderr)

    def test_subcommand_standard_options_and_cleanup_hooks(self) -> None:
        app = base_cli.App(name="subcommand-cleanup")
        seen = {}

        @app.subcommand()
        @base_cli.option("--dry-run", is_flag=True)
        def preview(ctx: base_cli.Context, dry_run: bool) -> None:
            seen["dry_run"] = dry_run
            seen["ctx_dry_run"] = ctx.dry_run
            seen["log_file"] = ctx.log_file
            seen["temp_dir"] = ctx.temp_dir
            seen["cleanup_called"] = False
            ctx.on_cleanup(lambda: seen.update(cleanup_called=True))
            ctx.log.info("preview")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["preview", "--dry-run"], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(seen["dry_run"])
            self.assertTrue(seen["ctx_dry_run"])
            self.assertIsNone(seen["log_file"])
            self.assertFalse(seen["temp_dir"].exists())
            self.assertTrue(seen["cleanup_called"])
            self.assertFalse((home / ".cache" / "base").exists())
            self.assertIn("preview", result.stderr)

    def test_group_standard_debug_option_before_subcommand(self) -> None:
        app = base_cli.App(name="group-debug", log_to_file=False)
        seen = {}

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            seen["debug"] = ctx.debug
            ctx.log.debug("debug status")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--debug", "status"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(seen["debug"])
        self.assertIn("debug status", result.stderr)

    def test_group_standard_environment_option_before_subcommand(self) -> None:
        app = base_cli.App(name="group-environment", log_to_file=False)
        seen = {}

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            seen["environment"] = ctx.environment

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["--environment", "stage", "status"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(seen["environment"], "stage")

    def test_subcommand_standard_debug_option_after_subcommand_still_works(self) -> None:
        app = base_cli.App(name="subcommand-debug", log_to_file=False)
        seen = {}

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            seen["debug"] = ctx.debug
            ctx.log.debug("debug status")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            result = invoke(app, ["status", "--debug"], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(seen["debug"])
        self.assertIn("debug status", result.stderr)

    def test_subcommand_redacts_sensitive_options_per_subcommand(self) -> None:
        app = base_cli.App(name="secret-subcommands")
        seen = {}

        @app.subcommand()
        @base_cli.option("--token", sensitive=True, required=True)
        def sync(ctx: base_cli.Context, token: str) -> None:
            seen["log_file"] = ctx.log_file
            ctx.log.info("token length %d", len(token))

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            with mock.patch.object(os.sys, "argv", ["secret-subcommands", "sync", "--token", "super-secret"]):
                result = invoke(app, ["sync", "--token", "super-secret"], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            log_text = seen["log_file"].read_text(encoding="utf-8")
            self.assertIn("argv=", log_text)
            self.assertIn("--token", log_text)
            self.assertIn("[REDACTED]", log_text)
            self.assertNotIn("super-secret", log_text)

    def test_rejects_top_level_command_after_subcommands(self) -> None:
        app = base_cli.App(name="mixed-tool")

        @app.subcommand()
        def status(ctx: base_cli.Context) -> None:
            del ctx

        with self.assertRaisesRegex(RuntimeError, "already has registered subcommands"):
            @app.command()
            def main(ctx: base_cli.Context) -> None:
                del ctx
