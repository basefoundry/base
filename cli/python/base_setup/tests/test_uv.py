from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import engine
from base_setup.manifest import ArtifactRequest, BaseManifest, read_manifest
from base_setup.tests.helpers import fake_context
from base_setup.uv import check_uv, reconcile_uv_project


def write_manifest(root: Path, content: str) -> BaseManifest:
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "base_manifest.yaml"
    manifest_path.write_text(content, encoding="utf-8")
    return read_manifest(manifest_path)


class UvProjectTests(unittest.TestCase):
    def test_reconcile_uv_project_dry_run_delegates_to_uv_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts: []",
                    ]
                ),
            )
            ctx = fake_context()

            reconcile_uv_project(ctx, manifest, dry_run=True)

        ctx.log.info.assert_any_call("[DRY-RUN] Would run in '%s': %s", root, "uv sync")

    def test_reconcile_uv_project_requires_uv_for_real_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = write_manifest(
                Path(tmpdir),
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts: []",
                    ]
                ),
            )
            ctx = fake_context()

            with mock.patch("base_setup.uv.process.command_exists", return_value=False):
                with self.assertRaisesRegex(RuntimeError, "uv is required"):
                    reconcile_uv_project(ctx, manifest, dry_run=False)

    def test_check_uv_warns_for_missing_uv_manager_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts: []",
                    ]
                ),
            )

            with mock.patch("base_setup.uv.process.command_exists", return_value=False):
                checks = check_uv(manifest)

        missing_uv = [check for check in checks if check.finding_id == "BASE-P150"]
        self.assertEqual(len(missing_uv), 1)
        self.assertEqual(missing_uv[0].status, "warn")
        self.assertIn("uv is not available", missing_uv[0].message)

    def test_check_uv_warns_for_runner_without_python_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "commands:",
                        "  audit:",
                        "    command: pytest tests/audit",
                        "    runner: uv",
                        "artifacts: []",
                    ]
                ),
            )

            with mock.patch("base_setup.uv.process.command_exists", return_value=False):
                checks = check_uv(manifest)

        missing_uv = [check for check in checks if check.finding_id == "BASE-P150"]
        self.assertEqual(len(missing_uv), 1)
        self.assertIn("uv runner", missing_uv[0].message)

    def test_check_uv_reports_project_files_and_stale_base_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            home = Path(tmpdir) / "home"
            stale_venv = home / ".base.d" / "demo" / ".venv"
            stale_venv.mkdir(parents=True)
            manifest = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts: []",
                    ]
                ),
            )
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {"HOME": str(home)}), mock.patch(
                "base_setup.uv.process.command_exists",
                return_value=True,
            ):
                checks = check_uv(manifest)

        findings = {check.finding_id: check for check in checks}
        self.assertEqual(findings["BASE-P151"].status, "")
        self.assertEqual(findings["BASE-P152"].status, "warn")
        self.assertEqual(findings["BASE-P153"].status, "warn")
        self.assertIn(str(stale_venv), findings["BASE-P153"].message)

    def test_uv_project_setup_skips_python_package_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(ArtifactRequest("python-package", "click", "8.4.1"),),
            )
            manifest = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts:",
                        "  - type: python-package",
                        "    name: requests",
                        "    version: latest",
                    ]
                ),
            )
            ctx = fake_context()

            with mock.patch("base_setup.engine.reconcile_uv_project") as reconcile_uv, mock.patch(
                "base_setup.engine.reconcile_artifacts"
            ) as reconcile_artifacts:
                engine.reconcile_manifest(ctx, default_manifest, manifest, dry_run=True)

        reconcile_uv.assert_called_once_with(ctx, manifest, dry_run=True)
        reconcile_artifacts.assert_not_called()
