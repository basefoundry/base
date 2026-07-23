from __future__ import annotations

import unittest

import base_cli
from base_cli import command_filters, command_protocol, history
from base_cli.config import UserConfig, UserGithubConfig, UserIdeConfig, UserIdePreference, UserWorkspaceConfig


class PublicApiTests(unittest.TestCase):
    def test_facade_exports_supported_modules_functions_and_types(self) -> None:
        expected = {
            "CommandProtocolError",
            "UserConfig",
            "UserGithubConfig",
            "UserIdeConfig",
            "UserIdePreference",
            "UserWorkspaceConfig",
            "command_filters",
            "command_matches",
            "command_protocol",
            "dumps_record",
            "dumps_records",
            "history",
            "loads_records",
            "normalize_command_filter",
            "normalize_command_filters",
        }

        self.assertTrue(expected.issubset(base_cli.__all__))
        self.assertIs(base_cli.UserConfig, UserConfig)
        self.assertIs(base_cli.UserGithubConfig, UserGithubConfig)
        self.assertIs(base_cli.UserIdeConfig, UserIdeConfig)
        self.assertIs(base_cli.UserIdePreference, UserIdePreference)
        self.assertIs(base_cli.UserWorkspaceConfig, UserWorkspaceConfig)
        self.assertIs(base_cli.command_filters, command_filters)
        self.assertIs(base_cli.command_protocol, command_protocol)

    def test_module_all_surfaces_are_explicit(self) -> None:
        self.assertEqual(
            set(command_filters.__all__),
            {"command_matches", "normalize_command_filter", "normalize_command_filters"},
        )
        self.assertEqual(
            set(command_protocol.__all__),
            {"CommandProtocolError", "dumps_record", "dumps_records", "loads_records"},
        )
        self.assertIn("write_primary_record", history.__all__)
        self.assertNotIn("lock_history_file", history.__all__)
        self.assertNotIn("write_all", history.__all__)

    def test_entry_points_have_docstrings(self) -> None:
        self.assertTrue(base_cli.App.__doc__)
        self.assertTrue(base_cli.Context.__doc__)
        self.assertTrue(base_cli.run_app.__doc__)


if __name__ == "__main__":
    unittest.main()
