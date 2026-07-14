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


def write_build_manifest_with_runner(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "services" / "api").mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "build:",
                "  default:",
                "    - package",
                "  targets:",
                "    package:",
                "      working_dir: services/api",
                "      command: python -m build",
                "      runner: uv",
                "      description: Build the Python package.",
                "artifacts: []",
            ]
        ),
        encoding="utf-8",
    )


def write_inline_uv_build_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "services" / "api").mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "python: {manager: uv}",
                "build:",
                "  default:",
                "    - api",
                "  targets:",
                "    api:",
                "      description: Build the API service.",
                "      working_dir: services/api",
                "      command: python -m build",
                "artifacts: []",
            ]
        ),
        encoding="utf-8",
    )


_engine_homes: list[Path] = []


def run_engine(args: list[str], base_home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        _engine_homes.append(Path(home_dir))
        env = {
            "HOME": str(_engine_homes[-1]),
            "BASE_HOME": str(base_home),
            "BASE_PROJECT": "",
            "BASE_PROJECT_MANIFEST": "",
        }
        with mock.patch.dict(os.environ, env):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def base_route_fields(base_home: Path, project: str, *, trust_required: bool = True) -> str:
    if not _engine_homes:
        raise AssertionError("run_engine must be called before base_route_fields")
    if project == "base":
        venv_dir = _engine_homes[-1] / ".base.d" / project / ".venv"
    else:
        venv_dir = (base_home.parent / project / ".venv").resolve()
    trust_value = "true" if trust_required else "false"
    return (
        f"\t__base_project_venv_dir={venv_dir}"
        "\t__base_uses_uv_manager=false"
        f"\t__base_manifest_command_trust_required={trust_value}"
    )


def uv_route_fields(project_root: Path, *, trust_required: bool = True) -> str:
    trust_value = "true" if trust_required else "false"
    return (
        f"\t__base_project_venv_dir={(project_root / '.venv').resolve()}"
        "\t__base_uses_uv_manager=true"
        f"\t__base_manifest_command_trust_required={trust_value}"
    )


class BuildTargetTests(unittest.TestCase):
    def test_projects_build_targets_requires_project_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, stdout, stderr = run_engine(["build-targets"], base_home)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("requires at least 1 argument (project name); got 0", stderr)

    def test_projects_build_targets_does_not_cap_target_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_build_manifest(workspace / "demo", "demo")
            targets = [f"target-{index}" for index in range(1001)]

            status, stdout, stderr = run_engine(["build-targets", "demo", *targets], base_home)

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("does not declare build target 'target-0'", stderr)
        self.assertNotIn("expects between 1 and 1000 arguments", stderr)

    def test_projects_build_target_list_requires_exactly_one_project_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, stdout, stderr = run_engine(["build-target-list"], base_home)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("requires exactly 1 argument (project name); got 0", stderr)

    def test_projects_build_target_list_rejects_extra_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, stdout, stderr = run_engine(["build-target-list", "demo", "api"], base_home)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("requires exactly 1 argument (project name); got 2", stderr)

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
            f"\tapi\t{(project_root / 'services' / 'api').resolve()}\tgo build ./cmd/api\tBuild the API service."
            f"{base_route_fields(base_home, 'demo')}\n"
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tworker\t{(project_root / 'services' / 'worker').resolve()}\tgo build ./cmd/worker"
            f"\tBuild the worker service.{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_build_targets_mark_manifest_command_trust_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_build_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["build-targets", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("__base_manifest_command_trust_required=true", stdout)

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
            f"\tBuild the worker service.{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_build_targets_prints_runner_when_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_build_manifest_with_runner(project_root, "demo")

            status, stdout, stderr = run_engine(["build-targets", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tpackage\t{(project_root / 'services' / 'api').resolve()}\tpython -m build"
            f"\tBuild the Python package.\tuv{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_build_targets_prints_python_route_metadata_for_inline_uv_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_inline_uv_build_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["build-targets", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tapi\t{(project_root / 'services' / 'api').resolve()}\tpython -m build"
            f"\tBuild the API service.{uv_route_fields(project_root)}\n",
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
