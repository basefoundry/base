from __future__ import annotations

import unittest

from base_cli.ide_schema import IDE_DEFINITIONS
from base_cli.ide_schema import PROJECT_AUTO_SETTING_KEYS
from base_cli.ide_schema import SUPPORTED_IDES
from base_cli.ide_schema import parse_ide_extensions
from base_cli.ide_schema import parse_ide_settings


class IdeSchemaTests(unittest.TestCase):
    def test_supported_ide_names_are_derived_from_definitions(self) -> None:
        self.assertEqual(SUPPORTED_IDES, frozenset(IDE_DEFINITIONS))
        self.assertEqual(IDE_DEFINITIONS["vscode"].cli, "code")
        self.assertEqual(IDE_DEFINITIONS["cursor"].settings_app_dir, "Cursor")

    def test_parse_ide_extensions_trims_and_rejects_empty_values(self) -> None:
        self.assertEqual(
            parse_ide_extensions("ide.vscode.extensions", [" ms-python.python "]),
            ("ms-python.python",),
        )

        with self.assertRaisesRegex(ValueError, r"ide.vscode.extensions\[1\]"):
            parse_ide_extensions("ide.vscode.extensions", [""])

    def test_parse_ide_settings_allows_auto_as_literal_by_default(self) -> None:
        self.assertEqual(
            parse_ide_settings("ide.vscode.settings", {"editor.defaultFormatter": "auto"}),
            {"editor.defaultFormatter": "auto"},
        )

    def test_parse_ide_settings_can_restrict_project_auto_values(self) -> None:
        self.assertEqual(
            parse_ide_settings(
                "ide.vscode.settings",
                {"python.defaultInterpreterPath": "auto"},
                auto_setting_keys=PROJECT_AUTO_SETTING_KEYS,
            ),
            {"python.defaultInterpreterPath": "auto"},
        )

        with self.assertRaisesRegex(ValueError, "does not support the special value 'auto'"):
            parse_ide_settings(
                "ide.vscode.settings",
                {"editor.defaultFormatter": "auto"},
                auto_setting_keys=PROJECT_AUTO_SETTING_KEYS,
            )
