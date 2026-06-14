from __future__ import annotations

# pylint: disable=too-many-public-methods

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
from base_cli.config import load_config, load_user_config, read_user_config, user_config_path
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
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": ""}), mock.patch(
                "base_cli.paths.sys.platform",
                "darwin",
            ):
                self.assertEqual(base_cache_root(root), root / "Library" / "Caches" / "base")

    def test_base_cache_root_uses_xdg_cache_directory_off_macos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": ""}), mock.patch(
                "base_cli.paths.sys.platform",
                "linux",
            ):
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

    def test_user_config_path_defaults_to_base_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            self.assertEqual(user_config_path(home), home / ".base.d" / "config.yaml")

    def test_load_user_config_missing_file_returns_empty_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_user_config(Path(tmpdir))

        self.assertEqual(config, {})

    def test_load_user_config_reads_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("ide:\n  enabled: true\n", encoding="utf-8")

            config = load_user_config(home)

        self.assertEqual(config, {"ide": {"enabled": True}})

    def test_load_user_config_rejects_non_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("- not\n- mapping\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must contain a YAML mapping"):
                load_user_config(home)

    def test_load_user_config_rejects_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("ide: [unterminated\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "contains invalid YAML"):
                load_user_config(home)

    def test_read_user_config_missing_file_returns_empty_ide_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = read_user_config(Path(tmpdir))

        self.assertEqual(config.raw, {})
        self.assertIsNone(config.workspace.root)
        self.assertIsNone(config.ide.enabled)
        self.assertEqual(config.ide.preferences, {})

    def test_read_user_config_parses_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            workspace = home / "work"
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text(f"workspace:\n  root: {workspace}\n", encoding="utf-8")

            config = read_user_config(home)

        self.assertEqual(config.workspace.root, workspace.resolve(strict=False))

    def test_read_user_config_rejects_non_mapping_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("workspace: true\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "workspace must be a mapping"):
                read_user_config(home)

    def test_read_user_config_rejects_relative_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("workspace:\n  root: work\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "workspace.root must be an absolute path"):
                read_user_config(home)

    def test_read_user_config_parses_ide_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text(
                "\n".join(
                    [
                        "ide:",
                        "  enabled: true",
                        "  vscode:",
                        "    enabled: true",
                        "    install: false",
                        "    extra_extensions:",
                        "      - eamodio.gitlens",
                        "      - github.copilot",
                        "    settings:",
                        "      editor.fontSize: 14",
                        "      editor.minimap.enabled: false",
                        "  cursor:",
                        "    enabled: false",
                    ]
                ),
                encoding="utf-8",
            )

            config = read_user_config(home)

        self.assertTrue(config.ide.enabled)
        vscode = config.ide.preferences["vscode"]
        self.assertTrue(vscode.enabled)
        self.assertFalse(vscode.install)
        self.assertEqual(vscode.extra_extensions, ("eamodio.gitlens", "github.copilot"))
        self.assertEqual(
            vscode.settings,
            {
                "editor.fontSize": 14,
                "editor.minimap.enabled": False,
            },
        )
        self.assertFalse(config.ide.preferences["cursor"].enabled)
        self.assertIsNone(config.ide.preferences["cursor"].install)

    def test_read_user_config_rejects_non_mapping_ide(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("ide: true\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ide must be a mapping"):
                read_user_config(home)

    def test_read_user_config_rejects_unknown_ide_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text(
                "\n".join(
                    [
                        "ide:",
                        "  windswept:",
                        "    enabled: true",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported ide keys: windswept"):
                read_user_config(home)

    def test_read_user_config_rejects_non_boolean_ide_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("ide:\n  enabled: sometimes\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ide.enabled must be a boolean"):
                read_user_config(home)

    def test_read_user_config_rejects_non_boolean_per_ide_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("ide:\n  vscode:\n    install: maybe\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ide.vscode.install must be a boolean"):
                read_user_config(home)

    def test_read_user_config_rejects_invalid_extra_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text(
                "\n".join(
                    [
                        "ide:",
                        "  cursor:",
                        "    extra_extensions:",
                        "      - github.copilot",
                        "      - 17",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, r"ide.cursor.extra_extensions\[2\]"):
                read_user_config(home)

    def test_read_user_config_rejects_non_mapping_ide_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("ide:\n  vscode:\n    settings: true\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ide.vscode.settings must be a mapping"):
                read_user_config(home)

    def test_log_debug_enables_python_debug_logging(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"LOG_DEBUG": "1"}):
                config = load_config(None, None, home=Path(tmpdir))

        self.assertEqual(config["log_level"], "debug")

    def test_exit_code_constants_match_base_conventions(self) -> None:
        from base_cli import ExitCode

        self.assertEqual(ExitCode.SUCCESS, 0)
        self.assertEqual(ExitCode.FAILURE, 1)
        self.assertEqual(ExitCode.USAGE_ERROR, 2)
        self.assertIs(ExitCode, base_cli.ExitCode)

    def test_app_rejects_duplicate_command_registration(self) -> None:
        app = base_cli.App(name="demo")

        @app.command()
        def first(ctx: base_cli.Context) -> None:
            del ctx

        with self.assertRaisesRegex(
            RuntimeError,
            "App 'demo' already has a registered command.*subcommands",
        ):
            @app.command()
            def second(ctx: base_cli.Context) -> None:
                del ctx

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
                log_dir = base_cache_root(home) / "cli" / "demo" / "logs"
                self.assertTrue(log_dir.is_dir())
                log_files = tuple(log_dir.glob("*.log"))
                self.assertEqual(len(log_files), 1)
                self.assertEqual(log_files[0].stat().st_mode & 0o777, 0o600)
                self.assertFalse((home / ".base.d" / "cli").exists())
                self.assertRegex(result.stderr, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO\s+")
                self.assertIn("hello Ada", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_dry_run_avoids_default_cache_writes(self) -> None:
        app = base_cli.App(name="dry-run-demo", version="0.1.0")
        seen = {}

        @app.command()
        @base_cli.option("--dry-run", is_flag=True)
        def main(ctx: base_cli.Context, dry_run: bool) -> None:
            seen["dry_run"] = dry_run
            seen["temp_dir"] = ctx.temp_dir
            seen["cache_dir"] = ctx.cache_dir
            seen["log_dir"] = ctx.log_dir
            seen["log_file"] = ctx.log_file
            ctx.log.info("dry run")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}):
                from base_cli.testing import invoke

                result = invoke(app, ["--dry-run"], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(seen["dry_run"])
            self.assertIsNone(seen["log_file"])
            self.assertFalse(seen["temp_dir"].exists())
            self.assertFalse(seen["cache_dir"].exists())
            self.assertFalse(seen["log_dir"].exists())
            self.assertFalse((home / "Library" / "Caches" / "base").exists())
            self.assertIn("dry run", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_can_disable_default_persistent_logging(self) -> None:
        app = base_cli.App(name="inspect-logs", log_to_file=False)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["log_file"] = ctx.log_file
            seen["state_dir"] = ctx.state_dir
            seen["cache_dir"] = ctx.cache_dir
            seen["temp_dir"] = ctx.temp_dir
            ctx.log.debug("debug without persistent log")
            ctx.log.info("info without persistent log")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}):
                from base_cli.testing import invoke

                result = invoke(app, ["--debug"], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIsNone(seen["log_file"])
            self.assertFalse(seen["state_dir"].exists())
            self.assertFalse(seen["cache_dir"].exists())
            self.assertFalse(seen["temp_dir"].exists())
            self.assertFalse((home / "Library" / "Caches" / "base").exists())
            self.assertIn("debug without persistent log", result.stderr)
            self.assertIn("info without persistent log", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_dry_run_honors_explicit_log_file_without_cache_dirs(self) -> None:
        app = base_cli.App(name="dry-run-log-demo", version="0.1.0")
        seen = {}

        @app.command()
        @base_cli.option("--dry-run", is_flag=True)
        def main(ctx: base_cli.Context, dry_run: bool) -> None:
            seen["dry_run"] = dry_run
            seen["temp_dir"] = ctx.temp_dir
            seen["cache_dir"] = ctx.cache_dir
            seen["log_file"] = ctx.log_file
            ctx.log.info("dry run with log")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_file = home / "logs" / "dry-run.log"
            with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_CACHE_DIR": ""}):
                from base_cli.testing import invoke

                result = invoke(app, ["--dry-run", "--log-file", str(log_file)], home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(seen["dry_run"])
            self.assertEqual(seen["log_file"], log_file)
            self.assertTrue(log_file.is_file())
            self.assertEqual(log_file.stat().st_mode & 0o777, 0o600)
            self.assertFalse(seen["temp_dir"].exists())
            self.assertFalse(seen["cache_dir"].exists())
            self.assertFalse((home / "Library" / "Caches" / "base").exists())
            self.assertIn("dry run with log", log_file.read_text(encoding="utf-8"))

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
                    base_cache_root(home) / "cli" / "secret-tool",
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
