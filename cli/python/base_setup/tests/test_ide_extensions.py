from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from base_setup import engine, ide
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest, IdeConfig
from base_setup.tests.helpers import fake_context

class IdeExtensionTests(unittest.TestCase):

    def test_ide_extensions_dry_run_prints_install_commands(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        ide.reconcile_ide_extensions(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertEqual(
            info_messages,
            [
                "[DRY-RUN] Would run: code --install-extension ms-python.python",
                "[DRY-RUN] Would run: code --install-extension github.copilot",
            ],
        )



    def test_ide_extensions_skip_installed_extensions(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.ide.list_ide_extensions",
            return_value={"ms-python.python", "github.copilot"},
        ), mock.patch("base_setup.process.run_command") as run_command:
            ide.reconcile_ide_extensions(ctx, manifest, dry_run=False)

        run_command.assert_not_called()



    def test_ide_extensions_install_missing_extensions(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "cursor": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.ide.list_ide_extensions",
            return_value={"ms-python.python"},
        ), mock.patch("base_setup.process.run_command") as run_command:
            ide.reconcile_ide_extensions(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["cursor", "--install-extension", "github.copilot"])



    def test_ide_extensions_warn_when_cli_is_missing(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python",),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.process.command_exists", return_value=False):
            ide.reconcile_ide_extensions(ctx, manifest, dry_run=False)

        warning_messages = [call.args[0] % call.args[1:] for call in ctx.log.warning.call_args_list]
        self.assertIn("VS Code CLI 'code' is not on PATH; skipping extension setup.", warning_messages)



    def test_list_ide_extensions_returns_installed_extension_ids(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with mock.patch(
            "base_setup.ide.process.run_capture",
            return_value=mock.Mock(returncode=0, stdout="ms-python.python\n\ngithub.copilot\n", stderr=""),
        ) as run_capture:
            extensions = ide.list_ide_extensions(definition)

        self.assertEqual(extensions, {"ms-python.python", "github.copilot"})
        run_capture.assert_called_once_with(
            ["code", "--list-extensions"],
            timeout_seconds=ide.process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )



    def test_list_ide_extensions_includes_stderr_on_failure(self) -> None:
        definition = ide.IDE_DEFINITIONS["cursor"]

        with mock.patch(
            "base_setup.ide.process.run_capture",
            return_value=mock.Mock(returncode=1, stdout="", stderr="extensions unavailable\n"),
        ):
            with self.assertRaisesRegex(ArtifactError, "extensions unavailable"):
                ide.list_ide_extensions(definition)

    def test_list_ide_extensions_reports_timeout(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with mock.patch(
            "base_setup.ide.process.run_capture",
            side_effect=subprocess.TimeoutExpired(
                ["code", "--list-extensions"],
                ide.process.DIAGNOSTIC_TIMEOUT_SECONDS,
            ),
        ):
            with self.assertRaisesRegex(ArtifactError, "timed out"):
                ide.list_ide_extensions(definition)

    def test_diagnostic_snapshot_reports_missing_extension_probe_result_explicitly(self) -> None:
        snapshot = ide.IdeDiagnosticSnapshot(ide.IDE_DEFINITIONS["vscode"])

        with mock.patch("base_setup.ide.list_ide_extensions", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "installed extensions"):
                snapshot.installed_extensions()



    def test_check_ide_extensions_reuses_probe_for_all_extensions_in_ide(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.process.command_exists", return_value=True) as command_exists, mock.patch(
            "base_setup.ide.list_ide_extensions",
            return_value={"ms-python.python"},
        ) as list_extensions:
            checks = ide.check_ide_extensions(manifest)

        command_exists.assert_called_once_with("code")
        list_extensions.assert_called_once_with(ide.IDE_DEFINITIONS["vscode"])
        self.assertEqual([check.name for check in checks], ["ms-python.python", "github.copilot"])
        self.assertEqual([check.ok for check in checks], [True, False])



    def test_check_ide_extension_reports_installed_extension(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.ide.list_ide_extensions",
            return_value={"ms-python.python"},
        ):
            check = ide.check_ide_extension("demo", definition, "ms-python.python")

        self.assertTrue(check.ok)
        self.assertEqual(check.name, "ms-python.python")
        self.assertIn("is installed", check.message)



    def test_check_ide_extension_reports_missing_extension(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.ide.list_ide_extensions",
            return_value=set(),
        ):
            check = ide.check_ide_extension("demo", definition, "ms-python.python")

        self.assertFalse(check.ok)
        self.assertEqual(check.fix, "basectl setup demo")
        self.assertIn("is not installed", check.message)



    def test_check_ide_extension_reports_missing_cli(self) -> None:
        definition = ide.IDE_DEFINITIONS["cursor"]

        with mock.patch("base_setup.process.command_exists", return_value=False):
            check = ide.check_ide_extension("demo", definition, "github.copilot")

        self.assertFalse(check.ok)
        self.assertIn("CLI 'cursor' is not on PATH", check.message)
        self.assertIn("basectl setup demo", check.fix)



    def test_manifest_checks_include_ide_extensions(self) -> None:
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
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python",),
                    settings={},
                )
            },
        )

        with mock.patch.dict("os.environ", {"BASE_SETUP_PROFILES": "dev"}), mock.patch(
            "base_setup.process.command_exists", return_value=True
        ), mock.patch(
            "base_setup.ide.list_ide_extensions",
            return_value={"ms-python.python"},
        ):
            checks = engine.manifest_checks(default_manifest, manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].name, "ms-python.python")
        self.assertTrue(checks[0].ok)


    def test_manifest_checks_skip_ide_extensions_without_dev_profile(self) -> None:
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
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python",),
                    settings={},
                )
            },
        )

        with mock.patch.dict("os.environ", {"BASE_SETUP_PROFILES": ""}), mock.patch(
            "base_setup.process.command_exists", return_value=False
        ) as command_exists, mock.patch("base_setup.ide.list_ide_extensions") as list_extensions:
            checks = engine.manifest_checks(default_manifest, manifest)

        command_exists.assert_not_called()
        list_extensions.assert_not_called()
        self.assertNotIn("ms-python.python", [check.name for check in checks])
