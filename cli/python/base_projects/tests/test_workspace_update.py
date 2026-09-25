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


def git_probe(stdout: str = "", returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout=stdout, stderr=stderr)


class WorkspaceUpdateRemoteDefaultBranchTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    def test_workspace_update_preflight_allows_clean_default_branch_tracking(self) -> None:
        target = workspace_update.WorkspaceUpdateTarget(
            name="demo",
            root=Path("/workspace/demo"),
            action="pull",
        )
        with mock.patch(
            "base_projects.workspace_update.run_workspace_git_probe",
            side_effect=(
                git_probe(".git\n.git\n"),
                git_probe("## main...origin/main\n"),
                git_probe("ref: refs/heads/main\tHEAD\n"),
            ),
        ):
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNone(result)

    def test_workspace_update_preflight_reads_remote_default_branch_without_local_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            origin = root / "origin.git"
            repository = root / "repository"
            subprocess.run(
                ["git", "init", "--bare", "--initial-branch=main", str(origin)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "init", "--initial-branch=main", str(repository)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repository), "config", "user.name", "Workspace Test"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repository), "config", "user.email", "workspace-test@example.com"],
                check=True,
            )
            (repository / "README.md").write_text("workspace test\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
            subprocess.run(
                ["git", "-C", str(repository), "commit", "-m", "initial"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repository), "remote", "add", "origin", str(origin)],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repository), "push", "--set-upstream", "origin", "main"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repository), "update-ref", "-d", "refs/remotes/origin/HEAD"],
                check=False,
                capture_output=True,
            )
            local_head = subprocess.run(
                ["git", "-C", str(repository), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(local_head.returncode, 0)

            target = workspace_update.WorkspaceUpdateTarget(
                name="demo",
                root=repository,
                action="pull",
            )
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNone(result)

    def test_parse_workspace_remote_default_branch_rejects_ambiguous_or_incomplete_responses(self) -> None:
        cases = (
            ("", None),
            ("deadbeef\tHEAD\n", None),
            ("refs/heads/main\tHEAD\n", None),
            ("ref: refs/heads/\tHEAD\n", None),
            ("ref: refs/heads/main\tHEAD\nref: refs/heads/develop\tHEAD\n", None),
            ("ref: refs/heads/main\tHEAD\n0123456789abcdef\tHEAD\n", "main"),
        )
        for output, expected in cases:
            with self.subTest(output=output):
                self.assertEqual(workspace_update.parse_workspace_remote_default_branch(output), expected)

    def test_workspace_update_preflight_rejects_configured_upstream_branch_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = workspace_update.WorkspaceUpdateTarget(
                name="demo",
                root=root,
                action="pull",
                default_branch="main",
            )
            with mock.patch(
                "base_projects.workspace_update.run_workspace_git_probe",
                side_effect=(
                    git_probe(".git\n.git\n"),
                    git_probe("## main...origin/feature/with/slash\n"),
                    git_probe("refs/heads/feature/with/slash\n"),
                ),
            ):
                result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNotNone(result)
        self.assertEqual(result.preflight, ("upstream_mismatch",))
        self.assertIn("not the configured default branch 'main'", result.detail or "")

    def test_workspace_update_real_git_fixture_preserves_head_for_mismatched_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            remote = root / "origin.git"
            seed = root / "seed"
            checkout = root / "checkout"
            subprocess.run(
                ["git", "init", "--bare", "--initial-branch=main", str(remote)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "init", "--initial-branch=main", str(seed)],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "-C", str(seed), "config", "user.name", "Workspace Test"], check=True)
            subprocess.run(["git", "-C", str(seed), "config", "user.email", "workspace@example.com"], check=True)
            (seed / "README.md").write_text("main\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(seed), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(seed), "commit", "-m", "main"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(seed), "remote", "add", "origin", str(remote)], check=True)
            subprocess.run(
                ["git", "-C", str(seed), "push", "--set-upstream", "origin", "main"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(seed), "switch", "-c", "feature/with/slash"],
                check=True,
                capture_output=True,
            )
            (seed / "feature.txt").write_text("feature\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(seed), "add", "feature.txt"], check=True)
            subprocess.run(["git", "-C", str(seed), "commit", "-m", "feature"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(seed), "push", "--set-upstream", "origin", "feature/with/slash"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "clone", "--branch", "main", str(remote), str(checkout)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(checkout),
                    "branch",
                    "--set-upstream-to=origin/feature/with/slash",
                    "main",
                ],
                check=True,
                capture_output=True,
            )
            before = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()

            result = workspace_update.preflight_workspace_update_target(
                workspace_update.WorkspaceUpdateTarget(
                    "demo", checkout, "pull", default_branch="main"
                )
            )

            after = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()

        self.assertIsNotNone(result)
        self.assertEqual(result.preflight, ("upstream_mismatch",))
        self.assertEqual(before, after)


class WorkspaceUpdateTests(unittest.TestCase):
    def test_workspace_update_debug_log_formats_captured_output(self) -> None:
        cases = (
            (
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
                "Git pull for repository 'demo' exited with 0; stdout=Already up to date.",
            ),
            (
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Updating abc..def\nFast-forward\n",
                    stderr="",
                ),
                "Git pull for repository 'demo' exited with 0; stdout=Updating abc..def Fast-forward",
            ),
            (
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    1,
                    stdout="",
                    stderr="fatal: Not possible to fast-forward, aborting.\n",
                ),
                "Git pull for repository 'demo' exited with 1; stderr=fatal: Not possible to fast-forward, aborting.",
            ),
        )

        for result, expected in cases:
            with self.subTest(result=result):
                ctx = mock.Mock()
                target = workspace_update.WorkspaceUpdateTarget(
                    name="demo",
                    root=Path("/workspace/demo"),
                    action="pull",
                )
                with mock.patch("base_projects.workspace_update.subprocess.run", return_value=result):
                    workspace_update.execute_workspace_update_target(ctx, target)

                message, *arguments = ctx.log.debug.call_args.args
                self.assertEqual(message % tuple(arguments), expected)

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

            with mock.patch("base_projects.workspace_update.preflight_workspace_update_target", return_value=None):
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

    def test_workspace_update_preflight_reports_dirty_root(self) -> None:
        target = workspace_update.WorkspaceUpdateTarget(
            name="demo",
            root=Path("/workspace/demo"),
            action="pull",
            default_branch="main",
        )
        with mock.patch(
            "base_projects.workspace_update.run_workspace_git_probe",
            side_effect=(
                git_probe(".git\n.git\n"),
                git_probe("## main...origin/main\n M README.md\n"),
            ),
        ):
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.preflight, ("dirty",))
        self.assertIn("working tree is dirty", result.detail or "")
        self.assertIn("/workspace/demo", result.detail or "")
        self.assertIn("will not stash or reset", result.detail or "")

    def test_workspace_update_preflight_reports_non_default_branch(self) -> None:
        target = workspace_update.WorkspaceUpdateTarget(
            name="demo",
            root=Path("/workspace/demo"),
            action="pull",
            default_branch="main",
        )
        with mock.patch(
            "base_projects.workspace_update.run_workspace_git_probe",
            side_effect=(
                git_probe(".git\n.git\n"),
                git_probe("## pr-33-review...origin/pr-33-review\n"),
            ),
        ):
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.preflight, ("non_default_branch",))
        self.assertIn("pr-33-review", result.detail or "")
        self.assertIn("expected default branch 'main'", result.detail or "")

    def test_workspace_update_preflight_reports_missing_upstream(self) -> None:
        target = workspace_update.WorkspaceUpdateTarget(
            name="demo",
            root=Path("/workspace/demo"),
            action="pull",
            default_branch="main",
        )
        with mock.patch(
            "base_projects.workspace_update.run_workspace_git_probe",
            side_effect=(
                git_probe(".git\n.git\n"),
                git_probe("## main\n"),
            ),
        ):
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.preflight, ("missing_upstream",))
        self.assertIn("branch 'main' has no upstream tracking branch", result.detail or "")

    def test_workspace_update_preflight_reports_linked_worktree_without_status_probe(self) -> None:
        target = workspace_update.WorkspaceUpdateTarget(
            name="demo",
            root=Path("/workspace/demo"),
            action="pull",
            default_branch="main",
        )
        with mock.patch(
            "base_projects.workspace_update.run_workspace_git_probe",
            return_value=git_probe(".git/worktrees/pr-33\n.git\n"),
        ) as probe:
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.preflight, ("linked_worktree",))
        self.assertIn("linked Git worktree", result.detail or "")
        self.assertIn("will not pull this PR worktree", result.detail or "")
        probe.assert_called_once()

    def test_workspace_update_preflight_detects_actual_linked_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            primary = root / "primary"
            linked = root / "linked"
            primary.mkdir()
            subprocess.run(["git", "init", "--initial-branch=main", str(primary)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(primary), "config", "user.name", "Workspace Test"], check=True)
            subprocess.run(
                ["git", "-C", str(primary), "config", "user.email", "workspace-test@example.com"],
                check=True,
            )
            (primary / "README.md").write_text("workspace test\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(primary), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(primary), "commit", "-m", "initial"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(primary), "worktree", "add", "-b", "pr-33-review", str(linked), "HEAD"],
                check=True,
                capture_output=True,
            )

            target = workspace_update.WorkspaceUpdateTarget(
                name="demo",
                root=linked,
                action="pull",
                default_branch="main",
            )
            result = workspace_update.preflight_workspace_update_target(target)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.preflight, ("linked_worktree",))
        self.assertIn("linked Git worktree", result.detail or "")

    def test_workspace_update_reports_preflight_diagnostics_in_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            (root / "demo").mkdir()
            manifest_path.write_text(
                "schema_version: 1\nworkspace:\n  name: demo-suite\nrepos:\n  - name: demo\n",
                encoding="utf-8",
            )
            preflight = workspace_update.WorkspaceUpdateResult(
                "skipped",
                detail=f"repository 'demo' at '{root / 'demo'}' is not safe to update:\nworking tree is dirty.",
                preflight=("dirty",),
            )

            with mock.patch(
                "base_projects.workspace_update.preflight_workspace_update_target",
                return_value=preflight,
            ):
                with mock.patch("base_projects.workspace_update.subprocess.run") as run:
                    status, stdout, stderr = invoke_engine(
                        [
                            "update",
                            "--workspace",
                            str(root),
                            "--manifest",
                            str(manifest_path),
                        ],
                        base_home,
                        home,
                    )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        assert_workspace_result(self, stdout, "demo", "SKIP", "skipped")
        self.assertIn("working tree is dirty", stdout)
        self.assertIn("Workspace update completed: updated=0 unchanged=0 skipped=1 failed=1.", stdout)
        run.assert_not_called()

    def test_workspace_update_json_reports_preflight_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            (root / "demo").mkdir()
            manifest_path.write_text(
                "schema_version: 1\nworkspace:\n  name: demo-suite\nrepos:\n  - name: demo\n",
                encoding="utf-8",
            )
            preflight = workspace_update.WorkspaceUpdateResult(
                "skipped",
                detail=f"repository 'demo' at '{root / 'demo'}' is a linked Git worktree.",
                preflight=("linked_worktree",),
            )

            with mock.patch(
                "base_projects.workspace_update.preflight_workspace_update_target",
                return_value=preflight,
            ):
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["repositories"][0]["action"], "skip")
        self.assertEqual(payload["repositories"][0]["status"], "skipped")
        self.assertTrue(payload["repositories"][0]["fatal"])
        self.assertEqual(payload["repositories"][0]["preflight"], ["linked_worktree"])
        self.assertEqual(payload["counts"], {"planned": 0, "updated": 0, "unchanged": 0, "skipped": 1, "failed": 1})

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
            with mock.patch("base_projects.workspace_update.preflight_workspace_update_target", return_value=None):
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
            with mock.patch("base_projects.workspace_update.preflight_workspace_update_target", return_value=None):
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

            with mock.patch("base_projects.workspace_update.preflight_workspace_update_target", return_value=None):
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
            with mock.patch("base_projects.workspace_update.preflight_workspace_update_target", return_value=None):
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

    def test_workspace_update_optional_preflight_skip_is_nonfatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            (root / "scratch").mkdir()
            manifest_path.write_text(
                "schema_version: 1\nworkspace:\n  name: demo-suite\n"
                "repos:\n  - name: scratch\n    required: false\n",
                encoding="utf-8",
            )
            preflight = workspace_update.WorkspaceUpdateResult(
                "skipped",
                detail="repository scratch is dirty",
                preflight=("dirty",),
            )

            with mock.patch(
                "base_projects.workspace_update.preflight_workspace_update_target",
                return_value=preflight,
            ):
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                    ],
                    base_home,
                    home,
                )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Workspace update completed: updated=0 unchanged=0 skipped=1 failed=0.", stdout)

    def test_workspace_update_dry_run_reports_preflight_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            (root / "demo").mkdir()
            manifest_path.write_text(
                "schema_version: 1\nworkspace:\n  name: demo-suite\nrepos:\n  - name: demo\n",
                encoding="utf-8",
            )
            preflight = workspace_update.WorkspaceUpdateResult(
                "skipped",
                detail=f"repository 'demo' at '{root / 'demo'}' is not safe to update:\nworking tree is dirty.",
                preflight=("dirty",),
            )

            with mock.patch(
                "base_projects.workspace_update.preflight_workspace_update_target",
                return_value=preflight,
            ):
                with mock.patch("base_projects.workspace_update.subprocess.run") as run:
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
        assert_workspace_result(self, stdout, "demo", "SKIP", "skipped")
        self.assertIn("working tree is dirty", stdout)
        self.assertIn("Workspace update plan complete: planned=0 skipped=1 failed=1.", stdout)
        run.assert_not_called()

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
