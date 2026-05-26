from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\nartifacts: []\n",
        encoding="utf-8",
    )


def run_engine(args: list[str], base_home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(os.environ, {"HOME": home_dir, "BASE_HOME": str(base_home)}):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class ProjectDiscoveryTests(unittest.TestCase):
    def test_discovers_projects_under_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            write_manifest(workspace / "zeta", "zeta")
            write_manifest(workspace / "alpha", "alpha")
            (workspace / "notes").mkdir()

            projects = engine.discover_projects(workspace)

        self.assertEqual([project.name for project in projects], ["alpha", "zeta"])

    def test_projects_list_defaults_to_base_home_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            write_manifest(base_home, "base")
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(["list"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"base\t{base_home.resolve()}", stdout)
        self.assertIn(f"demo\t{(workspace / 'demo').resolve()}", stdout)

    def test_projects_list_supports_workspace_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "custom"
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(["list", "--workspace", str(workspace)], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{(workspace / 'demo').resolve()}\n")

    def test_projects_list_reports_invalid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            bad = workspace / "bad"
            bad.mkdir()
            (bad / "base_manifest.yaml").write_text("project: []\n", encoding="utf-8")

            status, _stdout, stderr = run_engine(["list"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("project must be a mapping", stderr)

    def test_projects_list_rejects_duplicate_project_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            write_manifest(workspace / "one", "demo")
            write_manifest(workspace / "two", "demo")

            with self.assertRaisesRegex(engine.ProjectDiscoveryError, "Duplicate project names"):
                engine.discover_projects(workspace)


if __name__ == "__main__":
    unittest.main()
