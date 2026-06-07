from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from base_setup import build, engine
from base_setup.manifest import BaseManifest, BuildConfig, BuildTargetConfig


def default_manifest(path: Path) -> BaseManifest:
    return BaseManifest(
        path=path,
        project_name="base-defaults",
        brewfile=None,
        artifacts=(),
    )


def build_manifest(
    manifest_path: Path,
    targets: dict[str, BuildTargetConfig],
) -> BaseManifest:
    return BaseManifest(
        path=manifest_path,
        project_name="demo",
        brewfile=None,
        artifacts=(),
        build=BuildConfig(default=tuple(targets), targets=targets),
    )


class BuildDiagnosticsTests(unittest.TestCase):
    def test_check_build_returns_no_checks_without_build_config(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )

        self.assertEqual(build.check_build(manifest), [])

    def test_check_build_target_working_dir_reports_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "services" / "api").mkdir(parents=True)
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir="services/api")},
            )

            check = build.check_build(manifest)[0]

        self.assertTrue(check.ok)
        self.assertEqual(check.finding_id, "BASE-P070")
        self.assertEqual(check.name, "build.targets.api")
        self.assertIn("working directory 'services/api' exists", check.message)

    def test_check_build_target_working_dir_reports_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir="services/api")},
            )

            check = build.check_build(manifest)[0]

        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P070")
        self.assertIn("working directory 'services/api' does not exist", check.message)
        self.assertIn("build.targets.api.working_dir", check.fix)

    def test_check_build_target_working_dir_reports_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "services").mkdir()
            (project_root / "services" / "api").write_text("not a directory\n", encoding="utf-8")
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir="services/api")},
            )

            check = build.check_build(manifest)[0]

        self.assertFalse(check.ok)
        self.assertIn("working directory 'services/api' is not a directory", check.message)

    def test_check_build_target_working_dir_rejects_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir=str(project_root))},
            )

            check = build.check_build(manifest)[0]

        self.assertFalse(check.ok)
        self.assertIn("must be relative to the project root", check.message)

    def test_check_build_target_working_dir_rejects_escaping_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir="../api")},
            )

            check = build.check_build(manifest)[0]

        self.assertFalse(check.ok)
        self.assertIn("resolves outside the project root", check.message)

    def test_manifest_checks_include_build_target_working_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "services" / "api").mkdir(parents=True)
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir="services/api")},
            )

            checks = engine.manifest_checks(default_manifest(Path(tmpdir) / "default.yaml"), manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P070"])
        self.assertTrue(checks[0].ok)

    def test_doctor_manifest_reports_build_target_finding_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = build_manifest(
                project_root / "base_manifest.yaml",
                {"api": BuildTargetConfig(command="go build ./cmd/api", working_dir="services/api")},
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_manifest(default_manifest(Path(tmpdir) / "default.yaml"), manifest, "json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual([finding["id"] for finding in findings], ["BASE-P070"])
        self.assertEqual([finding["name"] for finding in findings], ["build.targets.api"])
        self.assertEqual([finding["status"] for finding in findings], ["error"])
