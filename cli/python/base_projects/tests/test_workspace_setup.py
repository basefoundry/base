from __future__ import annotations

import io
import os
import shlex
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_repo_inspection import WorkspaceRepoInspection
from base_projects.workspace_setup import workspace_setup_manifest_target


def write_manifest(project_root: Path, name: str, *, python: bool = False) -> None:
    project_root.mkdir(parents=True)
    python_section = "python:\n  manager: uv\n" if python else ""
    (project_root / "base_manifest.yaml").write_text(
        f"schema_version: 1\nproject:\n  name: {name}\n{python_section}",
        encoding="utf-8",
    )


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: missing
    required: false
  - name: no-manifest
  - name: invalid
    required: false
  - name: shell-only
  - name: python-project
""",
        encoding="utf-8",
    )


class WorkspaceSetupTests(unittest.TestCase):
    def test_workspace_setup_skips_base_manifest_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "base").mkdir()
            (workspace / "base" / "base_manifest.yaml").write_text("not: a valid base manifest", encoding="utf-8")
            repo = WorkspaceManifestRepo(name="base")

            with mock.patch(
                "base_projects.workspace_repo_inspection.read_manifest",
                side_effect=AssertionError("base manifest should not be parsed"),
            ):
                target = workspace_setup_manifest_target(workspace, repo)

        self.assertEqual(target.action, "skip")
        self.assertEqual(target.project_name, "base")
        self.assertEqual(target.reason, "active Base control plane is managed from BASE_HOME")

    def test_workspace_setup_fails_closed_when_inspected_manifest_is_missing(self) -> None:
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

        with mock.patch("base_projects.workspace_setup.inspect_workspace_repo", return_value=inspection):
            target = workspace_setup_manifest_target(root.parent, WorkspaceManifestRepo(name="api"))

        self.assertEqual(target.action, "skip")
        self.assertEqual(target.reason, "workspace repository inspection did not return a parsed manifest")
        self.assertTrue(target.fatal)

    def test_workspace_setup_rejects_repository_target_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            outside = root / "outside"
            manifest_path = root / "workspace.yaml"
            state_path = root / "basectl-calls"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            outside.mkdir()
            (workspace / "api").symlink_to(outside, target_is_directory=True)
            write_fake_basectl(base_home, state_path)
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: api
""",
                encoding="utf-8",
            )

            with mock.patch("base_projects.workspace_setup.subprocess.run") as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "setup",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                        "--yes",
                    ],
                    base_home,
                    home,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn("SKIP repository 'api'", stdout)
        self.assertIn("resolves outside workspace root", stdout)
        self.assertIn("Workspace setup completed: setup=0 skipped=1 failed=1.", stdout)
        self.assertFalse(state_path.exists())
        run.assert_not_called()

    def test_workspace_setup_dry_run_preserves_manifest_order_and_classifies_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_manifest(workspace / "base", "base")
            (workspace / "no-manifest").mkdir()
            (workspace / "invalid").mkdir()
            (workspace / "invalid" / "base_manifest.yaml").write_text(
                "schema_version: 1\nproject: invalid\n",
                encoding="utf-8",
            )
            write_manifest(workspace / "shell-only", "shell-only")
            write_manifest(workspace / "python-project", "python-project", python=True)
            write_workspace_manifest(manifest_path)

            status, stdout, stderr = invoke_engine(
                [
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--dry-run",
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace setup plan: {workspace.resolve()} (6 manifest repos)", stdout)
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertIn("SKIP repository 'base'", stdout)
            self.assertIn("active Base control plane is managed from BASE_HOME", stdout)
            self.assertIn("SKIP repository 'missing'", stdout)
            self.assertIn("repository is missing", stdout)
            self.assertIn("SKIP repository 'no-manifest'", stdout)
            self.assertIn("does not contain base_manifest.yaml", stdout)
            self.assertIn("SKIP repository 'invalid'", stdout)
            self.assertIn("base_manifest.yaml is invalid", stdout)
            self.assertIn("SETUP repository 'shell-only'", stdout)
            self.assertIn("SETUP repository 'python-project'", stdout)
            self.assertIn("Workspace setup plan complete: setup=2 skipped=4 failed=0.", stdout)
            self.assertIn("[DRY-RUN] No repositories were modified.", stdout)
            self.assertLess(stdout.index("repository 'base'"), stdout.index("repository 'missing'"))
            self.assertLess(stdout.index("repository 'missing'"), stdout.index("repository 'no-manifest'"))
            self.assertLess(stdout.index("repository 'no-manifest'"), stdout.index("repository 'invalid'"))
            self.assertLess(stdout.index("repository 'invalid'"), stdout.index("repository 'shell-only'"))
            self.assertLess(stdout.index("repository 'shell-only'"), stdout.index("repository 'python-project'"))
            self.assertFalse((workspace / "shell-only" / ".venv").exists())
            self.assertFalse((workspace / "python-project" / ".venv").exists())

    def test_workspace_setup_requires_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()

            status, stdout, stderr = invoke_engine(
                ["setup", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stdout, "")
            self.assertIn("requires a configured or explicit workspace manifest", stderr)

    def test_workspace_setup_executes_serially_and_aggregates_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest_path = root / "workspace.yaml"
            state_path = root / "basectl-state.txt"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_manifest(workspace / "base", "base")
            write_manifest(workspace / "first", "first")
            write_manifest(workspace / "failing", "failing")
            write_manifest(workspace / "later", "later")
            (workspace / "no-manifest").mkdir()
            write_fake_basectl(base_home, state_path, failing_project="failing")
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: first
  - name: failing
  - name: missing
    required: false
  - name: later
  - name: no-manifest
    required: false
""",
                encoding="utf-8",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--yes",
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertIn("SETUP repository 'first'", stdout)
            self.assertIn("SETUP repository 'failing'", stdout)
            self.assertIn("SETUP repository 'later'", stdout)
            self.assertIn("fake setup first", stdout)
            self.assertIn("fake setup later", stdout)
            self.assertIn("simulated setup failure for failing", stderr)
            self.assertIn("Setup failed for repository 'failing'.", stderr)
            self.assertIn("Workspace setup completed: setup=2 skipped=3 failed=1.", stdout)

            records = state_path.read_text(encoding="utf-8").splitlines()
            resolved_workspace = workspace.resolve()
            resolved_base_home = base_home.resolve()
            self.assertEqual(
                records,
                [
                    f"setup --manifest {resolved_workspace / 'first' / 'base_manifest.yaml'} --yes first\t"
                    f"{resolved_workspace / 'first'}\t{resolved_base_home}\t\t\t\t",
                    f"setup --manifest {resolved_workspace / 'failing' / 'base_manifest.yaml'} --yes failing\t"
                    f"{resolved_workspace / 'failing'}\t{resolved_base_home}\t\t\t\t",
                    f"setup --manifest {resolved_workspace / 'later' / 'base_manifest.yaml'} --yes later\t"
                    f"{resolved_workspace / 'later'}\t{resolved_base_home}\t\t\t\t",
                ],
            )

    def test_workspace_setup_fails_for_missing_required_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest_path = root / "workspace.yaml"
            state_path = root / "basectl-state.txt"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            (workspace / "invalid").mkdir()
            (workspace / "invalid" / "base_manifest.yaml").write_text(
                "schema_version: 1\nproject: invalid\n",
                encoding="utf-8",
            )
            write_fake_basectl(base_home, state_path)
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: missing
  - name: invalid
""",
                encoding="utf-8",
            )

            status, stdout, _ = invoke_engine(
                [
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertIn("repository is missing", stdout)
            self.assertIn("base_manifest.yaml is invalid", stdout)
            self.assertIn("Workspace setup completed: setup=0 skipped=2 failed=2.", stdout)
            self.assertFalse(state_path.exists())

    def test_workspace_setup_aggregates_timeout_as_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_manifest(workspace / "project", "project")
            write_fake_basectl(base_home, root / "basectl-state.txt")
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: project
""",
                encoding="utf-8",
            )

            with mock.patch(
                "base_projects.workspace_setup.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["basectl", "setup"], 1800),
            ):
                status, stdout, stderr = invoke_engine(
                    [
                        "setup",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 1)
            self.assertIn("Timed out running basectl setup for repository 'project'", stderr)
            self.assertIn("Workspace setup completed: setup=0 skipped=0 failed=1.", stdout)


def write_fake_basectl(
    base_home: Path,
    state_path: Path,
    *,
    failing_project: str | None = None,
) -> None:
    basectl = base_home / "bin" / "basectl"
    basectl.parent.mkdir(parents=True)
    script = """#!/usr/bin/env bash
set -u
project="${@: -1}"
printf '%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "$*" "$PWD" "${BASE_HOME-}" "${BASE_PROJECT-}" "${BASE_PROJECT_ROOT-}" "${BASE_PROJECT_MANIFEST-}" "${BASE_PROJECT_VENV_DIR-}" >> STATE_PATH
""".replace("STATE_PATH", shlex.quote(str(state_path)))
    if failing_project is not None:
        script += (
            f"if [[ \"$project\" == {shlex.quote(failing_project)} ]]; then\n"
            "  printf 'simulated setup failure for %s\\n' \"$project\" >&2\n"
            "  exit 1\n"
            "fi\n"
        )
    script += "printf 'fake setup %s\\n' \"$project\"\n"
    basectl.write_text(script, encoding="utf-8")
    basectl.chmod(0o755)


def invoke_engine(
    args: list[str],
    base_home: Path,
    home: Path,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    env = {
        "HOME": str(home),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_ROOT": "inherited-root",
        "BASE_PROJECT_MANIFEST": "",
        "BASE_PROJECT_VENV_DIR": "inherited-venv",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()
