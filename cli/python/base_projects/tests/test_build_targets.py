from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from base_cli_adapters.protocol import loads_records
from base_projects.build_targets import BuildTargetError
from base_projects.build_targets import resolve_build_target_working_dir
from base_projects import engine
from base_setup.manifest_model import BuildTargetConfig


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


def write_single_target_manifest(project_root: Path, name: str, working_dir: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "build:",
                "  default:",
                "    - target",
                "  targets:",
                "    target:",
                f"      working_dir: {working_dir}",
                "      command: echo test",
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


class BuildTargetWorkingDirectoryTests(unittest.TestCase):
    def test_resolve_build_target_working_dir_accepts_safe_nested_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            nested = project_root / "services" / "api"
            nested.mkdir(parents=True)
            project = SimpleNamespace(
                root=project_root,
                manifest_path=project_root / "base_manifest.yaml",
            )

            resolved = resolve_build_target_working_dir(
                project,
                "api",
                BuildTargetConfig(command="echo test", working_dir="services/api"),
            )

        self.assertEqual(resolved, nested.resolve())

    def test_resolve_build_target_working_dir_rejects_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            project = SimpleNamespace(
                root=project_root,
                manifest_path=project_root / "base_manifest.yaml",
            )

            with self.assertRaisesRegex(BuildTargetError, "must be a relative path"):
                resolve_build_target_working_dir(
                    project,
                    "api",
                    BuildTargetConfig(command="echo test", working_dir=str(project_root)),
                )

    def test_resolve_build_target_working_dir_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            project = SimpleNamespace(
                root=project_root,
                manifest_path=project_root / "base_manifest.yaml",
            )

            with self.assertRaisesRegex(BuildTargetError, "resolves outside"):
                resolve_build_target_working_dir(
                    project,
                    "api",
                    BuildTargetConfig(command="echo test", working_dir="../outside"),
                )

    def test_resolve_build_target_working_dir_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            project_root = workspace / "demo"
            outside = workspace / "outside"
            project_root.mkdir()
            outside.mkdir()
            (project_root / "linked").symlink_to(outside, target_is_directory=True)
            project = SimpleNamespace(
                root=project_root,
                manifest_path=project_root / "base_manifest.yaml",
            )

            with self.assertRaisesRegex(BuildTargetError, "resolves outside"):
                resolve_build_target_working_dir(
                    project,
                    "api",
                    BuildTargetConfig(command="echo test", working_dir="linked"),
                )

    def test_resolve_build_target_working_dir_rejects_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            project = SimpleNamespace(
                root=project_root,
                manifest_path=project_root / "base_manifest.yaml",
            )

            with self.assertRaisesRegex(BuildTargetError, "does not exist"):
                resolve_build_target_working_dir(
                    project,
                    "api",
                    BuildTargetConfig(command="echo test", working_dir="missing"),
                )

    def test_resolve_build_target_working_dir_rejects_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / "not-a-directory").write_text("fixture\n", encoding="utf-8")
            project = SimpleNamespace(
                root=project_root,
                manifest_path=project_root / "base_manifest.yaml",
            )

            with self.assertRaisesRegex(BuildTargetError, "not a directory"):
                resolve_build_target_working_dir(
                    project,
                    "api",
                    BuildTargetConfig(command="echo test", working_dir="not-a-directory"),
                )

    def test_build_targets_reject_invalid_working_dir_without_command_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_single_target_manifest(workspace / "demo", "demo", "../outside")

            status, stdout, stderr = run_engine(
                ["build-targets", "demo", "--format", "command-protocol"],
                base_home,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("resolves outside the project root", stderr)
        self.assertNotIn("echo test", stderr)

class BuildTargetTests(unittest.TestCase):
    def test_build_target_command_protocol_uses_explicit_typed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo with spaces"
            write_build_manifest_with_runner(project_root, "demo")

            status, stdout, stderr = run_engine(
                ["build-targets", "demo", "--format", "command-protocol"], base_home
            )

        self.assertEqual((status, stderr), (0, ""))
        _, records = loads_records(stdout, "build-target")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["target_name"], "package")
        self.assertEqual(records[0]["working_dir"], str((project_root / "services" / "api").resolve()))
        self.assertEqual(records[0]["runner"], "uv")
        self.assertTrue(records[0]["manifest_command_trust_required"])

    def test_projects_build_targets_defaults_to_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs"
            write_build_manifest(project_root, "demo")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["build-targets"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("\tapi\t", stdout)
        self.assertIn("\tworker\t", stdout)

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

    def test_projects_build_target_list_defaults_to_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs"
            write_build_manifest(project_root, "demo")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["build-target-list"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("\tapi\t", stdout)
        self.assertIn("\tworker\t", stdout)

    def test_projects_build_target_list_rejects_extra_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, stdout, stderr = run_engine(["build-target-list", "demo", "api"], base_home)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("accepts at most 1 positional project; got 2", stderr)

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

    def test_projects_build_target_list_json_is_stable_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo with spaces"
            write_build_manifest_with_runner(project_root, "demo")

            status, stdout, stderr = run_engine(
                ["build-target-list", "demo", "--format", "json"],
                base_home,
            )

        self.assertEqual((status, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(
            payload["project"],
            {
                "name": "demo",
                "root": str(project_root.resolve()),
                "manifest_path": str((project_root / "base_manifest.yaml").resolve()),
            },
        )
        self.assertEqual(
            payload["targets"],
            [
                {
                    "name": "package",
                    "working_dir": str((project_root / "services" / "api").resolve()),
                    "command": "python -m build",
                    "description": "Build the Python package.",
                    "runner": "uv",
                }
            ],
        )

    def test_projects_build_targets_respects_legacy_and_explicit_project_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            current_root = workspace / "current"
            other_root = workspace / "api"
            write_build_manifest(current_root, "current")
            write_build_manifest(other_root, "api")

            old_cwd = Path.cwd()
            try:
                os.chdir(current_root)
                legacy_status, legacy_stdout, legacy_stderr = run_engine(["build-targets", "api"], base_home)
                explicit_status, explicit_stdout, explicit_stderr = run_engine(
                    ["build-targets", "api", "--project", "current"],
                    base_home,
                )
            finally:
                os.chdir(old_cwd)

        self.assertEqual((legacy_status, legacy_stderr), (0, ""))
        self.assertTrue(legacy_stdout.startswith(f"api\t{other_root.resolve()}\t"))
        self.assertEqual((explicit_status, explicit_stderr), (0, ""))
        self.assertTrue(explicit_stdout.startswith(f"current\t{current_root.resolve()}\t"))
        self.assertIn("\tapi\t", explicit_stdout)

    def test_projects_build_targets_missing_current_project_is_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                status, stdout, stderr = run_engine(["build-targets", "unknown-target"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No base_manifest.yaml found", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_projects_build_targets_invalid_current_manifest_is_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            (workspace / "base_manifest.yaml").write_text("project: [\n", encoding="utf-8")

            old_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                status, stdout, stderr = run_engine(["build-targets", "api"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertNotIn("Traceback", stderr)

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
