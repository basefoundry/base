from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_workspace_manifest(path: Path, repositories: tuple[str, ...]) -> None:
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspace:",
                "  name: test-workspace",
                "repos:",
                *[f"  - name: {repository}" for repository in repositories],
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_test_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ntest:\n  command: ./run-tests.sh\nartifacts: []\n",
        encoding="utf-8",
    )


def write_shell_only_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_fake_basectl(base_home: Path) -> Path:
    basectl = base_home / "bin" / "basectl"
    basectl.parent.mkdir(parents=True)
    basectl.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    basectl.chmod(0o755)
    return basectl


def invoke_workspace_test(
    args: list[str],
    base_home: Path,
    home: Path,
) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    env = {
        "HOME": str(home),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_MANIFEST": "",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class WorkspaceTestCommandTests(unittest.TestCase):
    def test_workspace_test_runs_all_projects_and_reports_json_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha", "beta"))
            write_test_manifest(workspace / "alpha", "alpha")
            write_test_manifest(workspace / "beta", "beta")
            completed = subprocess.CompletedProcess([], 0, "alpha output\n", "")

            with mock.patch("base_projects.workspace_test.subprocess.run", return_value=completed) as run:
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["counts"], {"passed": 2, "failed": 0, "skipped": 0})
        self.assertEqual(payload["selected_projects"], ["alpha", "beta"])
        self.assertEqual([project["status"] for project in payload["projects"]], ["passed", "passed"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].kwargs["cwd"], (workspace / "alpha").resolve())
        self.assertEqual(run.call_args_list[1].kwargs["cwd"], (workspace / "beta").resolve())
        self.assertEqual(
            run.call_args_list[0].args[0],
            [str((base_home / "bin" / "basectl").resolve()), "test", "--workspace", str(workspace.resolve())],
        )

    def test_workspace_test_continues_after_a_project_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha", "beta", "gamma"))
            for project in ("alpha", "beta", "gamma"):
                write_test_manifest(workspace / project, project)
            results = [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 7, "", "beta failed\n"),
                subprocess.CompletedProcess([], 0, "", ""),
            ]

            with mock.patch("base_projects.workspace_test.subprocess.run", side_effect=results):
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(payload["counts"], {"passed": 2, "failed": 1, "skipped": 0})
        self.assertEqual(payload["projects"][1]["exit_code"], 7)
        self.assertEqual(payload["projects"][1]["stderr"], "beta failed\n")
        self.assertEqual(stderr, "")

    def test_workspace_test_fail_fast_skips_remaining_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha", "beta", "gamma"))
            for project in ("alpha", "beta", "gamma"):
                write_test_manifest(workspace / project, project)

            with mock.patch(
                "base_projects.workspace_test.subprocess.run",
                return_value=subprocess.CompletedProcess([], 3, "", "failed\n"),
            ) as run:
                status, stdout, stderr = invoke_workspace_test(
                    [
                        "test",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest),
                        "--fail-fast",
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(payload["counts"], {"passed": 0, "failed": 1, "skipped": 2})
        self.assertEqual(payload["projects"][1]["status"], "skipped")
        self.assertIn("--fail-fast", payload["projects"][1]["detail"])
        self.assertEqual(stderr, "")

    def test_workspace_test_projects_filter_runs_only_selected_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha", "beta"))
            write_test_manifest(workspace / "alpha", "alpha")
            write_test_manifest(workspace / "beta", "beta")

            with mock.patch(
                "base_projects.workspace_test.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run:
                status, stdout, stderr = invoke_workspace_test(
                    [
                        "test",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest),
                        "--projects",
                        "beta",
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(payload["selected_projects"], ["beta"])
        self.assertEqual(payload["projects"][0]["project"], "beta")

    def test_workspace_test_skips_project_without_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha", "shell-only"))
            write_test_manifest(workspace / "alpha", "alpha")
            write_shell_only_manifest(workspace / "shell-only", "shell-only")

            with mock.patch(
                "base_projects.workspace_test.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run:
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(payload["counts"], {"passed": 1, "failed": 0, "skipped": 1})
        self.assertEqual(payload["projects"][1]["status"], "skipped")
        self.assertIn("does not declare a test command", payload["projects"][1]["detail"])
