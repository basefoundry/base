from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import chdir, redirect_stderr
from pathlib import Path
from unittest import mock

import base_cli
from base_cli.paths import base_state_root, discover_manifest, normalize_cli_name
from base_cli.redaction import redact_argv


class BaseCliTests(unittest.TestCase):
    def test_import_has_no_state_directory_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                self.assertFalse((home / ".base.d").exists())

    def test_path_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            (root / "base_manifest.yaml").write_text("project:\n  name: demo\n", encoding="utf-8")

            self.assertEqual(base_state_root(root), root / ".base.d")
            self.assertEqual(normalize_cli_name("/tmp/demo.py"), "demo")
            self.assertEqual(discover_manifest(nested), (root / "base_manifest.yaml").resolve())

    def test_redacts_sensitive_option_values(self) -> None:
        argv = ["tool", "--api-key", "secret", "--token=hidden", "--name", "visible"]

        self.assertEqual(
            redact_argv(argv, {"api_key", "token"}),
            ["tool", "--api-key", "[REDACTED]", "--token=[REDACTED]", "--name", "visible"],
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_runs_with_context_and_cleans_temp_dir(self) -> None:
        app = base_cli.App(name="demo", version="0.1.0")
        seen = {}

        @app.command()
        @base_cli.option("--name", required=True)
        def main(ctx: base_cli.Context, name: str) -> None:
            seen["name"] = name
            seen["temp_dir"] = ctx.temp_dir
            seen["cache_dir"] = ctx.cache_dir
            ctx.log.info("hello %s", name)

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                from base_cli.testing import invoke

                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    result = invoke(app, ["--name", "Ada"], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(seen["name"], "Ada")
            self.assertFalse(seen["temp_dir"].exists())
            self.assertTrue(seen["cache_dir"].is_dir())
            self.assertTrue((home / ".base.d" / "cli" / "demo" / "logs").is_dir())
            self.assertRegex(result.stderr, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO\s+")
            self.assertIn("hello Ada", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_standard_options_manifest_context_and_sensitive_redaction(self) -> None:
        app = base_cli.App(name="secret-tool", version="0.1.0")
        seen = {}

        @app.command()
        @base_cli.option("--token", sensitive=True, required=True)
        def main(ctx: base_cli.Context, token: str) -> None:
            seen["token"] = token
            seen["debug"] = ctx.debug
            seen["temp_dir"] = ctx.temp_dir
            seen["log_file"] = ctx.log_file
            seen["manifest_path"] = ctx.manifest_path
            seen["project_root"] = ctx.project_root
            ctx.log.info("processed token")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            project = Path(tmpdir) / "project"
            home.mkdir()
            project.mkdir()
            manifest_path = project / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\n", encoding="utf-8")
            log_file = home / "custom.log"

            with mock.patch.dict(os.environ, {"HOME": str(home)}), mock.patch.object(
                os.sys,
                "argv",
                ["secret-tool", "--debug", "--token", "super-secret"],
            ), chdir(project):
                from base_cli.testing import invoke

                result = invoke(
                    app,
                    ["--debug", "--keep-temp", "--log-file", str(log_file), "--token", "super-secret"],
                    home=home,
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(seen["token"], "super-secret")
            self.assertTrue(seen["debug"])
            self.assertTrue(seen["temp_dir"].exists())
            self.assertEqual(seen["log_file"], log_file)
            self.assertEqual(seen["manifest_path"], manifest_path.resolve())
            self.assertEqual(seen["project_root"], project.resolve())

            log_text = log_file.read_text(encoding="utf-8")
            self.assertIn("--token", log_text)
            self.assertIn("[REDACTED]", log_text)
            self.assertNotIn("super-secret", log_text)
            self.assertIn("manifest_path=", log_text)
            self.assertIn("project_root=", log_text)


if __name__ == "__main__":
    unittest.main()
