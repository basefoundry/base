from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import base_cli
from base_cli.testing import invoke


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class InvokeTests(unittest.TestCase):
    def test_invoke_writes_manifest_fixture_into_cwd(self) -> None:
        app = base_cli.App(name="testing-manifest", log_to_file=False)
        seen: dict[str, Path | None] = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["project_root"] = ctx.project_root
            seen["manifest_path"] = ctx.manifest_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            result = invoke(
                app,
                [],
                home=home,
                cwd=project,
                manifest={"project": {"name": "demo"}, "artifacts": []},
            )

            manifest_path = project / "base_manifest.yaml"

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(seen["project_root"], project.resolve())
        self.assertEqual(seen["manifest_path"], manifest_path.resolve())

    def test_invoke_rejects_manifest_without_cwd(self) -> None:
        app = base_cli.App(name="testing-manifest-without-cwd", log_to_file=False)

        with self.assertRaisesRegex(ValueError, "manifest requires cwd"):
            invoke(app, [], manifest={"project": {"name": "demo"}})

    def test_invoke_with_cwd_without_manifest_preserves_no_manifest_behavior(self) -> None:
        app = base_cli.App(name="testing-no-manifest", log_to_file=False)
        seen: dict[str, Path | None] = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["project_root"] = ctx.project_root
            seen["manifest_path"] = ctx.manifest_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            isolated = root / "isolated"
            isolated.mkdir()

            result = invoke(app, [], home=home, cwd=isolated)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIsNone(seen["project_root"])
        self.assertIsNone(seen["manifest_path"])
