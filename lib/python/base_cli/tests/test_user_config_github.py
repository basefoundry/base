from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import base_cli
from base_cli.config import read_user_config, user_config_path


class GithubUserConfigTests(unittest.TestCase):
    def test_read_user_config_defaults_github_settings_to_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = read_user_config(Path(tmpdir))

        self.assertIsNone(config.github.default_owner)
        self.assertIsNone(config.github.clone_protocol)

    def test_read_user_config_parses_github_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text(
                "\n".join(
                    [
                        "github:",
                        "  default_owner: codeforester",
                        "  clone_protocol: https",
                    ]
                ),
                encoding="utf-8",
            )

            config = read_user_config(home)

        self.assertEqual(config.github.default_owner, "codeforester")
        self.assertEqual(config.github.clone_protocol, "https")

    def test_read_user_config_rejects_non_mapping_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("github: true\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "github must be a mapping"):
                read_user_config(home)

    def test_read_user_config_rejects_invalid_github_default_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("github:\n  default_owner: bad_owner!\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "github.default_owner must start with"):
                read_user_config(home)

    def test_read_user_config_rejects_invalid_github_clone_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("github:\n  clone_protocol: ftp\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "github.clone_protocol must be 'ssh' or 'https'"):
                read_user_config(home)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_context_exposes_github_typed_user_config(self) -> None:
        app = base_cli.App(name="typed-config-github", log_to_file=False)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["github"] = ctx.user_config.github

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("github:\n  default_owner: codeforester\n  clone_protocol: ssh\n", encoding="utf-8")
            from base_cli.testing import invoke

            result = invoke(app, [], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(seen["github"].default_owner, "codeforester")
        self.assertEqual(seen["github"].clone_protocol, "ssh")


if __name__ == "__main__":
    unittest.main()
