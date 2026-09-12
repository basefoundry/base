from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine
from base_projects import workspace_checks


def write_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\npython: {{}}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_shell_manifest(project_root: Path, name: str) -> None:
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


def write_git_repository(repository_root: Path) -> None:
    repository_root.mkdir(parents=True)
    (repository_root / ".git").mkdir()


def write_bare_git_repository(repository_root: Path) -> None:
    repository_root.mkdir(parents=True)
    (repository_root / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (repository_root / "config").write_text("[core]\n\tbare = true\n", encoding="utf-8")
    (repository_root / "objects").mkdir()
    (repository_root / "refs").mkdir()


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


def read_last_check(home: Path, project: str) -> dict[str, str]:
    return json.loads((home / ".base.d" / project / "checks" / "last.json").read_text(encoding="utf-8"))


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


class WorkspaceUndeclaredRepositoryTests(unittest.TestCase):
    def test_workspace_doctor_does_not_report_declared_git_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path, repos="  - name: base\n  - name: bare")
            write_git_repository(workspace / "base")
            write_bare_git_repository(workspace / "bare")

            status, stdout, stderr = invoke_engine(
                ["doctor", "--workspace", str(workspace), "--manifest", str(manifest_path), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        findings = [check for project in payload["projects"] for check in project["checks"]]
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertNotIn("BASE-W013", {check["id"] for check in findings})

    def test_workspace_check_warns_without_failing_for_one_undeclared_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path, repos="  - name: base")
            write_git_repository(workspace / "base")
            write_git_repository(workspace / "unlisted")

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--manifest", str(manifest_path), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        undeclared = [
            check
            for project in payload["projects"]
            for check in project["checks"]
            if check["id"] == "BASE-W013"
        ]
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["status"], "warn")
        self.assertEqual(len(undeclared), 1)
        self.assertEqual(undeclared[0]["status"], "warn")
        self.assertEqual(undeclared[0]["details"]["path"], str((workspace / "unlisted").resolve()))
        self.assertIn("mark it as unmanaged", undeclared[0]["fix"])

    def test_workspace_doctor_lists_two_undeclared_repository_paths_in_text_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path, repos="  - name: base")
            write_git_repository(workspace / "base")
            write_git_repository(workspace / "unlisted-one")
            write_bare_git_repository(workspace / "unlisted-two")

            text_status, text_stdout, text_stderr = invoke_engine(
                ["doctor", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )
            json_status, json_stdout, json_stderr = invoke_engine(
                ["doctor", "--workspace", str(workspace), "--manifest", str(manifest_path), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(json_stdout)
        undeclared = [
            check
            for project in payload["projects"]
            for check in project["checks"]
            if check["id"] == "BASE-W013"
        ]
        self.assertEqual(text_status, 0)
        self.assertIn("Workspace doctor:", text_stdout)
        self.assertNotIn("BASE-W013", text_stdout)
        self.assertIn(str((workspace / "unlisted-one").resolve()), text_stderr)
        self.assertIn(str((workspace / "unlisted-two").resolve()), text_stderr)
        self.assertEqual(json_status, 0)
        self.assertEqual(json_stderr, "")
        self.assertEqual(payload["status"], "warn")
        self.assertEqual(
            {check["details"]["path"] for check in undeclared},
            {str((workspace / "unlisted-one").resolve()), str((workspace / "unlisted-two").resolve())},
        )

class WorkspaceSymlinkTests(unittest.TestCase):
    def test_workspace_check_matches_logical_symlink_names_and_skips_outside_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            outside = root / "outside"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            outside.mkdir()
            write_default_manifest(base_home)
            manifest_path.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "workspace:",
                        "  name: symlink-suite",
                        "repos:",
                        "  - name: api",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            physical = root / "physical-api"
            write_shell_manifest(physical, "api")
            (physical / ".git").mkdir()
            (workspace / "api").symlink_to(physical, target_is_directory=True)
            outside_project = outside / "physical-outside"
            write_shell_manifest(outside_project, "outside")
            (outside_project / ".git").mkdir()
            (workspace / "outside").symlink_to(outside_project, target_is_directory=True)

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--manifest", str(manifest_path), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        projects_by_repo = {project["repository"]: project for project in payload["projects"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(set(projects_by_repo), {"api"})
        self.assertTrue(projects_by_repo["api"]["expected"])


class WorkspaceCheckTests(unittest.TestCase):
    def test_workspace_check_records_ok_and_warning_results_for_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_workspace_manifest(manifest_path, repos="  - name: demo")
            write_shell_manifest(workspace / "demo", "demo")
            write_shell_manifest(workspace / "extra", "extra")

            status, stdout, stderr = invoke_engine(
                ["check", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )
            demo_record = read_last_check(home, "demo")
            extra_record = read_last_check(home, "extra")
            status_status, status_stdout, status_stderr = invoke_engine(
                ["status", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 0)
        self.assertIn("extra", stdout + stderr)
        self.assertEqual(demo_record["command"], "basectl workspace check")
        self.assertEqual(demo_record["status"], "ok")
        self.assertEqual(extra_record["command"], "basectl workspace check")
        self.assertEqual(extra_record["status"], "warn")
        self.assertRegex(demo_record["checked_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(status_status, 0)
        self.assertEqual(status_stderr, "")
        self.assertIn(demo_record["checked_at"][:10], status_stdout)
        self.assertIn(extra_record["checked_at"][:10], status_stdout)

    def test_workspace_check_records_error_results_before_returning_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = invoke_engine(["check", "--workspace", str(workspace)], base_home, home)
            record = read_last_check(home, "demo")

        self.assertEqual(status, 1)
        self.assertIn("Project: demo [error]", stdout)
        self.assertIn("demo", stdout + stderr)
        self.assertEqual(record["command"], "basectl workspace check")
        self.assertEqual(record["status"], "error")

    def test_workspace_check_json_reports_a_false_record_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_shell_manifest(workspace / "demo", "demo")

            with mock.patch.object(workspace_checks, "write_check_record", return_value=False):
                status, stdout, stderr = invoke_engine(
                    ["check", "--workspace", str(workspace), "--format", "json"],
                    base_home,
                    home,
                )

            expected_path = home / ".base.d" / "demo" / "checks" / "last.json"

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(stderr, "")
        self.assertEqual(
            payload["record_warnings"],
            [
                {
                    "project": "demo",
                    "status": "warn",
                    "message": "Latest check record could not be saved.",
                    "fix": "Ensure the Base state directory is writable, then rerun the check.",
                    "path": str(expected_path),
                }
            ],
        )

    def test_workspace_check_text_reports_a_record_write_failure_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_shell_manifest(workspace / "demo", "demo")

            with mock.patch.object(workspace_checks, "write_check_record", return_value=False):
                status, stdout, stderr = invoke_engine(
                    ["check", "--workspace", str(workspace)],
                    base_home,
                    home,
                )

            expected_path = home / ".base.d" / "demo" / "checks" / "last.json"

        self.assertEqual(status, 0)
        self.assertIn("Project: demo [ok]", stdout)
        self.assertEqual(stderr.count("Latest check record could not be saved."), 1)
        self.assertIn("Project 'demo'", stderr)
        self.assertIn(str(expected_path), stderr)
        self.assertNotIn("Traceback", stderr)

    def test_workspace_check_reports_an_unwritable_record_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_shell_manifest(workspace / "demo", "demo")
            write_record = workspace_checks.write_check_record

            def reject_record_directory(*args, **kwargs) -> bool:
                with mock.patch.object(Path, "mkdir", side_effect=PermissionError("read-only")):
                    return write_record(*args, **kwargs)

            with mock.patch.object(
                workspace_checks,
                "write_check_record",
                side_effect=reject_record_directory,
            ):
                status, stdout, stderr = invoke_engine(
                    ["check", "--workspace", str(workspace), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(stderr, "")
        self.assertEqual([warning["project"] for warning in payload["record_warnings"]], ["demo"])

    def test_workspace_check_preserves_error_exit_when_record_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")
            old_record_path = home / ".base.d" / "demo" / "checks" / "last.json"
            old_record_path.parent.mkdir(parents=True)
            old_record_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project": "demo",
                        "command": "basectl workspace check",
                        "status": "warn",
                        "checked_at": "2026-01-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(Path, "replace", side_effect=OSError("read-only")):
                status, stdout, stderr = invoke_engine(
                    ["check", "--workspace", str(workspace), "--format", "json"],
                    base_home,
                    home,
                )
            retained_record = json.loads(old_record_path.read_text(encoding="utf-8"))

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(stderr, "")
        self.assertEqual([warning["project"] for warning in payload["record_warnings"]], ["demo"])
        self.assertEqual(retained_record["checked_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(retained_record["status"], "warn")

    def test_workspace_check_keeps_successful_records_when_one_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_shell_manifest(workspace / "alpha", "alpha")
            write_shell_manifest(workspace / "beta", "beta")
            write_record = workspace_checks.write_check_record

            def write_partially(
                path: Path,
                project: str,
                result_status: str,
                checked_at: str,
                *,
                command: str,
            ) -> bool:
                if project == "beta":
                    return False
                return write_record(
                    path,
                    project,
                    result_status,
                    checked_at,
                    command=command,
                )

            with mock.patch.object(
                workspace_checks,
                "write_check_record",
                side_effect=write_partially,
            ):
                status, stdout, stderr = invoke_engine(
                    ["check", "--workspace", str(workspace), "--format", "json"],
                    base_home,
                    home,
                )

            alpha_record = read_last_check(home, "alpha")
            beta_record_path = home / ".base.d" / "beta" / "checks" / "last.json"
            beta_record_exists = beta_record_path.exists()

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(alpha_record["status"], "ok")
        self.assertFalse(beta_record_exists)
        self.assertEqual([warning["project"] for warning in payload["record_warnings"]], ["beta"])

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
                if project_name == "base":
                    python_bin = home / ".base.d" / project_name / ".venv" / "bin" / "python"
                else:
                    python_bin = workspace / project_name / ".venv" / "bin" / "python"
                write_ready_python_bin(python_bin)

            status, stdout, stderr = invoke_engine(
                ["check", "--verify-project-runtime", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 1)
        self.assertIn(f"Workspace check: {workspace.resolve()} (5 repositories)", stdout)
        self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
        self.assertIn("Repository: base [ok]", stdout)
        self.assertIn("Repository: docs [ok]", stdout)
        self.assertIn("Repository: api [error]", stdout)
        self.assertIn("Repository: optional-tool [warn]", stdout)
        self.assertIn("Repository: extra [warn]", stdout)
        self.assertIn("workspace_repository_presence", stdout)
        self.assertIn("workspace_manifest_membership", stdout)
        self.assertEqual(stderr, "")
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
        self.assertIn("Repository: broken [error]", stdout)
        self.assertIn("project_manifest", stdout)
        self.assertEqual(stderr, "")

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
            python_bin = workspace / "demo" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)
            broken_root = workspace / "broken"
            broken_root.mkdir(parents=True)
            (broken_root / "base_manifest.yaml").write_text("project: [", encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["check", "--verify-project-runtime", "--workspace", str(workspace)],
                base_home, home,
            )

        self.assertEqual(status, 1)
        self.assertIn(f"Workspace check: {workspace.resolve()} (2 projects)", stdout)
        self.assertIn("Project: demo [ok]", stdout)
        self.assertIn("project_virtualenv", stdout)
        self.assertIn("manifest", stdout)
        self.assertIn("Project: broken [error]", stdout)
        self.assertIn("project_manifest", stdout)
        self.assertEqual(stderr, "")
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

            with (
                mock.patch("base_setup.uv.uv_executable", return_value=Path("uv")),
                mock.patch(
                    "base_setup.uv.process.run_capture",
                    return_value=subprocess.CompletedProcess(
                        ["uv"], 0, stdout='{"sync": {"changes": []}}', stderr=""
                    ),
                ),
            ):
                status, stdout, stderr = invoke_engine(
                    ["check", "--verify-project-runtime", "--workspace", str(workspace)],
                    base_home, home,
                )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Project: bankbuddy [ok]", stdout)
        self.assertIn("uv project virtualenv", stdout)
        self.assertNotIn("BASE-P154", stdout)
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

            with (
                mock.patch("base_setup.uv.uv_executable", return_value=Path("uv")),
                mock.patch(
                    "base_setup.uv.process.run_capture",
                    return_value=subprocess.CompletedProcess(
                        ["uv"], 0, stdout='{"sync": {"changes": []}}', stderr=""
                    ),
                ),
            ):
                status, stdout, stderr = invoke_engine(
                    ["doctor", "--verify-project-runtime", "--workspace", str(workspace)],
                    base_home, home,
                )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Project: bankbuddy [ok]", stdout)
        self.assertIn("BASE-P154", stdout)
        self.assertNotIn("BASE-P050", stdout)
        self.assertIn("All discovered projects passed.", stdout)

    def test_workspace_check_and_doctor_skip_project_venv_for_shell_only_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_shell_manifest(workspace / "shell-only", "shell-only")

            for command in ("check", "doctor"):
                with self.subTest(command=command):
                    status, stdout, stderr = invoke_engine(
                        [command, "--workspace", str(workspace)],
                        base_home,
                        home,
                    )
                    self.assertEqual(status, 0, stderr)
                    self.assertIn("Project: shell-only [ok]", stdout)
                    self.assertNotIn("BASE-P050", stdout + stderr)
                    self.assertIn("All discovered projects passed.", stdout)

            self.assertFalse((workspace / "shell-only" / ".venv").exists())

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
        self.assertEqual(payload["record_warnings"], [])
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
            python_bin = workspace / "demo" / ".venv" / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            python_bin.chmod(0o755)

            status, stdout, stderr = invoke_engine(
                ["check", "--verify-project-runtime", "--workspace", str(workspace), "--format", "json"],
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

    def test_workspace_check_text_avoids_doctor_finding_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")

            with mock.patch("base_projects.workspace_report_text.print_doctor_finding") as doctor_finding:
                status, stdout, stderr = invoke_engine(["check", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        doctor_finding.assert_not_called()
        self.assertIn("project_virtualenv", stdout)
        self.assertIn("Fix: Run 'basectl setup demo --recreate-venv'", stdout)
        self.assertNotIn("BASE-P050", stdout)

    def test_workspace_doctor_text_keeps_finding_ids_and_fix_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_default_manifest(base_home)
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = invoke_engine(["doctor", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 1)
        self.assertIn("BASE-P050", stderr)
        self.assertIn("Fix: Run 'basectl setup demo --recreate-venv'", stderr)
        self.assertNotIn("BASE-P050", stdout)

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
            python_bin = workspace / "demo" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)

            status, stdout, stderr = invoke_engine(
                ["doctor", "--verify-project-runtime", "--workspace", str(workspace)],
                base_home, home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace doctor: {workspace.resolve()} (1 projects)", stdout)
        self.assertIn("Project: demo [ok]", stdout)
        self.assertIn("All discovered projects passed.", stdout)
