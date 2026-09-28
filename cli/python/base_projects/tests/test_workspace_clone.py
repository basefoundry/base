from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_projects.tests.workspace_cli_helpers import invoke_engine
from base_projects.workspace_clone_command import clone_detail


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
    printf '2026-09-03 23:29:23 +0530 ERROR   subcommands/repo.sh:2179 Failed to clone repository.\\n' >&2
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


def workspace_clone_row(stdout: str, repo_name: str) -> list[str]:
    line = next(line for line in stdout.splitlines() if line.startswith(repo_name))
    return line.split()


class WorkspaceCloneTests(unittest.TestCase):
    def test_empty_workspace_clone_plan_is_a_successful_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            workspace.mkdir()
            base_home.mkdir()
            write_workspace_manifest(
                manifest_path,
                "schema_version: 1\nworkspace:\n  name: empty\nrepos: []\n",
            )

            status, stdout, stderr = invoke_engine(
                ["clone", "--workspace", str(workspace), "--manifest", str(manifest_path), "--dry-run"],
                base_home,
                home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Workspace clone: ", stdout)
        self.assertIn("(0 manifest repos)", stdout)
        self.assertIn("Workspace clone plan complete: planned=0 skipped=0 failed=0.", stdout)

    def test_clone_detail_filters_timestamped_base_log_records(self) -> None:
        detail = clone_detail(
            "Cloning GitHub repository 'codeforester/bleach'.\n",
            "\n".join(
                (
                    "HTTP 401: Bad credentials (https://api.github.com/graphql)",
                    "Try authenticating with: gh auth refresh -h github.com",
                    "2026-09-03 23:29:23 +0530 ERROR   subcommands/repo.sh:2179 Failed to clone repository.",
                    "2026-06-10 10:15:33 WARN    repo.sh:100 retrying",
                )
            ),
        )

        self.assertEqual(
            detail,
            "\n".join(
                (
                    "HTTP 401: Bad credentials (https://api.github.com/graphql)",
                    "Try authenticating with: gh auth refresh -h github.com",
                    "Cloning GitHub repository 'codeforester/bleach'.",
                )
            ),
        )

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
            self.assertIn(f"Workspace clone: {workspace.resolve()} (4 manifest repos)", stdout)
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertIn("REPOSITORY     ACTION  RESULT", stdout)
            self.assertIn("base           CHECK   planned", stdout)
            self.assertIn("api            CLONE   planned", stdout)
            self.assertIn("docs           CLONE   planned", stdout)
            self.assertIn("optional-tool  SKIP    skipped", stdout)
            self.assertIn("pass --include-optional to clone it", stdout)
            self.assertIn("Workspace clone plan complete: planned=3 skipped=1 failed=0.", stdout)
            self.assertIn("[DRY-RUN] No repositories were modified.", stdout)
            self.assertNotIn("fake basectl", stdout)
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
            (workspace / "api").mkdir()
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
            self.assertEqual(stderr, "")
            self.assertEqual(
                workspace_clone_row(stdout, "conflict"),
                ["conflict", "CLONE", "failed", "(exit", "1)"],
            )
            self.assertIn("simulated clone conflict for codeforester/conflict", stdout)
            self.assertNotIn("subcommands/repo.sh:2179", stdout)
            self.assertEqual(workspace_clone_row(stdout, "api"), ["api", "CHECK", "present"])
            self.assertEqual(
                workspace_clone_row(stdout, "optional-tool"),
                ["optional-tool", "CLONE", "cloned"],
            )
            self.assertIn("Workspace clone completed: present=1 cloned=1 skipped=0 failed=1.", stdout)
            self.assertNotIn("fake basectl", stdout)
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

    def test_workspace_clone_uses_configured_manifest_when_flag_is_omitted(self) -> None:
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
  - name: api
    url: https://github.com/codeforester/api.git
""",
            )

            status, stdout, stderr = invoke_engine(
                ["clone", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
                user_config=f"workspace:\n  manifest: {manifest_path}\n",
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertEqual(workspace_clone_row(stdout, "api"), ["api", "CLONE", "planned"])
            self.assertIn("Workspace clone plan complete: planned=1 skipped=0 failed=0.", stdout)
            self.assertEqual(
                state_file.read_text(encoding="utf-8").splitlines(),
                [f"repo clone codeforester/api --path {(workspace / 'api').resolve()} --dry-run"],
            )

    def test_workspace_clone_rejects_repository_target_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            outside = root / "outside"
            base_home = root / "base"
            state_file = root / "basectl-calls"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            workspace.mkdir()
            outside.mkdir()
            base_home.mkdir()
            (workspace / "api").symlink_to(outside, target_is_directory=True)
            write_fake_basectl(base_home, state_file)
            write_workspace_manifest(
                manifest_path,
                """
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: api
    url: https://github.com/codeforester/api.git
""",
            )

            status, stdout, stderr = invoke_engine(
                ["clone", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(workspace_clone_row(stdout, "api"), ["api", "CLONE", "failed"])
        self.assertIn("resolves outside workspace root", stdout)
        self.assertIn("Workspace clone completed: present=0 cloned=0 skipped=0 failed=1.", stdout)
        self.assertFalse(state_file.exists())

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
