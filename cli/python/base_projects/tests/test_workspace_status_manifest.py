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


def write_last_check(home: Path, project: str, checked_at: str, status: str = "ok") -> None:
    record_path = home / ".base.d" / project / "checks" / "last.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": project,
                "command": "basectl check",
                "status": status,
                "checked_at": checked_at,
            }
        ),
        encoding="utf-8",
    )


def write_ready_python_bin(python_bin: Path) -> None:
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_bin.chmod(0o755)


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspace:",
                "  name: demo-suite",
                "repos:",
                "  - name: base",
                "    url: git@github.com:codeforester/base.git",
                "    default_branch: master",
                "  - name: docs",
                "  - name: api",
                "    required: true",
                "  - name: optional-tool",
                "    required: false",
                "",
            ]
        ),
        encoding="utf-8",
    )


def invoke_engine(
    args: list[str],
    base_home: Path,
    home: Path,
    user_config: str | None = None,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    if user_config is not None:
        config_path = home / ".base.d" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(user_config, encoding="utf-8")
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


class WorkspaceStatusManifestTests(unittest.TestCase):
    def test_workspace_status_manifest_reports_expected_missing_and_extra_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_manifest(workspace / "base", "base")
            (workspace / "docs").mkdir(parents=True)
            write_manifest(workspace / "extra", "extra")
            python_bin = home / ".base.d" / "base" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)
            write_last_check(home, "base", "2026-06-17T14:30:00Z")

            status, stdout, stderr = invoke_engine(
                ["status", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace: {workspace.resolve()} (5 repositories)", stdout)
        self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
        self.assertIn("base                 ok     yes      present  ready          valid    2026-06-17", stdout)
        self.assertIn("docs                 ok", stdout)
        self.assertIn("api                  error", stdout)
        self.assertIn("optional-tool        warn", stdout)
        self.assertIn("extra                warn", stdout)
        self.assertIn("3 repositories need attention", stdout)

    def test_workspace_status_manifest_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_manifest(workspace / "base", "base")
            (workspace / "docs").mkdir(parents=True)
            python_bin = home / ".base.d" / "base" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)
            write_last_check(home, "base", "2026-06-17T14:30:00Z")

            status, stdout, stderr = invoke_engine(
                [
                    "status",
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
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertEqual(payload["workspace_manifest"]["path"], str(manifest_path.resolve()))
        self.assertEqual(payload["workspace_manifest"]["name"], "demo-suite")
        self.assertEqual(payload["repository_count"], 4)
        self.assertEqual(projects_by_repo["base"]["status"], "ok")
        self.assertEqual(projects_by_repo["base"]["required"], True)
        self.assertEqual(projects_by_repo["base"]["repo"], "present")
        self.assertEqual(projects_by_repo["base"]["url"], "git@github.com:codeforester/base.git")
        self.assertEqual(
            projects_by_repo["base"]["last_check"],
            {
                "checked_at": "2026-06-17T14:30:00Z",
                "status": "ok",
            },
        )
        self.assertEqual(projects_by_repo["docs"]["manifest"], "missing")
        self.assertEqual(projects_by_repo["docs"]["venv"], "not_applicable")
        self.assertEqual(projects_by_repo["api"]["status"], "error")
        self.assertEqual(projects_by_repo["api"]["repo"], "missing")
        self.assertEqual(projects_by_repo["optional-tool"]["status"], "warn")
        self.assertEqual(projects_by_repo["optional-tool"]["required"], False)

    def test_workspace_status_uses_configured_manifest_when_flag_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_workspace_manifest(manifest_path)

            status, stdout, stderr = invoke_engine(
                ["status", "--workspace", str(workspace)],
                base_home,
                home,
                user_config=f"workspace:\n  manifest: {manifest_path}\n",
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
        self.assertIn("api                  error", stdout)

    def test_workspace_status_manifest_flag_overrides_configured_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            configured_manifest = root / "configured.yaml"
            cli_manifest = root / "cli.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_workspace_manifest(configured_manifest)
            cli_manifest.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "workspace:",
                        "  name: cli-suite",
                        "repos:",
                        "  - name: cli-only",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "status",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(cli_manifest),
                ],
                base_home,
                home,
                user_config=f"workspace:\n  manifest: {configured_manifest}\n",
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace manifest: {cli_manifest.resolve()} (cli-suite)", stdout)
        self.assertIn("cli-only             error", stdout)
        self.assertNotIn("demo-suite", stdout)
