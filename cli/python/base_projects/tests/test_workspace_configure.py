from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine, workspace_configure


def write_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_workspace_manifest(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def write_git_remote(repo_root: Path, url: str) -> None:
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text(
        f"[remote \"origin\"]\n\turl = {url}\n",
        encoding="utf-8",
    )


def write_fake_basectl(base_home: Path, state_file: Path) -> None:
    basectl = base_home / "bin" / "basectl"
    basectl.parent.mkdir(parents=True)
    basectl.write_text(
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> {state_file}
repo=""
while (($#)); do
    case "$1" in
        --repo)
            repo="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
if [[ "$repo" == "basefoundry/failing" ]]; then
    printf 'simulated configure failure for %s\\n' "$repo" >&2
    exit 1
fi
printf 'fake configure %s\\n' "$repo"
""",
        encoding="utf-8",
    )
    basectl.chmod(0o755)


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


class WorkspaceConfigureTests(unittest.TestCase):
    def test_workspace_configure_dry_run_scans_base_managed_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            state_file = root / "basectl-calls"
            home.mkdir()
            base_home.mkdir()
            write_fake_basectl(base_home, state_file)
            write_manifest(workspace / "base", "base")
            write_git_remote(workspace / "base", "git@github.com:basefoundry/base.git")
            write_manifest(workspace / "local-only", "local-only")
            write_git_remote(workspace / "local-only", "file:///repos/local-only.git")
            (workspace / "notes").mkdir(parents=True)

            status, stdout, stderr = invoke_engine(
                ["configure", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace configure: {workspace.resolve()} (2 discovered project(s))", stdout)
            self.assertIn(
                f"CONFIGURE repository 'base' at '{(workspace / 'base').resolve()}' for 'basefoundry/base'.",
                stdout,
            )
            self.assertIn("SKIP repository 'local-only' has no supported GitHub origin remote.", stdout)
            self.assertIn("[DRY-RUN] No repositories were modified.", stdout)
            self.assertIn("Workspace configure completed: configured=1 skipped=1 failed=0.", stdout)
            self.assertEqual(
                state_file.read_text(encoding="utf-8").splitlines(),
                [
                    f"repo configure {(workspace / 'base').resolve()} --repo basefoundry/base --dry-run",
                ],
            )

    def test_workspace_configure_manifest_continues_after_failures_and_skips_missing_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            state_file = root / "basectl-calls"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_fake_basectl(base_home, state_file)
            write_manifest(workspace / "base", "base")
            write_manifest(workspace / "failing", "failing")
            write_workspace_manifest(
                manifest_path,
                """
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
    url: git@github.com:basefoundry/base.git
  - name: missing
    url: git@github.com:basefoundry/missing.git
  - name: failing
    url: git@github.com:basefoundry/failing.git
""",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "configure",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertIn("simulated configure failure for basefoundry/failing", stderr)
            self.assertIn("Configure failed for repository 'failing'.", stderr)
            self.assertIn(f"Workspace configure: {workspace.resolve()} (3 manifest repos)", stdout)
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertIn(
                f"CONFIGURE repository 'base' at '{(workspace / 'base').resolve()}' for 'basefoundry/base'.",
                stdout,
            )
            self.assertIn(
                f"SKIP repository 'missing' is missing at '{(workspace / 'missing').resolve()}'.",
                stdout,
            )
            self.assertIn("Workspace configure completed: configured=1 skipped=1 failed=1.", stdout)
            self.assertEqual(
                state_file.read_text(encoding="utf-8").splitlines(),
                [
                    f"repo configure {(workspace / 'base').resolve()} --repo basefoundry/base",
                    f"repo configure {(workspace / 'failing').resolve()} --repo basefoundry/failing",
                ],
            )

    def test_workspace_configure_uses_configured_manifest_when_flag_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            state_file = root / "basectl-calls"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_fake_basectl(base_home, state_file)
            write_manifest(workspace / "base", "base")
            write_workspace_manifest(
                manifest_path,
                """
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
    url: https://github.com/basefoundry/base.git
""",
            )

            status, stdout, stderr = invoke_engine(
                ["configure", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
                user_config=f"workspace:\n  manifest: {manifest_path}\n",
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertEqual(
                state_file.read_text(encoding="utf-8").splitlines(),
                [
                    f"repo configure {(workspace / 'base').resolve()} --repo basefoundry/base --dry-run",
                ],
            )

    def test_configure_workspace_repo_passes_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = mock.Mock()
            basectl = root / "base" / "bin" / "basectl"
            target = workspace_configure.WorkspaceConfigureTarget(
                name="base",
                root=root / "base",
                repo_spec="basefoundry/base",
            )
            completed = subprocess.CompletedProcess(
                [str(basectl), "repo", "configure", str(target.root), "--repo", "basefoundry/base"],
                0,
                stdout="configured\n",
                stderr="",
            )

            with mock.patch("base_projects.workspace_configure.subprocess.run", return_value=completed) as run:
                status = workspace_configure.configure_workspace_repo(ctx, basectl, target, dry_run=False)

        self.assertEqual(status, 0)
        self.assertEqual(run.call_args.kwargs["timeout"], workspace_configure.WORKSPACE_CONFIGURE_TIMEOUT_SECONDS)

    def test_configure_workspace_repo_reports_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = mock.Mock()
            basectl = root / "base" / "bin" / "basectl"
            target = workspace_configure.WorkspaceConfigureTarget(
                name="base",
                root=root / "base",
                repo_spec="basefoundry/base",
            )
            command = [str(basectl), "repo", "configure", str(target.root), "--repo", "basefoundry/base"]

            with mock.patch(
                "base_projects.workspace_configure.subprocess.run",
                side_effect=subprocess.TimeoutExpired(command, timeout=120),
            ):
                status = workspace_configure.configure_workspace_repo(ctx, basectl, target, dry_run=False)

        self.assertEqual(status, 1)
        ctx.log.error.assert_called_once()
        self.assertIn("Timed out running basectl repo configure", ctx.log.error.call_args.args[0])

    def test_github_origin_repo_spec_passes_timeout(self) -> None:
        completed = subprocess.CompletedProcess(
            ["git", "-C", "/repo", "config", "--get", "remote.origin.url"],
            0,
            stdout="https://github.com/basefoundry/base.git\n",
            stderr="",
        )

        with mock.patch("base_projects.workspace_configure.subprocess.run", return_value=completed) as run:
            repo_spec = workspace_configure.github_origin_repo_spec(Path("/repo"))

        self.assertEqual(repo_spec, "basefoundry/base")
        self.assertEqual(run.call_args.kwargs["timeout"], workspace_configure.GIT_CONFIG_TIMEOUT_SECONDS)

    def test_github_origin_repo_spec_falls_back_to_config_file_on_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            write_git_remote(repo, "git@github.com:basefoundry/base.git")
            command = ["git", "-C", str(repo), "config", "--get", "remote.origin.url"]

            with mock.patch(
                "base_projects.workspace_configure.subprocess.run",
                side_effect=subprocess.TimeoutExpired(command, timeout=10),
            ):
                repo_spec = workspace_configure.github_origin_repo_spec(repo)

        self.assertEqual(repo_spec, "basefoundry/base")
