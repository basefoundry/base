from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import ide
from base_setup import ide_settings
from base_setup.manifest import BaseManifest, IdeConfig
from base_setup.tests.helpers import fake_context

# The regression tests intentionally exercise the JSONC rewriter's private helpers.
# pylint: disable=protected-access

class IdeSettingsTests(unittest.TestCase):  # pylint: disable=too-many-public-methods

    def test_project_ide_mutation_plan_lists_apps_extensions_and_settings(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=True,
                    extensions=("ms-python.python",),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir, mock.patch.dict(os.environ, {"HOME": home_dir}):
            plans = ide.log_project_ide_mutation_plan(ctx, manifest, manifest)
            expected_settings_file = ide.ide_settings_file(ide.IDE_DEFINITIONS["vscode"])

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].definition, ide.IDE_DEFINITIONS["vscode"])
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("Project 'demo' requests project-originated IDE mutations:", info_messages)
        self.assertIn("  VS Code app: brew install --cask visual-studio-code", info_messages)
        self.assertIn("  VS Code extension: ms-python.python", info_messages)
        self.assertIn(
            f"  VS Code user settings file: {expected_settings_file}",
            info_messages,
        )
        self.assertIn("    editor.formatOnSave = true", info_messages)

    def test_resolve_ide_settings_auto_interpreter_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "demo-venv"
            with mock.patch.dict(os.environ, {"BASE_PROJECT_VENV_DIR": str(venv_dir)}):
                settings = ide.resolve_ide_settings(
                    "demo",
                    {
                        "python.defaultInterpreterPath": "auto",
                        "editor.formatOnSave": True,
                    },
                )

        self.assertEqual(settings["python.defaultInterpreterPath"], str(venv_dir / "bin" / "python"))
        self.assertTrue(settings["editor.formatOnSave"])

    def test_resolve_ide_settings_auto_interpreter_uses_manifest_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
            )
            settings = ide.resolve_ide_settings(
                manifest,
                {
                    "python.defaultInterpreterPath": "auto",
                },
            )

        self.assertEqual(
            settings["python.defaultInterpreterPath"],
            str((project_root / ".venv" / "bin" / "python").resolve()),
        )



    def test_check_ide_settings_auto_interpreter_uses_manifest_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                ide={
                    "vscode": IdeConfig(
                        install=False,
                        extensions=(),
                        settings={"python.defaultInterpreterPath": "auto"},
                    )
                },
            )

            with mock.patch("base_setup.ide_settings.check_ide_setting") as check_setting:
                check_setting.return_value = ide.ArtifactCheck(
                    name="vscode setting python.defaultInterpreterPath",
                    ok=True,
                    message="ok",
                    fix="",
                    finding_id="BASE-P060",
                )
                ide.check_ide_settings(manifest)

        check_setting.assert_called_once_with(
            "demo",
            ide.IDE_DEFINITIONS["vscode"],
            "python.defaultInterpreterPath",
            str((project_root / ".venv" / "bin" / "python").resolve()),
            snapshot=mock.ANY,
        )

    def test_ide_settings_file_uses_macos_application_support(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir}, clear=False), mock.patch(
                "base_setup.ide_settings.sys.platform", "darwin"
            ):
                settings_file = ide.ide_settings_file(definition)

        self.assertEqual(
            settings_file,
            Path(home_dir) / "Library" / "Application Support" / "Code" / "User" / "settings.json",
        )



    def test_ide_settings_file_uses_xdg_config_home_off_macos(self) -> None:
        definition = ide.IDE_DEFINITIONS["cursor"]

        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            config_home = Path(tmpdir) / "xdg-config"
            home_dir.mkdir()
            with mock.patch.dict(
                os.environ,
                {"HOME": str(home_dir), "XDG_CONFIG_HOME": str(config_home)},
                clear=False,
            ), mock.patch("base_setup.ide_settings.sys.platform", "linux"):
                settings_file = ide.ide_settings_file(definition)

        self.assertEqual(settings_file, config_home / "Cursor" / "User" / "settings.json")



    def test_ide_settings_file_defaults_to_home_config_off_macos(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}, clear=False), mock.patch(
                "base_setup.ide_settings.sys.platform", "linux"
            ):
                settings_file = ide.ide_settings_file(definition)

        self.assertEqual(settings_file, Path(home_dir) / ".config" / "Code" / "User" / "settings.json")



    def test_merge_ide_settings_writes_missing_keys(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                ide.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.formatOnSave": True},
                    dry_run=False,
                )
                settings_file = ide.ide_settings_file(definition)
                settings = json.loads(settings_file.read_text(encoding="utf-8"))

        self.assertEqual(settings, {"editor.formatOnSave": True})

    def test_write_json_atomic_removes_temp_file_when_dump_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_dir = Path(tmpdir)
            settings_file = settings_dir / "settings.json"

            with mock.patch("base_setup.ide_settings.json.dump", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    ide.write_json_atomic(settings_file, {"editor.formatOnSave": True})

            self.assertEqual(list(settings_dir.iterdir()), [])

    def test_write_json_atomic_removes_temp_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_dir = Path(tmpdir)
            settings_file = settings_dir / "settings.json"

            with mock.patch.object(Path, "replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    ide.write_json_atomic(settings_file, {"editor.formatOnSave": True})

            self.assertEqual(list(settings_dir.iterdir()), [])



    def test_merge_ide_settings_preserves_existing_user_value(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["cursor"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(
                    json.dumps({"editor.formatOnSave": False}),
                    encoding="utf-8",
                )

                ide.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.formatOnSave": True, "editor.rulers": [100]},
                    dry_run=False,
                )
                settings = json.loads(settings_file.read_text(encoding="utf-8"))

        self.assertEqual(settings["editor.formatOnSave"], False)
        self.assertEqual(settings["editor.rulers"], [100])
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("Cursor setting 'editor.formatOnSave' already set by user; leaving intact.", info_messages)

    def test_merge_ide_settings_preserves_jsonc_comments_and_nested_values(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["vscode"]
        source = """{
  // Keep this user comment.
  "editor.formatOnSave": false,
  "nested": {
    "url": "https://example.test/a//b",
  }, /* Keep this trailing comment. */
}
"""

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(source, encoding="utf-8")

                ide.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.rulers": [100]},
                    dry_run=False,
                )
                updated = settings_file.read_text(encoding="utf-8")
                settings = ide.read_ide_settings(definition)

        self.assertIn("// Keep this user comment.", updated)
        self.assertIn("/* Keep this trailing comment. */", updated)
        self.assertIn('"https://example.test/a//b"', updated)
        self.assertEqual(settings["nested"], {"url": "https://example.test/a//b"})
        self.assertEqual(settings["editor.rulers"], [100])
        self.assertFalse(settings["editor.formatOnSave"])

    def test_jsonc_rewriter_appends_after_a_trailing_string_value(self) -> None:
        source = '{\n  "editor.fontFamily": "Menlo"\n}\n'

        updated = ide_settings._jsonc_object_with_added_properties(source, {"editor.rulers": [100]})

        self.assertEqual(
            ide_settings._parse_jsonc(updated),
            {"editor.fontFamily": "Menlo", "editor.rulers": [100]},
        )

    def test_jsonc_rewriter_separates_multiple_single_line_properties(self) -> None:
        source = '{"editor.fontFamily": "Menlo"}'

        updated = ide_settings._jsonc_object_with_added_properties(
            source,
            {"editor.rulers": [100], "editor.tabSize": 4},
        )

        self.assertEqual(
            ide_settings._parse_jsonc(updated),
            {"editor.fontFamily": "Menlo", "editor.rulers": [100], "editor.tabSize": 4},
        )



    def test_merge_ide_settings_dry_run_does_not_write(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                ide.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.formatOnSave": True},
                    dry_run=True,
                )
                settings_file = ide.ide_settings_file(definition)

        self.assertFalse(settings_file.exists())
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            "[DRY-RUN] Would set VS Code user setting 'editor.formatOnSave' to true.",
            info_messages,
        )

    def test_merge_ide_settings_dry_run_preserves_jsonc_bytes(self) -> None:
        ctx = fake_context()
        definition = ide.IDE_DEFINITIONS["cursor"]
        source = '{\n  // User-owned setting.\n  "editor.minimap.enabled": true,\n}\n'

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(source, encoding="utf-8")
                before = settings_file.read_bytes()

                ide.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.rulers": [100]},
                    dry_run=True,
                )

                self.assertEqual(settings_file.read_bytes(), before)



    def test_reconcile_ide_settings_uses_manifest_settings(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with mock.patch("base_setup.ide_settings.merge_ide_settings") as merge_settings:
            ide.reconcile_ide_settings(ctx, manifest, dry_run=True)

        merge_settings.assert_called_once_with(
            ctx,
            ide.IDE_DEFINITIONS["vscode"],
            {"editor.formatOnSave": True},
            dry_run=True,
        )



    def test_check_ide_setting_reports_absent_key(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                check = ide.check_ide_setting("demo", definition, "editor.formatOnSave", True)

        self.assertFalse(check.ok)
        self.assertIn("is absent", check.message)
        self.assertEqual(check.fix, "basectl setup demo")



    def test_check_ide_setting_reports_matching_key(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                check = ide.check_ide_setting("demo", definition, "editor.formatOnSave", True)

        self.assertTrue(check.ok)
        self.assertIn("matches", check.message)



    def test_check_ide_setting_reports_divergent_key(self) -> None:
        definition = ide.IDE_DEFINITIONS["cursor"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": False}), encoding="utf-8")
                check = ide.check_ide_setting("demo", definition, "editor.formatOnSave", True)

        self.assertFalse(check.ok)
        self.assertIn("Base will not overwrite user settings", check.message)
        self.assertIn("remove the key", check.fix)



    def test_check_ide_settings_includes_manifest_settings(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(ide.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                checks = ide.check_ide_settings(manifest)

        self.assertEqual(len(checks), 1)
        self.assertTrue(checks[0].ok)



    def test_check_ide_settings_reuses_probe_for_all_settings_in_ide(self) -> None:
        definition = ide.IDE_DEFINITIONS["vscode"]
        settings_file = Path("/tmp/vscode-settings.json")
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={
                        "editor.formatOnSave": True,
                        "editor.rulers": [100],
                    },
                )
            },
        )

        with mock.patch(
            "base_setup.ide_settings.ide_settings_file",
            return_value=settings_file,
        ) as settings_path, mock.patch(
            "base_setup.ide_settings.read_ide_settings",
            return_value={
                "editor.formatOnSave": True,
                "editor.rulers": [100],
            },
        ) as read_settings:
            checks = ide.check_ide_settings(manifest)

        settings_path.assert_called_once_with(definition)
        read_settings.assert_called_once_with(definition)
        self.assertEqual(
            [check.name for check in checks],
            ["VS Code setting: editor.formatOnSave", "VS Code setting: editor.rulers"],
        )
        self.assertTrue(all(check.ok for check in checks))

    def test_diagnostic_snapshot_reports_missing_settings_probe_result_explicitly(self) -> None:
        snapshot = ide.IdeDiagnosticSnapshot(ide.IDE_DEFINITIONS["vscode"])

        with mock.patch("base_setup.ide_settings.read_ide_settings", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "settings"):
                snapshot.current_settings()
