from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from base_setup import demo, engine
from base_setup.manifest import BaseManifest, DemoConfig
from base_setup.tests.helpers import fake_context


def demo_manifest(manifest_path: Path, script: str) -> BaseManifest:
    return BaseManifest(
        path=manifest_path,
        project_name="demo",
        brewfile=None,
        artifacts=(),
        demo=DemoConfig(script=script, description="Interactive demo"),
    )


class DemoDiagnosticsTests(unittest.TestCase):
    def test_resolve_demo_script_path_returns_executable_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            script = project_root / "demo" / "demo.sh"
            script.parent.mkdir()
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o755)
            manifest = demo_manifest(project_root / "base_manifest.yaml", "./demo/demo.sh")

            resolved = demo.resolve_demo_script_path(manifest)

        self.assertEqual(resolved, script.resolve())

    def test_check_demo_script_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = demo_manifest(project_root / "base_manifest.yaml", "./demo/demo.sh")

            check = demo.check_demo_script(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P061")
        self.assertIn("does not exist", check.message)

    def test_check_demo_script_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "demo").mkdir()
            manifest = demo_manifest(project_root / "base_manifest.yaml", "./demo")

            check = demo.check_demo_script(manifest)

        self.assertFalse(check.ok)
        self.assertIn("is not a file", check.message)

    def test_check_demo_script_rejects_non_executable_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            script = project_root / "demo.sh"
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o644)
            manifest = demo_manifest(project_root / "base_manifest.yaml", "./demo.sh")

            check = demo.check_demo_script(manifest)

        self.assertFalse(check.ok)
        self.assertIn("is not executable", check.message)

    def test_check_demo_script_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = demo_manifest(project_root / "base_manifest.yaml", str(project_root / "demo.sh"))

            check = demo.check_demo_script(manifest)

        self.assertFalse(check.ok)
        self.assertIn("must be relative to the project root", check.message)

    def test_check_demo_script_rejects_paths_that_escape_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()
            manifest = demo_manifest(project_root / "base_manifest.yaml", "../demo.sh")

            check = demo.check_demo_script(manifest)

        self.assertFalse(check.ok)
        self.assertIn("must stay inside the project root", check.message)

    def test_check_manifest_reports_demo_declaration_and_script(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            script = project_root / "demo.sh"
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o755)
            manifest = demo_manifest(project_root / "base_manifest.yaml", "./demo.sh")
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        checks = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual([check["name"] for check in checks], ["demo declaration", "demo script"])
        self.assertTrue(all(check["ok"] for check in checks))

    def test_doctor_manifest_reports_demo_finding_ids(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            script = project_root / "demo.sh"
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o644)
            manifest = demo_manifest(project_root / "base_manifest.yaml", "./demo.sh")
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual([finding["id"] for finding in findings], ["BASE-P060", "BASE-P061"])
        self.assertEqual([finding["status"] for finding in findings], ["ok", "error"])
