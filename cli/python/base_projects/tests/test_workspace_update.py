from __future__ import annotations

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_projects import workspace_update
from base_projects.tests.workspace_cli_helpers import invoke_engine
from base_projects.workspace_manifest import WorkspaceManifestRepo


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: first
  - name: failing
  - name: unchanged
  - name: optional-missing
    required: false
  - name: required-missing
  - name: later
""",
        encoding="utf-8",
    )


class WorkspaceUpdateTests(unittest.TestCase):
    def test_workspace_update_rejects_repository_target_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            outside = root / "outside"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            outside.mkdir()
            (workspace / "api").symlink_to(outside, target_is_directory=True)
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: api
""",
                encoding="utf-8",
            )

            with mock.patch("base_projects.workspace_update.subprocess.run") as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                    ],
                    base_home,
                    home,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn("SKIP    skipped", stdout)
        self.assertIn("resolves outside workspace root", stdout)
        self.assertIn("Workspace update completed: updated=0 unchanged=0 skipped=1 failed=1.", stdout)
        run.assert_not_called()

    def test_workspace_update_allows_repository_symlink_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            repository = workspace / "repository"
            workspace.mkdir()
            repository.mkdir()
            (workspace / "api").symlink_to(repository, target_is_directory=True)

            target = workspace_update.workspace_update_manifest_target(
                workspace,
                WorkspaceManifestRepo(name="api"),
            )

        self.assertEqual(target.root, repository.resolve())
        self.assertEqual(target.action, "pull")
        self.assertFalse(target.fatal)

    def test_workspace_update_dry_run_preserves_order_and_includes_active_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            for name in ("first", "failing", "unchanged", "later"):
                (root / name).mkdir()
            write_workspace_manifest(manifest_path)

            status, stdout, stderr = invoke_engine(
                [
                    "update",
                    "--workspace",
                    str(root),
                    "--manifest",
                    str(manifest_path),
                    "--dry-run",
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace update: {root.resolve()} (7 manifest repos)", stdout)
            self.assertIn("REPOSITORY", stdout)
            assert_workspace_result(self, stdout, "base", "PULL", "planned")
            assert_workspace_result(self, stdout, "first", "PULL", "planned")
            assert_workspace_result(self, stdout, "optional-missing", "SKIP", "skipped")
            assert_workspace_result(self, stdout, "later", "PULL", "planned")
            self.assertNotIn("active Base control plane is managed from BASE_HOME", stdout)
            self.assertIn("Workspace update plan complete: planned=5 skipped=2 failed=1.", stdout)
            self.assertIn("[DRY-RUN] No repositories were modified.", stdout)
            self.assertLess(stdout.index("\nbase "), stdout.index("\nfirst "))
            self.assertLess(stdout.index("\nfirst "), stdout.index("\nlater "))

    def test_workspace_update_pulls_serially_and_aggregates_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = workspace / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            workspace.mkdir()
            base_home.mkdir()
            for name in ("first", "failing", "unchanged", "later"):
                (workspace / name).mkdir()
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: first
  - name: failing
  - name: unchanged
  - name: optional-missing
    required: false
  - name: later
""",
                encoding="utf-8",
            )

            results = [
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Updating abc..def\nFast-forward\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    1,
                    stdout="",
                    stderr="fatal: Not possible to fast-forward, aborting.\n",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Updating ghi..jkl\nFast-forward\n",
                    stderr="",
                ),
            ]
            with mock.patch("base_projects.workspace_update.subprocess.run", side_effect=results) as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 1)
            self.assertEqual(stderr, "")
            assert_workspace_result(self, stdout, "base", "PULL", "unchanged")
            assert_workspace_result(self, stdout, "first", "PULL", "updated")
            assert_workspace_result(self, stdout, "failing", "PULL", "failed (exit 1)")
            self.assertIn("fatal: Not possible to fast-forward, aborting.", stdout)
            assert_workspace_result(self, stdout, "later", "PULL", "updated")
            self.assertNotIn("Already up to date.", stdout)
            self.assertIn("Workspace update completed: updated=2 unchanged=2 skipped=1 failed=1.", stdout)
            self.assertEqual(
                [call.kwargs["cwd"] for call in run.call_args_list],
                [
                    workspace.resolve() / "base",
                    workspace.resolve() / "first",
                    workspace.resolve() / "failing",
                    workspace.resolve() / "unchanged",
                    workspace.resolve() / "later",
                ],
            )
            for call in run.call_args_list:
                self.assertEqual(call.args[0], ["git", "pull", "--ff-only"])
                self.assertEqual(call.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
                self.assertEqual(call.kwargs["env"]["LC_ALL"], "C")

    def test_workspace_update_repos_filter_preserves_manifest_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            for name in ("first", "later"):
                (root / name).mkdir()
            write_workspace_manifest(manifest_path)

            results = [
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
            ]
            with mock.patch("base_projects.workspace_update.subprocess.run", side_effect=results) as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--repos",
                        "later,first",
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace update: {root.resolve()} (2 manifest repos)", stdout)
            self.assertNotIn("base ", stdout)
            self.assertLess(stdout.index("\nfirst "), stdout.index("\nlater "))
            self.assertEqual(
                [call.kwargs["cwd"] for call in run.call_args_list],
                [root.resolve() / "first", root.resolve() / "later"],
            )

    def test_workspace_update_repos_filter_rejects_unknown_names_before_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)

            with mock.patch("base_projects.workspace_update.subprocess.run") as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--repos",
                        "first,missing",
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 2)
            self.assertEqual(stdout, "")
            self.assertIn("unknown repository name(s): missing", stderr)
            run.assert_not_called()

    def test_workspace_update_json_dry_run_is_machine_readable_and_does_not_run_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            for name in ("first", "later"):
                (root / name).mkdir()
            write_workspace_manifest(manifest_path)

            with mock.patch("base_projects.workspace_update.subprocess.run") as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--repos",
                        "later,first",
                        "--dry-run",
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            payload = json.loads(stdout)
            self.assertEqual(payload["schema_version"], 1)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["selected_repositories"], ["first", "later"])
            self.assertEqual([repo["status"] for repo in payload["repositories"]], ["planned", "planned"])
            self.assertEqual(payload["counts"], {"planned": 2, "updated": 0, "unchanged": 0, "skipped": 0, "failed": 0})
            run.assert_not_called()

    def test_workspace_update_json_reports_results_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = workspace / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            workspace.mkdir()
            base_home.mkdir()
            for name in ("first", "failing"):
                (workspace / name).mkdir()
            write_workspace_manifest(manifest_path)

            results = [
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Updating abc..def\nFast-forward\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    1,
                    stdout="",
                    stderr="fatal: Not possible to fast-forward, aborting.\n",
                ),
            ]
            with mock.patch("base_projects.workspace_update.subprocess.run", side_effect=results):
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                        "--repos",
                        "first,failing,optional-missing",
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 1)
            self.assertEqual(stderr, "")
            payload = json.loads(stdout)
            self.assertEqual(
                [repo["repository"] for repo in payload["repositories"]],
                ["first", "failing", "optional-missing"],
            )
            self.assertEqual(payload["repositories"][0]["status"], "updated")
            self.assertEqual(payload["repositories"][1]["status"], "failed")
            self.assertEqual(payload["repositories"][1]["exit_code"], 1)
            self.assertIn("Not possible to fast-forward", payload["repositories"][1]["detail"])
            self.assertEqual(payload["repositories"][2]["status"], "skipped")
            self.assertEqual(payload["counts"], {"planned": 0, "updated": 1, "unchanged": 0, "skipped": 1, "failed": 1})

    def test_workspace_update_requires_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()

            status, stdout, stderr = invoke_engine(
                ["update", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stdout, "")
            self.assertIn("requires a configured or explicit workspace manifest", stderr)


def assert_workspace_result(
    test_case: unittest.TestCase,
    output: str,
    repository: str,
    action: str,
    result: str,
) -> None:
    pattern = rf"^{re.escape(repository)}\s+{re.escape(action)}\s+{re.escape(result)}$"
    test_case.assertRegex(output, re.compile(pattern, re.MULTILINE))
