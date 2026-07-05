from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import delegates
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest
from base_setup.tests.helpers import fake_context


class BrewfileTests(unittest.TestCase):
    def test_delegates_reexports_brewfile_helpers(self) -> None:
        from base_setup import brewfile_delegate

        expected_names = (
            "check_brewfile",
            "homebrew_no_auto_update_env",
            "reconcile_brewfile",
            "resolve_brewfile_path",
        )

        for name in expected_names:
            with self.subTest(name=name):
                self.assertIs(getattr(delegates, name), getattr(brewfile_delegate, name))

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
            timeout_seconds=delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
        self.assertEqual(run_check.call_args.kwargs["env"]["HOMEBREW_NO_AUTO_UPDATE"], "1")

    def test_brewfile_check_warns_when_probe_times_out(self) -> None:
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
                mock.patch(
                    "base_setup.process.run_check",
                    side_effect=subprocess.TimeoutExpired(
                        ["brew", "bundle", "check", f"--file={expected_brewfile}"],
                        delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
                    ),
                ) as run_check,
            ):
                check = delegates.check_brewfile(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-P012")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, "Retry 'basectl doctor demo' or inspect Homebrew with 'brew doctor'.")
        run_check.assert_called_once_with(
            ["brew", "bundle", "check", f"--file={expected_brewfile}"],
            env=mock.ANY,
            timeout_seconds=delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_brewfile_check_warns_and_skips_homebrew_off_macos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text('brew "uv"\n', encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )

            with (
                mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}),
                mock.patch("base_setup.process.command_exists") as command_exists,
                mock.patch("base_setup.process.run_check") as run_check,
            ):
                check = delegates.check_brewfile(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-P011")
        self.assertIn("Brewfile delegates are macOS/Homebrew-only", check.message)
        self.assertIn("linux-debian", check.message)
        command_exists.assert_not_called()
        run_check.assert_not_called()

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
            timeout_seconds=delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
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

    def test_brewfile_setup_skips_homebrew_off_macos(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text('brew "uv"\n', encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            with (
                mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}),
                mock.patch("base_setup.process.command_exists") as command_exists,
                mock.patch("base_setup.process.run_check") as run_check,
                mock.patch("base_setup.process.run_command") as run_command,
            ):
                delegates.reconcile_brewfile(ctx, manifest, dry_run=False)

        command_exists.assert_not_called()
        run_check.assert_not_called()
        run_command.assert_not_called()
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            f"Skipping Brewfile '{expected_brewfile}' on BASE_PLATFORM='linux-debian'; "
            "Brewfile delegates are macOS/Homebrew-only.",
            info_messages,
        )

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
