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
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_repo_inspection import WorkspaceRepoInspection
from base_projects.workspace_test import workspace_test_manifest_target
from base_setup.manifest import read_manifest
from base_setup.manifest_trust import ManifestCommandTrustStore
from base_setup.manifest_trust import compute_trust_identity


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


def allow_workspace_test_manifests(workspace: Path, trusted_projects: tuple[str, ...] | None) -> None:
    trust_store = ManifestCommandTrustStore()
    for manifest_path in workspace.rglob("base_manifest.yaml"):
        manifest = read_manifest(manifest_path)
        if trusted_projects is not None and manifest.project_name not in trusted_projects:
            continue
        trust_store.allow(compute_trust_identity(manifest), base_version="test")


def write_binary_output_basectl(base_home: Path) -> Path:
    basectl = base_home / "bin" / "basectl"
    basectl.parent.mkdir(parents=True, exist_ok=True)
    basectl.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stdout.buffer.write(b'result: \\xff\\n')\n"
        "sys.stderr.buffer.write(b'warning: \\xfe\\n')\n",
        encoding="utf-8",
    )
    basectl.chmod(0o755)
    return basectl


def invoke_workspace_test(
    args: list[str],
    base_home: Path,
    home: Path,
    *,
    trusted_projects: tuple[str, ...] | None = None,
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
        workspace = Path(args[args.index("--workspace") + 1])
        allow_workspace_test_manifests(workspace, trusted_projects)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class WorkspaceTestCommandTests(unittest.TestCase):
    def test_workspace_test_fails_closed_when_inspected_manifest_is_missing(self) -> None:
        root = Path("/workspace/api")
        inspection = WorkspaceRepoInspection(
            name="api",
            root=root,
            manifest_path=root / "base_manifest.yaml",
            project_name=None,
            manifest=None,
            state="inspected",
            reason=None,
            required=True,
            fatal=False,
        )

        with mock.patch("base_projects.workspace_test.inspect_workspace_repo", return_value=inspection):
            target = workspace_test_manifest_target(root.parent, WorkspaceManifestRepo(name="api"))

        self.assertEqual(target.action, "skip")
        self.assertEqual(target.reason, "workspace repository inspection did not return a parsed manifest")
        self.assertTrue(target.fatal)

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

            with mock.patch("base_projects.workspace_test.run_workspace_subprocess", return_value=completed) as run:
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["counts"], {"passed": 2, "failed": 0, "blocked": 0, "not_run": 0, "skipped": 0})
        self.assertEqual(payload["selected_projects"], ["alpha", "beta"])
        self.assertEqual([project["status"] for project in payload["projects"]], ["passed", "passed"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].kwargs["cwd"], (workspace / "alpha").resolve())
        self.assertEqual(run.call_args_list[1].kwargs["cwd"], (workspace / "beta").resolve())
        self.assertEqual(
            run.call_args_list[0].args[0],
            [str((base_home / "bin" / "basectl").resolve()), "test", "--workspace", str(workspace.resolve())],
        )

    def test_workspace_test_replaces_invalid_utf8_in_json_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_binary_output_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha",))
            write_test_manifest(workspace / "alpha", "alpha")

            status, stdout, stderr = invoke_workspace_test(
                ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["projects"][0]["stdout"], "result: \ufffd\n")
        self.assertEqual(payload["projects"][0]["stderr"], "warning: \ufffd\n")

    def test_workspace_test_redacts_captured_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha",))
            write_test_manifest(workspace / "alpha", "alpha")

            with mock.patch(
                "base_projects.workspace_test.run_workspace_subprocess",
                return_value=subprocess.CompletedProcess(
                    [], 1,
                    "GITHUB_TOKEN=" + "fixture-value\n",
                    "https://alice:URLSECRET123456@github.com/acme/private.git\n",
                ),
            ):
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(payload["projects"][0]["stdout"], "GITHUB_TOKEN=" + "[REDACTED]\n")
        self.assertEqual(payload["projects"][0]["stderr"], "https://[REDACTED]@github.com/acme/private.git\n")
        self.assertNotIn("SECRET", stdout)
        self.assertNotIn("SECRET", stderr)

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

            with mock.patch("base_projects.workspace_test.run_workspace_subprocess", side_effect=results):
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(payload["counts"], {"passed": 2, "failed": 1, "blocked": 0, "not_run": 0, "skipped": 0})
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
                "base_projects.workspace_test.run_workspace_subprocess",
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
        self.assertEqual(payload["counts"], {"passed": 0, "failed": 1, "blocked": 0, "not_run": 2, "skipped": 0})
        self.assertEqual(payload["projects"][1]["status"], "not_run")
        self.assertIn("execution was stopped", payload["projects"][1]["detail"])
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
                "base_projects.workspace_test.run_workspace_subprocess",
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
                "base_projects.workspace_test.run_workspace_subprocess",
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
        self.assertEqual(payload["counts"], {"passed": 1, "failed": 0, "blocked": 0, "not_run": 0, "skipped": 1})
        self.assertEqual(payload["projects"][1]["status"], "skipped")
        self.assertIn("does not declare a test command", payload["projects"][1]["detail"])

    def test_workspace_test_preflights_all_projects_before_running_any_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("trusted", "blocked"))
            write_test_manifest(workspace / "trusted", "trusted")
            write_test_manifest(workspace / "blocked", "blocked")

            with mock.patch(
                "base_projects.workspace_test.run_workspace_subprocess",
                return_value=subprocess.CompletedProcess([], 0, "should not run\n", ""),
            ) as run:
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                    trusted_projects=("trusted",),
                )
                payload = json.loads(stdout)
                self.assertEqual(status, 1)
                self.assertEqual(stderr, "")
                self.assertEqual(run.call_count, 0)
                self.assertEqual(payload["preflight"], "blocked")
                self.assertFalse(payload["execution_started"])
                self.assertEqual(
                    payload["counts"],
                    {"passed": 0, "failed": 0, "blocked": 1, "not_run": 1, "skipped": 0},
                )
                self.assertEqual(
                    [project["status"] for project in payload["projects"]], ["not_run", "blocked"]
                )

                manifest.write_text(
                    "\n".join(
                        [
                            "schema_version: 1",
                            "workspace:",
                            "  name: test-workspace",
                            "repos:",
                            "  - name: blocked",
                            "  - name: trusted",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )
                run.reset_mock()
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest), "--format", "json"],
                    base_home,
                    home,
                    trusted_projects=("trusted",),
                )
                payload = json.loads(stdout)
                self.assertEqual(status, 1)
                self.assertEqual(stderr, "")
                self.assertEqual(run.call_count, 0)
                self.assertEqual(
                    [project["status"] for project in payload["projects"]], ["blocked", "not_run"]
                )

    def test_workspace_test_dry_run_reports_plan_without_running_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home)
            write_workspace_manifest(manifest, ("alpha",))
            write_test_manifest(workspace / "alpha", "alpha")

            with mock.patch("base_projects.workspace_test.run_workspace_subprocess") as run:
                status, stdout, stderr = invoke_workspace_test(
                    [
                        "test",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest),
                        "--dry-run",
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertFalse(run.called)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["execution_started"])
        self.assertEqual(payload["projects"][0]["status"], "not_run")

    def test_workspace_test_dry_run_fails_for_required_missing_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_workspace_manifest(manifest, ("missing",))

            status, stdout, stderr = invoke_workspace_test(
                [
                    "test",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest),
                    "--dry-run",
                    "--format",
                    "json",
                ],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["counts"], {"passed": 0, "failed": 1, "blocked": 0, "not_run": 0, "skipped": 0})
        self.assertEqual(payload["projects"][0]["status"], "failed")
        self.assertIn("repository is missing", payload["projects"][0]["detail"])
        self.assertFalse(payload["execution_started"])

    def test_workspace_test_text_reports_start_and_completion_progress(self) -> None:
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
                "base_projects.workspace_test.run_workspace_subprocess",
                side_effect=[
                    subprocess.CompletedProcess([], 0, "alpha tests\n", ""),
                    subprocess.CompletedProcess([], 0, "beta tests\n", ""),
                ],
            ):
                status, stdout, stderr = invoke_workspace_test(
                    ["test", "--workspace", str(workspace), "--manifest", str(manifest)],
                    base_home,
                    home,
                )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Workspace test preflight: 2 selected projects.", stdout)
        self.assertIn("[1/2] START project 'alpha' (trust=allowed)", stdout)
        self.assertIn("[2/2] START project 'beta' (trust=allowed)", stdout)
        self.assertIn("PASS project 'alpha'", stdout)
        self.assertIn("PASS project 'beta'", stdout)
        self.assertIn("Workspace test completed:", stdout)
        self.assertIn("execution_started=yes", stdout)
