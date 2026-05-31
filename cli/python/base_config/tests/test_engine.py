from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_cli.config import user_config_path
from base_config import engine


class BaseConfigCommandTests(unittest.TestCase):
    def test_safe_resolve_returns_resolved_existing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.yaml"
            path.write_text("ide: {}\n", encoding="utf-8")

            resolved = engine.safe_resolve(path)

        self.assertEqual(resolved, path.resolve())

    def test_safe_resolve_handles_missing_path_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing" / "config.yaml"

            resolved = engine.safe_resolve(path)

        self.assertEqual(resolved, path.resolve(strict=False))

    def test_safe_resolve_resolves_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.yaml"
            symlink = Path(tmpdir) / "config.yaml"
            target.write_text("ide: {}\n", encoding="utf-8")
            symlink.symlink_to(target)

            resolved = engine.safe_resolve(symlink)

        self.assertEqual(resolved, target.resolve())

    def test_print_finding_formats_status_name_and_message(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            engine.print_finding("warn", "file", "Config file is missing.")

        self.assertEqual(stdout.getvalue(), "warn   file          Config file is missing.\n")

    def test_show_config_prints_empty_mapping_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.show_config_command()

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {})

    def test_show_config_prints_parsed_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(Path(tmpdir))
                path.parent.mkdir(parents=True)
                path.write_text("ide:\n  enabled: true\n", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.show_config_command()

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"ide": {"enabled": True}})

    def test_show_config_reports_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(Path(tmpdir))
                path.parent.mkdir(parents=True)
                path.write_text("ide: [unterminated\n", encoding="utf-8")
                with redirect_stderr(io.StringIO()):
                    status = engine.show_config_command()

        self.assertEqual(status, 1)

    def test_doctor_config_reports_missing_file_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        output = stdout.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("Base config doctor", output)
        self.assertIn("warn", output)
        self.assertIn("Config file is missing", output)

    def test_doctor_config_reports_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(Path(tmpdir))
                path.parent.mkdir(parents=True)
                path.write_text("ide:\n  enabled: true\n", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        output = stdout.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("Config YAML is valid", output)
        self.assertIn("Config contains 1 top-level key", output)
        self.assertIn("workspace.root is not configured", output)

    def test_doctor_config_reports_configured_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "work"
            workspace.mkdir()
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(root)
                path.parent.mkdir(parents=True)
                path.write_text(f"workspace:\n  root: {workspace}\n", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        output = stdout.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("workspace.root points to", output)
        self.assertIn(str(workspace), output)

    def test_doctor_config_reports_invalid_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(root)
                path.parent.mkdir(parents=True)
                path.write_text("workspace:\n  root: work\n", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        self.assertEqual(status, 1)
        self.assertIn("workspace.root must be an absolute path", stdout.getvalue())

    def test_doctor_config_reports_broken_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(Path(tmpdir))
                path.parent.mkdir(parents=True)
                target = path.parent / "missing-config.yaml"
                path.symlink_to(target)
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        output = stdout.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("warn", output)
        self.assertIn("broken symlink", output)
        self.assertIn(str(target), output)

    def test_doctor_config_reports_unexpected_top_level_keys_as_valid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(Path(tmpdir))
                path.parent.mkdir(parents=True)
                path.write_text("unexpected: true\nide:\n  enabled: true\n", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        output = stdout.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("Config YAML is valid", output)
        self.assertIn("Config contains 2 top-level key", output)

    def test_doctor_config_reports_invalid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                path = user_config_path(Path(tmpdir))
                path.parent.mkdir(parents=True)
                path.write_text("ide: [unterminated\n", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_config_command()

        self.assertEqual(status, 1)
        self.assertIn("error", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
