from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import delegates, engine
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest
from base_setup.tests.helpers import fake_context

class MiseTests(unittest.TestCase):

    def test_mise_dry_run_invokes_mise_install_in_project_root(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            delegates.reconcile_mise(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"[DRY-RUN] Would run in '{project_root.resolve()}': mise install", info_messages)



    def test_mise_invokes_install_in_project_root(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
                "base_setup.process.run_command"
            ) as run_command:
                delegates.reconcile_mise(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["mise", "install"], cwd=project_root.resolve())



    def test_mise_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "mise config '.mise.toml' does not exist"):
                delegates.resolve_mise_path(manifest)



    def test_mise_must_stay_inside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise="../.mise.toml",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "mise must stay inside the project root"):
                delegates.resolve_mise_path(manifest)



    def test_manifest_checks_include_mise_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            default_manifest = BaseManifest(
                path=Path(tmpdir) / "default.yaml",
                project_name="base",
                brewfile=None,
                artifacts=(),
            )
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with mock.patch("base_setup.process.command_exists", return_value=True):
                checks = engine.manifest_checks(default_manifest, manifest)

        self.assertIn("mise", [check.name for check in checks])
        mise_check = next(check for check in checks if check.name == "mise")
        self.assertFalse(mise_check.ok)
        self.assertEqual(mise_check.status, "warn")
        self.assertIn("installed mise tools are not verified", mise_check.message)
        self.assertEqual(mise_check.fix, "Run 'basectl setup demo' to install declared mise tools.")
