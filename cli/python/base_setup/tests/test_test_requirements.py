from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup.manifest import read_manifest
from base_setup.manifest_model import BaseManifest
from base_setup.manifest_model import TestConfig as ManifestTestConfig
from base_setup.test_requirements import check_test_requirements
from base_setup.test_requirements import read_test_requirements
from base_setup.test_requirements import reconcile_test_requirements
from base_setup.test_requirements import resolve_test_requirements_path
from base_setup.test_requirements import requirements_file_digest
from base_setup.tests.helpers import fake_context


class TestRequirementsTests(unittest.TestCase):
    @staticmethod
    def write_manifest(root: Path, requirements: str = "requirements-dev.txt"):
        manifest_path = root / "base_manifest.yaml"
        manifest_path.write_text(
            "project:\n"
            "  name: demo\n"
            "test:\n"
            "  command: pytest tests/\n"
            f"  requirements: {requirements}\n"
            "artifacts: []\n",
            encoding="utf-8",
        )
        return read_manifest(manifest_path)

    def test_reads_direct_exact_and_unpinned_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.write_manifest(root)
            (root / "requirements-dev.txt").write_text(
                "pytest==9.0.3\njsonschema\n# comment\n",
                encoding="utf-8",
            )

            path, requirements = read_test_requirements(manifest) or (None, ())

        self.assertEqual(path, (root / "requirements-dev.txt").resolve())
        self.assertEqual(
            [(item.name, item.version) for item in requirements],
            [("pytest", "9.0.3"), ("jsonschema", "latest")],
        )

    def test_rejects_requirements_outside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            root.mkdir()
            manifest = self.write_manifest(root, "../requirements.txt")

            with self.assertRaisesRegex(RuntimeError, "inside the project root"):
                resolve_test_requirements_path(manifest)

    def test_rejects_unsupported_requirements_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.write_manifest(root)
            (root / "requirements-dev.txt").write_text("-r other.txt\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "unsupported requirement syntax"):
                read_test_requirements(manifest)

    def test_check_reports_missing_test_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.write_manifest(root)
            (root / "requirements-dev.txt").write_text("jsonschema==4.25.1\n", encoding="utf-8")
            (root / ".venv" / "bin").mkdir(parents=True)
            (root / ".venv" / "bin" / "python").touch()

            with mock.patch("base_setup.test_requirements.python_artifact_installed", return_value=False):
                check = check_test_requirements(manifest)

        assert check is not None
        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P181")
        self.assertIn("jsonschema==4.25.1", check.message)
        self.assertIn("basectl setup demo", check.fix)

    def test_check_passes_and_reports_requirements_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.write_manifest(root)
            requirements_path = root / "requirements-dev.txt"
            requirements_path.write_text("jsonschema==4.25.1\n", encoding="utf-8")
            (root / ".venv" / "bin").mkdir(parents=True)
            (root / ".venv" / "bin" / "python").touch()

            with mock.patch("base_setup.test_requirements.python_artifact_installed", return_value=True):
                check = check_test_requirements(manifest)

            digest = requirements_file_digest(manifest)

        assert check is not None
        self.assertTrue(check.ok)
        self.assertEqual(check.finding_id, "BASE-P181")
        self.assertEqual(check.details["sha256"], digest)
        self.assertIsInstance(digest, str)

    def test_reconcile_dry_run_plans_install_from_declared_requirements(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            requirements_path = root / "requirements-dev.txt"
            requirements_path.write_text("jsonschema==4.25.1\n", encoding="utf-8")
            manifest = BaseManifest(
                path=root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                test=ManifestTestConfig(command="pytest", requirements="requirements-dev.txt"),
            )

            with (
                mock.patch("base_setup.test_requirements.create_project_virtualenv") as create_virtualenv,
                mock.patch("base_setup.test_requirements.process.dry_run_command") as dry_run_command,
            ):
                reconcile_test_requirements(ctx, manifest, dry_run=True)

        expected_root = root.resolve()
        expected_venv = expected_root / ".venv"
        create_virtualenv.assert_called_once_with(ctx, expected_venv, None)
        dry_run_command.assert_called_once_with(
            ctx,
            [
                str(expected_venv / "bin" / "python"),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements_path.resolve()),
            ],
            cwd=expected_root,
        )
