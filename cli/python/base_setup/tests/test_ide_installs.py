from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from base_setup import engine, ide
from base_setup.manifest import BaseManifest, IdeConfig
from base_setup.tests.helpers import fake_context

class IdeInstallTests(unittest.TestCase):

    def test_ide_install_dry_run_invokes_homebrew_cask_install(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(install=True, extensions=(), settings={}),
                "cursor": IdeConfig(install=False, extensions=(), settings={}),
            },
        )

        ide.reconcile_ide_installs(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("[DRY-RUN] Would run: brew install --cask visual-studio-code", info_messages)
        self.assertEqual(len(info_messages), 1)



    def test_ide_install_skips_existing_cask_and_reports_available_cli(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.process.run_check",
            return_value=True,
        ), mock.patch("base_setup.process.run_command") as run_command:
            ide.reconcile_ide_install(ctx, definition, dry_run=False)

        run_command.assert_not_called()
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("VS Code is already installed via Homebrew cask 'visual-studio-code'.", info_messages)
        self.assertIn("VS Code CLI 'code' is available on PATH.", info_messages)



    def test_ide_install_installs_missing_cask(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["cursor"]

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.process.run_check",
            return_value=False,
        ), mock.patch("base_setup.process.run_command") as run_command:
            ide.reconcile_ide_install(ctx, definition, dry_run=False)

        run_command.assert_called_once_with(ctx, ["brew", "install", "--cask", "cursor"])



    def test_ide_install_warns_when_cli_is_missing_after_install(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["vscode"]

        def command_exists(name: str) -> bool:
            return name == "brew"

        with mock.patch("base_setup.process.command_exists", side_effect=command_exists), mock.patch(
            "base_setup.process.run_check",
            return_value=True,
        ):
            ide.reconcile_ide_install(ctx, definition, dry_run=False)

        warning_messages = [call.args[0] % call.args[1:] for call in ctx.log.warning.call_args_list]
        self.assertIn(
            "VS Code is installed, but CLI 'code' is not on PATH. Enable the IDE shell command before extension setup.",
            warning_messages,
        )



    def test_check_ide_install_reports_missing_cask(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.process.run_check",
            return_value=False,
        ):
            check = ide.check_ide_install("demo", definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.name, "VS Code app")
        self.assertIn("Homebrew cask 'visual-studio-code'", check.message)
        self.assertEqual(check.fix, "basectl setup demo")



    def test_check_ide_install_reports_missing_cli(self) -> None:
        definition = ide.IDE_DEFINITIONS["cursor"]

        def command_exists(name: str) -> bool:
            return name == "brew"

        with mock.patch("base_setup.process.command_exists", side_effect=command_exists), mock.patch(
            "base_setup.process.run_check",
            return_value=True,
        ):
            check = ide.check_ide_install("demo", definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.name, "Cursor CLI")
        self.assertIn("CLI 'cursor' is not on PATH", check.message)
        self.assertIn("Enable the 'cursor' shell command", check.fix)



    def test_manifest_checks_include_requested_ide_installs(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={"vscode": IdeConfig(install=True, extensions=(), settings={})},
        )

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.process.run_check",
            return_value=True,
        ):
            checks = engine.manifest_checks(default_manifest, manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].name, "VS Code app")
        self.assertTrue(checks[0].ok)
