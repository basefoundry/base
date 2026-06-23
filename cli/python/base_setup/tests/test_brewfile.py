from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import delegates
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest
from base_setup.tests.helpers import fake_context


class BrewfileTests(unittest.TestCase):

    def test_brewfile_dry_run_invokes_brew_bundle(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text("brew \"jq\"\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            delegates.reconcile_brewfile(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"[DRY-RUN] Would run: brew bundle --file={expected_brewfile}", info_messages)

    def test_brewfile_check_disables_homebrew_auto_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text("brew \"jq\"\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            with (
                mock.patch("base_setup.process.command_exists", return_value=True),
                mock.patch("base_setup.process.run_check", return_value=True) as run_check,
            ):
                check = delegates.check_brewfile(manifest)

        self.assertTrue(check.ok)
        run_check.assert_called_once_with(
            ["brew", "bundle", "check", f"--file={expected_brewfile}"],
            env=mock.ANY,
        )
        self.assertEqual(run_check.call_args.kwargs["env"]["HOMEBREW_NO_AUTO_UPDATE"], "1")

    def test_brewfile_skips_brew_bundle_when_dependencies_are_satisfied(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text("brew \"jq\"\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            with (
                mock.patch("base_setup.process.command_exists", return_value=True),
                mock.patch("base_setup.process.run_check", return_value=True) as run_check,
                mock.patch("base_setup.process.run_command") as run_command,
            ):
                delegates.reconcile_brewfile(ctx, manifest, dry_run=False)

        run_check.assert_called_once_with(
            ["brew", "bundle", "check", f"--file={expected_brewfile}"],
            env=mock.ANY,
        )
        self.assertEqual(run_check.call_args.kwargs["env"]["HOMEBREW_NO_AUTO_UPDATE"], "1")
        run_command.assert_not_called()
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"Brewfile dependencies are already satisfied for '{expected_brewfile}'.", info_messages)

    def test_brewfile_invokes_brew_bundle_when_dependencies_are_missing(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text("brew \"jq\"\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            with (
                mock.patch("base_setup.process.command_exists", return_value=True),
                mock.patch("base_setup.process.run_check", return_value=False),
                mock.patch("base_setup.process.run_command") as run_command,
            ):
                delegates.reconcile_brewfile(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(
            ctx,
            ["brew", "bundle", f"--file={expected_brewfile}"],
            env=mock.ANY,
        )
        self.assertEqual(run_command.call_args.kwargs["env"]["HOMEBREW_NO_AUTO_UPDATE"], "1")

    def test_brewfile_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "does not exist"):
                delegates.resolve_brewfile_path(manifest)
    def test_brewfile_must_stay_inside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="../Brewfile",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "must stay inside the project root"):
                delegates.resolve_brewfile_path(manifest)
