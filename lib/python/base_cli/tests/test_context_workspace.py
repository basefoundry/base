from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import base_cli
from base_cli.config import user_config_path


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class ContextWorkspaceRootTests(unittest.TestCase):
    def test_context_exposes_workspace_root_when_configured(self) -> None:
        app = base_cli.App(name="workspace-root-configured", log_to_file=False)
        seen: dict[str, Path | None] = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["workspace_root"] = ctx.workspace_root
            seen["user_config_workspace_root"] = ctx.user_config.workspace.root

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            workspace.mkdir()
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text(f"workspace:\n  root: {workspace}\n", encoding="utf-8")

            from base_cli.testing import invoke

            result = invoke(app, [], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(seen["workspace_root"], workspace.resolve())
        self.assertEqual(seen["user_config_workspace_root"], workspace.resolve())

    def test_context_workspace_root_is_none_without_configured_root(self) -> None:
        app = base_cli.App(name="workspace-root-default", log_to_file=False)
        seen: dict[str, Path | None] = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["workspace_root"] = ctx.workspace_root
            seen["user_config_workspace_root"] = ctx.user_config.workspace.root

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)

            from base_cli.testing import invoke

            result = invoke(app, [], home=home)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIsNone(seen["workspace_root"])
        self.assertIsNone(seen["user_config_workspace_root"])
