from __future__ import annotations

import io
import json
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


def write_test_manifest(project_root: Path, name: str, command: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ntest:\n  command: {command}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_mise_test_manifest(project_root: Path, name: str, task: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ntest:\n  mise: {task}\nartifacts: []\n",
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

    def test_projects_list_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "custom"
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(
                ["list", "--workspace", str(workspace), "--format", "json"],
                base_home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), [{"name": "demo", "path": str((workspace / "demo").resolve())}])

    def test_projects_list_rejects_unknown_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, _stdout, stderr = run_engine(["list", "--format", "xml"], base_home)

        self.assertEqual(status, 2)
        self.assertIn("Unsupported output format 'xml'", stderr)

    def test_projects_resolve_prints_project_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["resolve", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\n")

    def test_projects_test_command_prints_project_details_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_test_manifest(project_root, "demo", "pytest tests/")

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/\n",
        )

    def test_projects_test_command_prints_mise_task_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_mise_test_manifest(project_root, "demo", "unit")

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tmise run unit\n",
        )

    def test_test_command_rejects_invalid_config_without_assert(self) -> None:
        with self.assertRaisesRegex(ValueError, "TestConfig must have command or mise set"):
            engine.test_command(engine.TestConfig())

    def test_projects_test_command_defaults_to_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs"
            write_test_manifest(project_root, "demo", "pytest tests/")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["test-command"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/\n",
        )

    def test_projects_test_command_requires_manifest_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare test.command or test.mise", stderr)

    def test_projects_manifest_prints_project_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            manifest_path = project_root / "base_manifest.yaml"
            write_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["manifest", str(manifest_path)], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{manifest_path.resolve()}\n")

    def test_projects_manifest_requires_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()

            status, _stdout, stderr = run_engine(["manifest"], base_home)

        self.assertEqual(status, 2)
        self.assertIn("Manifest path is required", stderr)

    def test_projects_current_prints_nearest_project_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs" / "notes"
            write_manifest(project_root, "demo")
            nested.mkdir(parents=True)

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["current"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\n")

    def test_projects_current_reports_missing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            outside = workspace / "outside"
            outside.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(outside)
                status, _stdout, stderr = run_engine(["current"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 1)
        self.assertIn("No base_manifest.yaml found", stderr)

    def test_projects_resolve_reports_missing_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, _stdout, stderr = run_engine(["resolve", "missing"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("Project 'missing' was not found", stderr)

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
