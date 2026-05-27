from __future__ import annotations

import importlib.util
import io
import logging
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from unittest import mock

import base_cli
from base_cli import config as config_module
from base_cli.config import load_config
from base_cli.logging import BaseCliFormatter
from base_cli.paths import base_cache_root, base_state_root, discover_manifest, normalize_cli_name
from base_cli.redaction import redact_argv


@contextmanager
def change_directory(path: Path):
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


class BaseCliTests(unittest.TestCase):
    @staticmethod
    def make_context(tmpdir: str) -> tuple[base_cli.Context, mock.Mock]:
        root = Path(tmpdir)
        temp_dir = root / "tmp"
        temp_dir.mkdir()
        log = mock.Mock()
        log.handlers = []
        context = base_cli.Context(
            cli_name="demo",
            run_id="run",
            state_dir=root / "state",
            log_dir=root / "logs",
            cache_dir=root / "cache",
            temp_dir=temp_dir,
            log_file=root / "logs" / "run.log",
            config={},
            environment="dev",
            debug=False,
            keep_temp=False,
            log=log,
        )
        return context, log

    def test_import_has_no_runtime_directory_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}):
                self.assertFalse((home / ".base.d").exists())
                self.assertFalse((home / "Library" / "Caches" / "base").exists())

    def test_path_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            (root / "base_manifest.yaml").write_text("project:\n  name: demo\n", encoding="utf-8")

            self.assertEqual(base_state_root(root), root / ".base.d")
            self.assertEqual(normalize_cli_name("/tmp/demo.py"), "demo")
            self.assertEqual(discover_manifest(nested), (root / "base_manifest.yaml").resolve())

    def test_base_cache_root_uses_macos_cache_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with mock.patch("base_cli.paths.sys.platform", "darwin"):
                self.assertEqual(base_cache_root(root), root / "Library" / "Caches" / "base")

    def test_base_cache_root_uses_xdg_cache_directory_off_macos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with mock.patch("base_cli.paths.sys.platform", "linux"):
                self.assertEqual(base_cache_root(root), root / ".cache" / "base")

    def test_base_cache_root_honors_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(root / "custom-cache")}):
                self.assertEqual(base_cache_root(root), root / "custom-cache")

    def test_redacts_sensitive_option_values(self) -> None:
        argv = ["tool", "--api-key", "secret", "--token=hidden", "--name", "visible"]

        self.assertEqual(
            redact_argv(argv, {"api_key", "token"}),
            ["tool", "--api-key", "[REDACTED]", "--token=[REDACTED]", "--name", "visible"],
        )

    def test_log_source_fallback_uses_resolved_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_home = root / "base-home"
            cwd = root / "cwd"
            external = root / "external" / "same_name.py"
            base_home.mkdir()
            cwd.mkdir()
            external.parent.mkdir()
            external.write_text("# test\n", encoding="utf-8")
            record = logging.LogRecord(
                name="base_cli.test",
                level=logging.INFO,
                pathname=str(external),
                lineno=7,
                msg="hello",
                args=(),
                exc_info=None,
            )

            with mock.patch.dict(os.environ, {"BASE_HOME": str(base_home)}), change_directory(cwd):
                formatted = BaseCliFormatter().format(record)

        self.assertIn(f"{external.resolve()}:7 hello", formatted)

    def test_config_precedence_excludes_implicit_system_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            project = root / "project"
            explicit = root / "explicit.yaml"
            home_config = home / ".base.d" / "config.yaml"
            project_config = project / ".base" / "config.yaml"
            home_config.parent.mkdir(parents=True)
            project_config.parent.mkdir(parents=True)
            home_config.write_text("environment: user\nlog_level: info\n", encoding="utf-8")
            project_config.write_text("environment: project\n", encoding="utf-8")
            explicit.write_text("log_level: warning\n", encoding="utf-8")

            original_load_yaml_file = config_module.load_yaml_file

            def load_without_system_config(path: Path) -> dict:
                if path == Path("/etc/base.d/config.yaml"):
                    raise AssertionError("system config should not be loaded")
                return original_load_yaml_file(path)

            with mock.patch.dict(os.environ, {"BASE_CLI_ENVIRONMENT": "env"}), mock.patch(
                "base_cli.config.load_yaml_file",
                side_effect=load_without_system_config,
            ):
                config = load_config(project, explicit, home=home)

        self.assertEqual(config["environment"], "env")
        self.assertEqual(config["log_level"], "warning")

    def test_log_debug_enables_python_debug_logging(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"LOG_DEBUG": "1"}):
                config = load_config(None, None, home=Path(tmpdir))

        self.assertEqual(config["log_level"], "debug")

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
            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}):
                from base_cli.testing import invoke

                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    result = invoke(app, ["--name", "Ada"], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(seen["name"], "Ada")
            self.assertFalse(seen["temp_dir"].exists())
            self.assertTrue(seen["cache_dir"].is_dir())
            log_dir = home / "Library" / "Caches" / "base" / "cli" / "demo" / "logs"
            self.assertTrue(log_dir.is_dir())
            log_files = tuple(log_dir.glob("*.log"))
            self.assertEqual(len(log_files), 1)
            self.assertEqual(log_files[0].stat().st_mode & 0o777, 0o600)
            self.assertFalse((home / ".base.d" / "cli").exists())
            self.assertRegex(result.stderr, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO\s+")
            self.assertIn("hello Ada", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_testing_invoke_captures_stderr_separately(self) -> None:
        app = base_cli.App(name="streams", version="0.1.0")

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            print("stdout text")
            ctx.log.info("stderr text")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}):
                from base_cli.testing import invoke

                result = invoke(app, [], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("stdout text", result.stdout)
        self.assertNotIn("stderr text", result.stdout)
        self.assertIn("stderr text", result.stderr)

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

            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}), mock.patch.object(
                os.sys,
                "argv",
                ["secret-tool", "--debug", "--token", "super-secret"],
            ), change_directory(project):
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
            self.assertEqual(
                seen["temp_dir"].parents[1],
                home / "Library" / "Caches" / "base" / "cli" / "secret-tool",
            )
            self.assertEqual(seen["manifest_path"], manifest_path.resolve())
            self.assertEqual(seen["project_root"], project.resolve())

            log_text = log_file.read_text(encoding="utf-8")
            self.assertEqual(log_file.stat().st_mode & 0o777, 0o600)
            self.assertIn("--token", log_text)
            self.assertIn("[REDACTED]", log_text)
            self.assertNotIn("super-secret", log_text)
            self.assertIn("manifest_path=", log_text)
            self.assertIn("project_root=", log_text)

    def test_cleanup_continues_after_hook_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            context, log = self.make_context(tmpdir)
            calls = []

            def failing_hook() -> None:
                calls.append("failing")
                raise RuntimeError("hook exploded")

            def later_hook() -> None:
                calls.append("later")

            context.on_cleanup(failing_hook)
            context.on_cleanup(later_hook)

            context.cleanup()

            self.assertEqual(calls, ["failing", "later"])
            self.assertFalse(context.temp_dir.exists())
            log.warning.assert_any_call("Cleanup hook failed: %s", mock.ANY)

    def test_cleanup_logs_temp_removal_failure_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            context, log = self.make_context(tmpdir)

            with mock.patch("base_cli.context.shutil.rmtree", side_effect=OSError("permission denied")):
                context.cleanup()

            log.warning.assert_any_call(
                "Temp directory cleanup failed for '%s': %s",
                context.temp_dir,
                mock.ANY,
            )

    def test_cleanup_removes_handler_after_flush_and_close_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            context, log = self.make_context(tmpdir)
            handler = mock.Mock()
            handler.flush.side_effect = RuntimeError("flush exploded")
            handler.close.side_effect = RuntimeError("close exploded")
            log.handlers = [handler]

            context.cleanup()

            log.removeHandler.assert_called_once_with(handler)
            self.assertEqual(log.warning.call_count, 2)


if __name__ == "__main__":
    unittest.main()
