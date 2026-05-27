from __future__ import annotations

import io
import importlib.util
import json
import os
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


if __name__ == "__main__":
    unittest.main()
