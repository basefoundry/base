from __future__ import annotations

import io
import importlib.util
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_test import engine


def write_manifest(project_root: Path, name: str, test_section: str | None) -> None:
    project_root.mkdir(parents=True)
    manifest = [f"project:\n  name: {name}"]
    if test_section is not None:
        manifest.append(test_section)
    manifest.append("artifacts: []")
    (project_root / "base_manifest.yaml").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def run_engine(args: list[str], base_home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(os.environ, {"HOME": home_dir, "BASE_HOME": str(base_home)}):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class BaseTestRunnerTests(unittest.TestCase):
    def test_dry_run_prints_project_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo", "test:\n  command: python -m unittest")

            status, stdout, stderr = run_engine(["demo", "--dry-run"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"[DRY-RUN] Would run in {project_root.resolve()}: python -m unittest", stdout)

    def test_runs_project_test_command_from_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            marker = project_root / "marker"
            write_manifest(project_root, "demo", "test:\n  command: pwd > marker")

            status, _stdout, _stderr = run_engine(["demo"], base_home)

            self.assertEqual(status, 0)
            self.assertEqual(marker.read_text(encoding="utf-8").strip(), str(project_root.resolve()))

    def test_preserves_project_test_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo", "test:\n  command: exit 7")

            status, _stdout, _stderr = run_engine(["demo"], base_home)

        self.assertEqual(status, 7)

    def test_mise_test_config_delegates_to_mise_run_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo", "test:\n  mise: unit")

            status, stdout, stderr = run_engine(["demo", "--dry-run"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("mise run unit", stdout)

    def test_reports_missing_test_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo", None)

            status, _stdout, stderr = run_engine(["demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("test is not configured", stderr)


if __name__ == "__main__":
    unittest.main()
