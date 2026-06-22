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


def write_uv_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\npython:\n  manager: uv\n",
        encoding="utf-8",
    )
    (project_root / "pyproject.toml").write_text(
        f"[project]\nname = \"{name}\"\nrequires-python = \">=3.12\"\n",
        encoding="utf-8",
    )
    (project_root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    python_bin = project_root / ".venv" / "bin" / "python"
    write_ready_python_bin(python_bin)


def write_ready_python_bin(python_bin: Path) -> None:
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_bin.chmod(0o755)


def write_workspace_manifest(path: Path, repos: str | None = None) -> None:
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspace:",
                "  name: demo-suite",
                "repos:",
                repos
                or "\n".join(
                    [
                        "  - name: base",
                        "  - name: docs",
                        "  - name: api",
                        "    required: true",
                        "  - name: optional-tool",
                        "    required: false",
                    ]
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_default_manifest(base_home: Path) -> None:
    default_manifest = base_home / "lib" / "base" / "default_manifest.yaml"
    default_manifest.parent.mkdir(parents=True)
    default_manifest.write_text(
        "project:\n  name: base-defaults\nartifacts: []\n",
        encoding="utf-8",
    )


def invoke_engine(args: list[str], base_home: Path, home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
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


class WorkspaceCheckTests(unittest.TestCase):
    def test_workspace_check_manifest_reports_expected_missing_and_extra_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path)
            write_manifest(workspace / "base", "base")
            (workspace / "docs").mkdir(parents=True)
            write_manifest(workspace / "extra", "extra")
            for project_name in ("base", "extra"):
                python_bin = home / ".base.d" / project_name / ".venv" / "bin" / "python"
                write_ready_python_bin(python_bin)

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace check: {workspace.resolve()} (5 repositories)", stdout)
        self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
        self.assertIn("Repository: base [ok]", stdout)
        self.assertIn("Repository: docs [ok]", stdout)
        self.assertIn("Repository: api [error]", stdout)
        self.assertIn("Repository: optional-tool [warn]", stdout)
        self.assertIn("Repository: extra [warn]", stdout)
        self.assertIn("BASE-W010", stdout)
        self.assertIn("BASE-W011", stdout)
        self.assertIn("BASE-W012", stdout)
        self.assertIn("Workspace has 1 error finding(s).", stdout)

    def test_workspace_check_manifest_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path)
            write_manifest(workspace / "base", "base")
            (workspace / "docs").mkdir(parents=True)
            write_manifest(workspace / "extra", "extra")
            for project_name in ("base", "extra"):
                python_bin = home / ".base.d" / project_name / ".venv" / "bin" / "python"
                write_ready_python_bin(python_bin)

            status, stdout, stderr = invoke_engine(
                [
                    "check",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--format",
                    "json",
                ],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        projects_by_repo = {project["repository"]: project for project in payload["projects"]}
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertTrue(stdout.startswith("{\n"))
        self.assertIn('  "workspace": ', stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["workspace_manifest"]["name"], "demo-suite")
        self.assertEqual(payload["repository_count"], 5)
        self.assertEqual(projects_by_repo["base"]["checks"][0]["id"], "BASE-W010")
        self.assertEqual(projects_by_repo["base"]["checks"][0]["status"], "ok")
        self.assertEqual(projects_by_repo["docs"]["checks"][0]["id"], "BASE-W012")
        self.assertEqual(projects_by_repo["docs"]["checks"][0]["status"], "ok")
        self.assertEqual(projects_by_repo["api"]["status"], "error")
        self.assertEqual(projects_by_repo["api"]["checks"][0]["id"], "BASE-W010")
        self.assertEqual(projects_by_repo["api"]["checks"][0]["status"], "error")
        self.assertEqual(projects_by_repo["api"]["checks"][0]["details"]["required"], True)
        self.assertEqual(projects_by_repo["optional-tool"]["status"], "warn")
        self.assertEqual(projects_by_repo["optional-tool"]["checks"][0]["status"], "warn")
        self.assertEqual(projects_by_repo["extra"]["checks"][0]["id"], "BASE-W011")
        self.assertEqual(projects_by_repo["extra"]["checks"][0]["status"], "warn")

    def test_workspace_check_manifest_reports_invalid_project_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            broken_root = workspace / "broken"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path, repos="  - name: broken")
            broken_root.mkdir(parents=True)
            (broken_root / "base_manifest.yaml").write_text("project: [", encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn("Repository: broken [error]", stdout)
        self.assertIn("BASE-P002", stdout)

    def test_workspace_check_reports_project_findings_and_invalid_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")
            python_bin = home / ".base.d" / "demo" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)
            broken_root = workspace / "broken"
            broken_root.mkdir(parents=True)
            (broken_root / "base_manifest.yaml").write_text("project: [", encoding="utf-8")

            status, stdout, stderr = invoke_engine(["check", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace check: {workspace.resolve()} (2 projects)", stdout)
        self.assertIn("Project: demo [ok]", stdout)
        self.assertIn("BASE-P050", stdout)
        self.assertIn("BASE-P001", stdout)
        self.assertIn("Project: broken [error]", stdout)
        self.assertIn("BASE-P002", stdout)
        self.assertIn("Workspace has 1 error finding(s).", stdout)

    def test_workspace_check_uses_uv_project_venv_without_base_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_uv_manifest(workspace / "bankbuddy", "bankbuddy")

            with mock.patch("base_setup.uv.process.command_exists", return_value=True):
                status, stdout, stderr = invoke_engine(["check", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Project: bankbuddy [ok]", stdout)
        self.assertIn("BASE-P154", stdout)
        self.assertNotIn("BASE-P050", stdout)
        self.assertIn("All discovered projects passed.", stdout)

    def test_workspace_doctor_uses_uv_project_venv_without_base_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_uv_manifest(workspace / "bankbuddy", "bankbuddy")

            with mock.patch("base_setup.uv.process.command_exists", return_value=True):
                status, stdout, stderr = invoke_engine(["doctor", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Project: bankbuddy [ok]", stdout)
        self.assertIn("BASE-P154", stdout)
        self.assertNotIn("BASE-P050", stdout)
        self.assertIn("All discovered projects passed.", stdout)

    def test_workspace_check_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertTrue(stdout.startswith("{\n"))
        self.assertIn('  "workspace": ', stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project_count"], 1)
        self.assertEqual(payload["projects"][0]["name"], "demo")
        self.assertEqual(payload["projects"][0]["status"], "error")
        self.assertEqual(payload["projects"][0]["checks"][0]["id"], "BASE-P050")
        self.assertEqual(payload["projects"][0]["checks"][0]["status"], "error")
        self.assertNotIn("ok", payload["projects"][0]["checks"][0])

    def test_workspace_check_reports_unrunnable_project_venv_as_p050(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")
            python_bin = home / ".base.d" / "demo" / ".venv" / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            python_bin.chmod(0o755)

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        checks = payload["projects"][0]["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["projects"][0]["status"], "error")
        self.assertEqual(checks[0]["id"], "BASE-P050")
        self.assertEqual(checks[0]["status"], "error")
        self.assertIn("basectl setup demo --recreate-venv", checks[0]["fix"])
        self.assertNotIn("BASE-P040", {check["id"] for check in checks})

    def test_workspace_doctor_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = invoke_engine(
                ["doctor", "--workspace", str(workspace), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertTrue(stdout.startswith("{\n"))
        self.assertIn('  "workspace": ', stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertEqual(payload["projects"][0]["checks"][0]["id"], "BASE-P050")
        self.assertEqual(payload["projects"][0]["checks"][0]["status"], "error")
        self.assertNotIn("ok", payload["projects"][0]["checks"][0])

    def test_workspace_doctor_text_reports_all_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")
            python_bin = home / ".base.d" / "demo" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)

            status, stdout, stderr = invoke_engine(["doctor", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace doctor: {workspace.resolve()} (1 projects)", stdout)
        self.assertIn("Project: demo [ok]", stdout)
        self.assertIn("All discovered projects passed.", stdout)
