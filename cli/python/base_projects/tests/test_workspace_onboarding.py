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


def write_project_manifest(project_root: Path, name: str, test_command: str | None = None) -> None:
    project_root.mkdir(parents=True)
    lines = [
        "project:",
        f"  name: {name}",
    ]
    if test_command is not None:
        lines.extend(
            [
                "test:",
                f"  command: {test_command}",
            ]
        )
    lines.extend(["python: {}", "artifacts: []", ""])
    (project_root / "base_manifest.yaml").write_text("\n".join(lines), encoding="utf-8")


def write_ready_python_bin(home: Path, project: str) -> None:
    python_bin = home / ".base.d" / project / ".venv" / "bin" / "python"
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
                "    url: git@github.com:basefoundry/base.git",
                "    default_branch: main",
                "  - name: docs",
                "  - name: api",
                "    url: git@github.com:example/api.git",
                "  - name: optional-tool",
                "    url: git@github.com:example/optional-tool.git",
                "    required: false",
                "",
            ]
        ),
        encoding="utf-8",
    )


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


def invoke_engine(args: list[str], base_home: Path, home: Path) -> tuple[int, str, str]:
    stdout = TerminalStringIO()
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


class WorkspaceOnboardingTests(unittest.TestCase):
    def test_shell_only_repository_is_ready_without_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            manifest_path.write_text(
                "schema_version: 1\nworkspace:\n  name: demo-suite\nrepos:\n  - name: shell-only\n",
                encoding="utf-8",
            )
            project_root = workspace / "shell-only"
            project_root.mkdir(parents=True)
            (project_root / "base_manifest.yaml").write_text(
                "project:\n  name: shell-only\nartifacts: []\n",
                encoding="utf-8",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "onboarding",
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

        repository = json.loads(stdout)["repositories"][0]
        self.assertEqual(status, 0, stderr)
        self.assertEqual(repository["status"], "ready")
        self.assertEqual(repository["venv"], "not_applicable")
        self.assertEqual(repository["next_action"], "Run validation command.")

    def test_workspace_onboarding_json_reports_complete_manifest_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_project_manifest(workspace / "base", "base", "./bin/base-test")
            write_project_manifest(workspace / "docs", "docs")
            write_project_manifest(workspace / "api", "api", "pytest tests/")
            write_project_manifest(workspace / "optional-tool", "optional-tool")
            for project in ("base", "docs", "api", "optional-tool"):
                write_ready_python_bin(home, project)

            status, stdout, stderr = invoke_engine(
                [
                    "onboarding",
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
        repositories = {item["repository"]: item for item in payload["repositories"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertEqual(payload["workspace_manifest"]["name"], "demo-suite")
        self.assertEqual(payload["repository_count"], 4)
        self.assertEqual(repositories["base"]["status"], "ready")
        self.assertEqual(repositories["base"]["discovery_status"], "present")
        self.assertEqual(repositories["base"]["path"], str((workspace / "base").resolve()))
        self.assertEqual(repositories["base"]["setup_command"], f"cd {(workspace / 'base').resolve()} && basectl setup")
        self.assertEqual(
            repositories["base"]["validation_command"],
            f"cd {(workspace / 'base').resolve()} && basectl check",
        )
        self.assertEqual(repositories["base"]["test_command"], "./bin/base-test")
        self.assertIsNone(repositories["base"]["clone_command"])
        self.assertEqual(repositories["docs"]["test_command"], None)
        self.assertEqual(repositories["optional-tool"]["required"], False)

    def test_workspace_onboarding_text_reports_missing_required_and_optional_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_project_manifest(workspace / "base", "base", "./bin/base-test")
            write_ready_python_bin(home, "base")

            status, stdout, stderr = invoke_engine(
                ["onboarding", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace onboarding: {workspace.resolve()} (demo-suite)", stdout)
        self.assertIn(f"Workspace manifest: {manifest_path.resolve()}", stdout)
        self.assertIn("base                 yes      ready", stdout)
        self.assertIn("api                  yes      missing_required", stdout)
        self.assertIn("optional-tool        no       missing_optional", stdout)
        self.assertIn(f"clone: git clone git@github.com:example/api.git {(workspace / 'api').resolve()}", stdout)
        self.assertIn("optional repository is missing; clone it only if this role needs it", stdout)
        self.assertIn(f"validate: cd {(workspace / 'base').resolve()} && basectl check", stdout)
        self.assertIn("test: ./bin/base-test", stdout)

    def test_workspace_onboarding_json_reports_partial_non_base_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_project_manifest(workspace / "base", "base")
            (workspace / "docs").mkdir(parents=True)
            write_ready_python_bin(home, "base")

            status, stdout, stderr = invoke_engine(
                [
                    "onboarding",
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
        repositories = {item["repository"]: item for item in payload["repositories"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(repositories["docs"]["status"], "present_without_manifest")
        self.assertEqual(repositories["docs"]["discovery_status"], "present")
        self.assertEqual(repositories["docs"]["manifest"], "missing")
        self.assertEqual(repositories["docs"]["setup_command"], None)
        self.assertEqual(repositories["docs"]["validation_command"], None)
        self.assertEqual(
            repositories["docs"]["next_action"],
            f"Add or verify {(workspace / 'docs' / 'base_manifest.yaml').resolve()} before Base setup.",
        )
