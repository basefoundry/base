from __future__ import annotations

import io
import importlib
import importlib.util
import json
import os
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_dev import engine
from base_dev.engine import main


def run_engine(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(os.environ, {"HOME": home_dir, "BASE_HOME": str(Path(__file__).resolve().parents[4])}):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class DevManifestTests(unittest.TestCase):
    def test_importing_main_module_does_not_execute_main(self) -> None:
        sys.modules.pop("base_dev.__main__", None)

        with mock.patch("base_dev.engine.main", side_effect=AssertionError("main should not run on import")):
            module = importlib.import_module("base_dev.__main__")

        self.assertEqual(module.__name__, "base_dev.__main__")

    def test_running_module_dispatches_to_main(self) -> None:
        sys.modules.pop("base_dev.__main__", None)

        with mock.patch("base_dev.engine.main", return_value=7) as main_mock:
            with self.assertRaises(SystemExit) as exc:
                runpy.run_module("base_dev", run_name="__main__", alter_sys=True)

        self.assertEqual(exc.exception.code, 7)
        main_mock.assert_called_once_with()

    def test_dev_manifest_declares_supported_developer_tools(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        artifacts = {(artifact.artifact_type, artifact.name, artifact.version) for artifact in manifest.artifacts}

        self.assertIn(("tool", "bats-core", "latest"), artifacts)
        self.assertIn(("tool", "gh", "latest"), artifacts)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_manifest_artifacts(self) -> None:
        with mock.patch("base_dev.engine.run_check", return_value=False):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        self.assertEqual(status, 1)
        self.assertIn('"name": "bats-core"', stdout)
        self.assertIn('"ok": false', stdout)
        self.assertIn('"name": "gh"', stdout)
        self.assertEqual(stderr, "")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_invalid_github_auth_when_gh_is_installed(self) -> None:
        def fake_run_check(command: list[str]) -> bool:
            if command == ["brew", "list", "bats-core"]:
                return True
            if command == ["brew", "list", "gh"]:
                return True
            if command == ["gh", "auth", "status"]:
                return False
            raise AssertionError(f"Unexpected command: {command}")

        with mock.patch("base_dev.engine.run_check", side_effect=fake_run_check):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        findings = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(
            {
                "name": "gh-auth",
                "ok": False,
                "message": "GitHub CLI authentication is not ready.",
                "fix": "gh auth login -h github.com",
            },
            findings,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_dry_run_uses_homebrew_registry_definitions(self) -> None:
        status, _stdout, stderr = run_engine(["setup", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install bats-core", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install gh", stderr)

    def test_doctor_returns_number_of_failed_manifest_artifacts(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        with mock.patch("base_dev.engine.run_check", return_value=False):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 2)
        self.assertIn("error", stdout.getvalue())
        self.assertIn("Fix: basectl setup --dev", stdout.getvalue())

    def test_doctor_reports_invalid_github_auth(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        def fake_run_check(command: list[str]) -> bool:
            if command == ["brew", "list", "bats-core"]:
                return True
            if command == ["brew", "list", "gh"]:
                return True
            if command == ["gh", "auth", "status"]:
                return False
            raise AssertionError(f"Unexpected command: {command}")

        with mock.patch("base_dev.engine.run_check", side_effect=fake_run_check):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 1)
        self.assertIn("gh-auth", stdout.getvalue())
        self.assertIn("GitHub CLI authentication is not ready.", stdout.getvalue())
        self.assertIn("Fix: gh auth login -h github.com", stdout.getvalue())

    def test_doctor_supports_json_output(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        with mock.patch("base_dev.engine.run_check", return_value=False):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(findings[0]["status"], "error")
        self.assertEqual(findings[0]["fix"], "basectl setup --dev")

    def test_doctor_warning_status_does_not_fail(self) -> None:
        check = engine.DevCheck(
            name="optional-tool",
            ok=False,
            message="Optional developer tool is not installed.",
            fix="brew install optional-tool",
            status="warn",
        )

        self.assertEqual(engine.doctor_status(check), "warn")
        self.assertEqual(engine.check_to_doctor_json(check)["status"], "warn")

        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)
        with mock.patch("base_dev.engine.check_homebrew_artifact", return_value=check):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 0)
        self.assertIn("warn", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
