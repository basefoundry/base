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
