from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        """\
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: api
    url: git@github.com:codeforester/api.git
  - name: docs
""",
        encoding="utf-8",
    )


def write_fake_basectl(base_home: Path, state_file: Path) -> None:
    basectl = base_home / "bin" / "basectl"
    basectl.parent.mkdir(parents=True)
    basectl.write_text(
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> {state_file}
repo="${{3:-}}"
path=""
dry_run=0
while (($#)); do
    case "$1" in
        --path)
            path="$2"
            shift 2
            ;;
        --dry-run)
            dry_run=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done
if [[ "$repo" == "codeforester/base-workspace" && -n "$path" && "$dry_run" != "1" ]]; then
    mkdir -p "$path"
    cat > "$path/workspace.yaml" <<'YAML'
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: api
    url: git@github.com:codeforester/api.git
  - name: docs
YAML
fi
printf 'fake basectl %s\\n' "$*"
""",
        encoding="utf-8",
    )
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
        "BASE_PROJECT_MANIFEST": "",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class WorkspaceInitTests(unittest.TestCase):
    def test_workspace_init_dry_run_uses_local_source_without_writing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            source = root / "base-workspace"
            state_file = root / "basectl-calls"
            config_path = home / ".base.d" / "config.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            source.mkdir()
            write_workspace_manifest(source / "workspace.yaml")
            write_fake_basectl(base_home, state_file)

            status, stdout, stderr = invoke_engine(
                [
                    "init",
                    str(source),
                    "--path",
                    str(source),
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                ],
                base_home,
                home,
            )

            state_lines = state_file.read_text(encoding="utf-8").splitlines() if state_file.exists() else []
            config_exists = config_path.exists()

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertFalse(config_exists)
        self.assertIn("Workspace init", stdout)
        self.assertIn(f"Workspace source: {source}", stdout)
        self.assertIn(f"Workspace config repo: {source.resolve()}", stdout)
        self.assertIn(f"Workspace root: {workspace.resolve()}", stdout)
        self.assertIn(f"Workspace manifest: {(source / 'workspace.yaml').resolve()} (demo-suite)", stdout)
        self.assertIn("[DRY-RUN] Would update user config:", stdout)
        self.assertEqual(
            state_lines,
            [
                f"repo clone codeforester/api --path {(workspace / 'api').resolve()} --dry-run",
                f"repo clone docs --path {(workspace / 'docs').resolve()} --dry-run",
            ],
        )

    def test_workspace_init_writes_config_and_clones_repositories_under_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            source = workspace / "base-workspace"
            state_file = root / "basectl-calls"
            config_path = home / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "github:\n"
                "  default_owner: codeforester\n"
                "  clone_protocol: https\n",
                encoding="utf-8",
            )
            base_home.mkdir()
            workspace.mkdir()
            source.mkdir()
            write_workspace_manifest(source / "workspace.yaml")
            write_fake_basectl(base_home, state_file)

            status, stdout, stderr = invoke_engine(
                [
                    "init",
                    str(source),
                    "--path",
                    str(source),
                ],
                base_home,
                home,
            )
            config_content = config_path.read_text(encoding="utf-8")
            state_lines = state_file.read_text(encoding="utf-8").splitlines() if state_file.exists() else []

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace root: {workspace.resolve()}", stdout)
        self.assertIn(f"Updated user config: {config_path}", stdout)
        self.assertIn("github:", config_content)
        self.assertIn("default_owner: codeforester", config_content)
        self.assertIn("clone_protocol: https", config_content)
        self.assertIn("workspace:", config_content)
        self.assertIn(f"root: {workspace.resolve()}", config_content)
        self.assertIn(f"manifest: {(source / 'workspace.yaml').resolve()}", config_content)
        self.assertEqual(
            state_lines,
            [
                f"repo clone codeforester/api --path {(workspace / 'api').resolve()}",
                f"repo clone docs --path {(workspace / 'docs').resolve()}",
            ],
        )

    def test_workspace_init_clones_short_workspace_source_with_owner_before_reading_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            source = workspace / "base-workspace"
            state_file = root / "basectl-calls"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_fake_basectl(base_home, state_file)

            status, stdout, stderr = invoke_engine(
                [
                    "init",
                    "base-workspace",
                    "--owner",
                    "codeforester",
                    "--path",
                    str(source),
                    "--workspace",
                    str(workspace),
                ],
                base_home,
                home,
            )
            state_lines = state_file.read_text(encoding="utf-8").splitlines() if state_file.exists() else []

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Workspace source: codeforester/base-workspace", stdout)
        self.assertIn(f"Workspace manifest: {(source / 'workspace.yaml').resolve()} (demo-suite)", stdout)
        self.assertEqual(
            state_lines,
            [
                f"repo clone codeforester/base-workspace --path {source.resolve()}",
                f"repo clone codeforester/api --path {(workspace / 'api').resolve()}",
                f"repo clone docs --path {(workspace / 'docs').resolve()}",
            ],
        )

    def test_workspace_init_remote_dry_run_without_local_manifest_stops_after_config_repo_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            source = workspace / "base-workspace"
            state_file = root / "basectl-calls"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_fake_basectl(base_home, state_file)

            status, stdout, stderr = invoke_engine(
                [
                    "init",
                    "base-workspace",
                    "--owner",
                    "codeforester",
                    "--path",
                    str(source),
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                ],
                base_home,
                home,
            )
            state_lines = state_file.read_text(encoding="utf-8").splitlines()

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Workspace init", stdout)
        self.assertIn("Workspace source: codeforester/base-workspace", stdout)
        self.assertIn(f"Workspace config repo: {source.resolve()}", stdout)
        self.assertIn(f"Workspace root: {workspace.resolve()}", stdout)
        self.assertIn(f"[DRY-RUN] Would read workspace manifest: {(source / 'workspace.yaml').resolve()}", stdout)
        self.assertIn(
            "[DRY-RUN] Skipping member repository plan because the workspace config repo is not present.",
            stdout,
        )
        self.assertEqual(
            state_lines,
            [f"repo clone codeforester/base-workspace --path {source.resolve()} --dry-run"],
        )
