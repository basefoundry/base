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


def write_default_manifest(base_home: Path) -> None:
    default_manifest = base_home / "lib" / "base" / "default_manifest.yaml"
    default_manifest.parent.mkdir(parents=True)
    default_manifest.write_text(
        "project:\n  name: __base_defaults__\nartifacts: []\n",
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
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/usr/bin/env python\n", encoding="utf-8")
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
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project_count"], 1)
        self.assertEqual(payload["projects"][0]["name"], "demo")
        self.assertEqual(payload["projects"][0]["status"], "error")
        self.assertEqual(payload["projects"][0]["checks"][0]["id"], "BASE-P050")
        self.assertEqual(payload["projects"][0]["checks"][0]["status"], "error")
        self.assertEqual(payload["projects"][0]["checks"][0]["ok"], False)

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
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/usr/bin/env python\n", encoding="utf-8")

            status, stdout, stderr = invoke_engine(["doctor", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace doctor: {workspace.resolve()} (1 projects)", stdout)
        self.assertIn("Project: demo [ok]", stdout)
        self.assertIn("All discovered projects passed.", stdout)
