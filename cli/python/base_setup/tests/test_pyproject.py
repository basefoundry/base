from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_setup.manifest import BaseManifest
from base_setup.pyproject import check_pyproject


def manifest_at(path: Path) -> BaseManifest:
    return BaseManifest(
        path=path,
        project_name="demo",
        brewfile=None,
        artifacts=(),
    )


class PyprojectDiagnosticsTests(unittest.TestCase):
    def test_missing_pyproject_produces_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = manifest_at(Path(tmpdir) / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual(checks, ())

    def test_valid_project_metadata_reports_name_and_requires_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "demo-python"',
                        'requires-python = ">=3.11"',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].finding_id, "BASE-P140")
        self.assertTrue(checks[0].ok)
        self.assertEqual(checks[0].status, "")
        self.assertIn("demo-python", checks[0].message)
        self.assertIn(">=3.11", checks[0].message)

    def test_malformed_pyproject_warns_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project\n", encoding="utf-8")
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].finding_id, "BASE-P141")
        self.assertFalse(checks[0].ok)
        self.assertEqual(checks[0].status, "warn")
        self.assertIn("not readable TOML", checks[0].message)

    def test_dependency_metadata_warns_without_listing_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "demo-python"',
                        'dependencies = ["requests @ https://user:secret@example.invalid/pkg.whl"]',
                        "",
                        "[project.optional-dependencies]",
                        'dev = ["pytest"]',
                        "",
                        "[dependency-groups]",
                        'lint = ["ruff"]',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P140", "BASE-P142"])
        dependency_check = checks[1]
        self.assertFalse(dependency_check.ok)
        self.assertEqual(dependency_check.status, "warn")
        self.assertIn("dependency metadata", dependency_check.message)
        self.assertNotIn("secret", dependency_check.message)
        self.assertNotIn("example.invalid", dependency_check.message)

    def test_tool_base_warns_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "demo-python"',
                        "",
                        "[tool.base]",
                        'command = "pytest"',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P140", "BASE-P143"])
        tool_base_check = checks[1]
        self.assertFalse(tool_base_check.ok)
        self.assertEqual(tool_base_check.status, "warn")
        self.assertIn("[tool.base]", tool_base_check.message)
