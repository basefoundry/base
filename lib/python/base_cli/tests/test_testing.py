from __future__ import annotations

import importlib.util
import inspect
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import base_cli
from base_cli.testing import invoke


class PackageExportTests(unittest.TestCase):
    def test_package_exports_testing_module_for_documented_access(self) -> None:
        env = os.environ.copy()
        pythonpath = str(Path(__file__).resolve().parents[2])
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            pythonpath
            if not existing_pythonpath
            else f"{pythonpath}{os.pathsep}{existing_pythonpath}"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import base_cli; assert base_cli.testing.invoke",
            ],
            check=False,
            capture_output=True,
            env=env,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class InvokeTests(unittest.TestCase):
    def test_invoke_declares_click_result_return_type(self) -> None:
        return_annotation = inspect.signature(invoke).return_annotation

        self.assertNotEqual(return_annotation, inspect.Signature.empty)
        self.assertIn("Result", str(return_annotation))

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

    def test_invoke_with_cwd_does_not_mutate_process_cwd(self) -> None:
        app = base_cli.App(name="testing-cwd-isolation", log_to_file=False)
        seen: dict[str, Path | None] = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["project_root"] = ctx.project_root
            seen["manifest_path"] = ctx.manifest_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            manifest_path = project / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\n", encoding="utf-8")
            original_cwd = Path.cwd()

            with mock.patch("os.chdir", side_effect=AssertionError("process-global cwd mutation")):
                result = invoke(app, [], home=home, cwd=project)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(seen["project_root"], project.resolve())
        self.assertEqual(seen["manifest_path"], manifest_path.resolve())
        self.assertEqual(Path.cwd(), original_cwd)

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
