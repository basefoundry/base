from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_cli.config import UserConfig, UserIdeConfig, UserIdePreference
from base_setup import engine, ide
from base_setup.manifest import BaseManifest, IdeConfig
from base_setup.tests.helpers import fake_context

class UserIdePreferenceMergeTests(unittest.TestCase):

    def test_effective_ide_config_adds_user_extensions_and_settings(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=True,
                    extensions=("ms-python.python",),
                    settings={"python.defaultInterpreterPath": "auto"},
                )
            },
        )
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=True,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=True,
                        install=None,
                        extra_extensions=("eamodio.gitlens", "ms-python.python"),
                        settings={"editor.fontSize": 14},
                    )
                },
            ),
        )

        effective = engine.effective_manifest_with_user_config(manifest, user_config)

        vscode = effective.ide["vscode"]
        self.assertTrue(vscode.install)
        self.assertEqual(vscode.extensions, ("ms-python.python", "eamodio.gitlens"))
        self.assertEqual(
            vscode.settings,
            {
                "editor.fontSize": 14,
                "python.defaultInterpreterPath": "auto",
            },
        )



    def test_effective_ide_config_project_setting_wins_over_user_setting(self) -> None:
        project_ide = {
            "vscode": IdeConfig(
                install=False,
                extensions=(),
                settings={"editor.formatOnSave": True},
            )
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=None,
                        install=None,
                        extra_extensions=(),
                        settings={"editor.formatOnSave": False, "editor.fontSize": 14},
                    )
                },
            ),
        )

        effective = ide.effective_ide_config(project_ide, user_config)

        self.assertEqual(
            effective["vscode"].settings,
            {"editor.formatOnSave": True, "editor.fontSize": 14},
        )



    def test_effective_ide_config_user_install_preference_overrides_project_install(self) -> None:
        project_ide = {
            "cursor": IdeConfig(
                install=True,
                extensions=("github.copilot",),
                settings={},
            )
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "cursor": UserIdePreference(
                        enabled=None,
                        install=False,
                        extra_extensions=(),
                        settings={},
                    )
                },
            ),
        )

        effective = ide.effective_ide_config(project_ide, user_config)

        self.assertFalse(effective["cursor"].install)
        self.assertEqual(effective["cursor"].extensions, ("github.copilot",))



    def test_effective_ide_config_can_disable_all_ide_work(self) -> None:
        project_ide = {
            "vscode": IdeConfig(
                install=True,
                extensions=("ms-python.python",),
                settings={"editor.formatOnSave": True},
            )
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(enabled=False, preferences={}),
        )

        self.assertEqual(ide.effective_ide_config(project_ide, user_config), {})

    def test_reconcile_manifest_uses_context_user_config(self) -> None:
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
            ide={"vscode": IdeConfig(install=True, extensions=("ms-python.python",), settings={})},
        )
        ctx = fake_context()
        ctx.user_config = UserConfig(raw={}, ide=UserIdeConfig(enabled=False, preferences={}))

        with (
            mock.patch("base_setup.engine.reconcile_brewfile"),
            mock.patch("base_setup.engine.reconcile_mise"),
            mock.patch("base_setup.engine.reconcile_ide_installs") as reconcile_ide_installs,
            mock.patch("base_setup.engine.reconcile_ide_extensions"),
            mock.patch("base_setup.engine.reconcile_ide_settings"),
            mock.patch("base_setup.engine.reconcile_uv_project"),
        ):
            engine.reconcile_manifest(ctx, default_manifest, manifest, dry_run=True)

        effective_manifest = reconcile_ide_installs.call_args.args[1]
        self.assertEqual(effective_manifest.ide, {})

    def test_manifest_checks_accepts_injected_user_config(self) -> None:
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
            ide={"vscode": IdeConfig(install=True, extensions=("ms-python.python",), settings={})},
        )
        user_config = UserConfig(raw={}, ide=UserIdeConfig(enabled=False, preferences={}))

        checks = engine.manifest_checks(default_manifest, manifest, user_config=user_config)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].name, "user IDE config")
        self.assertIn("disables", checks[0].message)



    def test_effective_ide_config_can_disable_one_ide(self) -> None:
        project_ide = {
            "vscode": IdeConfig(install=True, extensions=(), settings={}),
            "cursor": IdeConfig(install=True, extensions=(), settings={}),
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "cursor": UserIdePreference(
                        enabled=False,
                        install=None,
                        extra_extensions=(),
                        settings={},
                    )
                },
            ),
        )

        effective = ide.effective_ide_config(project_ide, user_config)

        self.assertEqual(set(effective), {"vscode"})



    def test_effective_ide_config_includes_user_only_ide_preferences(self) -> None:
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=None,
                        install=False,
                        extra_extensions=("eamodio.gitlens",),
                        settings={"editor.fontSize": 14},
                    )
                },
            ),
        )

        effective = ide.effective_ide_config({}, user_config)

        self.assertEqual(set(effective), {"vscode"})
        self.assertFalse(effective["vscode"].install)
        self.assertEqual(effective["vscode"].extensions, ("eamodio.gitlens",))



    def test_ide_preference_warning_checks_report_setting_conflicts(self) -> None:
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
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=None,
                        install=None,
                        extra_extensions=(),
                        settings={"editor.formatOnSave": False},
                    )
                },
            ),
        )

        checks = ide.ide_preference_warning_checks(manifest, user_config)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].status, "warn")
        self.assertIn("is ignored", checks[0].message)



    def test_check_manifest_warns_but_succeeds_for_setting_conflict_only(self) -> None:
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
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir:
            config_path = Path(home_dir) / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "ide:\n  vscode:\n    settings:\n      editor.formatOnSave: false\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(ide.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="text")

        self.assertEqual(status, 0)
