from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_workspace_manifest(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


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
if [[ "$repo" == "codeforester/conflict" ]]; then
    printf 'simulated clone conflict for %s\\n' "$repo" >&2
    exit 1
fi
if [[ "$dry_run" != "1" && -n "$path" ]]; then
    mkdir -p "$path"
    printf 'project:\\n  name: %s\\nartifacts: []\\n' "$(basename "$path")" > "$path/base_manifest.yaml"
fi
printf 'fake basectl %s\\n' "$repo"
""",
        encoding="utf-8",
    )
    basectl.chmod(0o755)


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


class WorkspaceCloneTests(unittest.TestCase):
    def test_workspace_clone_dry_run_materializes_missing_required_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            state_file = root / "basectl-calls"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            (workspace / "base").mkdir(parents=True)
            write_fake_basectl(base_home, state_file)
            write_workspace_manifest(
                manifest_path,
                """
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
    url: git@github.com:codeforester/base.git
  - name: api
    url: https://github.com/codeforester/api.git
  - name: docs
  - name: optional-tool
    url: git@github.com:codeforester/optional-tool.git
    required: false
""",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "clone",
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
            self.assertIn(f"Workspace clone: {workspace.resolve()} (4 repositories)", stdout)
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertIn(f"CHECK required repository 'base' at '{(workspace / 'base').resolve()}'.", stdout)
            self.assertIn(f"CLONE required repository 'api' into '{(workspace / 'api').resolve()}'.", stdout)
            self.assertIn(f"CLONE required repository 'docs' into '{(workspace / 'docs').resolve()}'.", stdout)
            self.assertIn("SKIP optional repository 'optional-tool' is missing", stdout)
            self.assertEqual(
                state_file.read_text(encoding="utf-8").splitlines(),
                [
                    f"repo clone codeforester/base --path {(workspace / 'base').resolve()} --dry-run",
                    f"repo clone codeforester/api --path {(workspace / 'api').resolve()} --dry-run",
                    f"repo clone docs --path {(workspace / 'docs').resolve()} --dry-run",
                ],
            )
            self.assertFalse((workspace / "api").exists())

    def test_workspace_clone_include_optional_continues_after_clone_failures(self) -> None:
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
            write_workspace_manifest(
                manifest_path,
                """
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: conflict
    url: git@github.com:codeforester/conflict.git
  - name: api
    url: git@github.com:codeforester/api.git
  - name: optional-tool
    url: git@github.com:codeforester/optional-tool.git
    required: false
""",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "clone",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--include-optional",
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertIn("Clone failed for repository 'conflict'.", stderr)
            self.assertIn("simulated clone conflict for codeforester/conflict", stderr)
            self.assertIn(f"CLONE required repository 'conflict' into '{(workspace / 'conflict').resolve()}'.", stdout)
            self.assertIn(f"CLONE required repository 'api' into '{(workspace / 'api').resolve()}'.", stdout)
            self.assertIn(
                f"CLONE optional repository 'optional-tool' into '{(workspace / 'optional-tool').resolve()}'.",
                stdout,
            )
            self.assertIn("Workspace clone completed with 1 error(s).", stdout)
            self.assertEqual(
                state_file.read_text(encoding="utf-8").splitlines(),
                [
                    f"repo clone codeforester/conflict --path {(workspace / 'conflict').resolve()}",
                    f"repo clone codeforester/api --path {(workspace / 'api').resolve()}",
                    f"repo clone codeforester/optional-tool --path {(workspace / 'optional-tool').resolve()}",
                ],
            )
            self.assertTrue((workspace / "api" / "base_manifest.yaml").is_file())
            self.assertTrue((workspace / "optional-tool" / "base_manifest.yaml").is_file())

    def test_workspace_clone_requires_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()

            status, _stdout, stderr = invoke_engine(
                ["clone", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

        self.assertEqual(status, 2)
        self.assertIn("workspace clone requires --manifest <path>.", stderr)
