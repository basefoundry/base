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


def write_build_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "services" / "api").mkdir(parents=True)
    (project_root / "services" / "worker").mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "build:",
                "  default:",
                "    - api",
                "    - worker",
                "  targets:",
                "    api:",
                "      description: Build the API service.",
                "      working_dir: services/api",
                "      command: go build ./cmd/api",
                "    worker:",
                "      description: Build the worker service.",
                "      working_dir: services/worker",
                "      command: go build ./cmd/worker",
                "artifacts: []",
            ]
        ),
        encoding="utf-8",
    )


def write_build_manifest_without_default(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "services" / "api").mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "build:",
                "  targets:",
                "    api:",
                "      working_dir: services/api",
                "      command: go build ./cmd/api",
                "artifacts: []",
            ]
        ),
        encoding="utf-8",
    )


def run_engine(args: list[str], base_home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    env = {
        "HOME": str(base_home.parent / "home"),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_MANIFEST": "",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class BuildTargetTests(unittest.TestCase):
    def test_projects_build_targets_prints_default_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_build_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["build-targets", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tapi\t{(project_root / 'services' / 'api').resolve()}\tgo build ./cmd/api\tBuild the API service.\n"
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tworker\t{(project_root / 'services' / 'worker').resolve()}\tgo build ./cmd/worker"
            "\tBuild the worker service.\n",
        )

    def test_projects_build_targets_prints_explicit_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_build_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["build-targets", "demo", "worker"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tworker\t{(project_root / 'services' / 'worker').resolve()}\tgo build ./cmd/worker"
            "\tBuild the worker service.\n",
        )

    def test_projects_build_target_list_prints_all_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_build_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["build-target-list", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("\tapi\t", stdout)
        self.assertIn("\tworker\t", stdout)

    def test_projects_build_targets_requires_build_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["build-targets", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare build targets", stderr)

    def test_projects_build_targets_requires_default_when_no_targets_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_build_manifest_without_default(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["build-targets", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare build.default", stderr)

    def test_projects_build_targets_reports_unknown_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_build_manifest(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["build-targets", "demo", "web"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare build target 'web'", stderr)
