from __future__ import annotations

import io
import importlib
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from base_projects import engine, workspace_init as workspace_init_module
from base_projects.command_helpers import ProjectCommandResult
from base_projects.workspace_manifest import WorkspaceManifestError


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
    def test_workspace_init_config_repo_clone_redacts_child_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = SimpleNamespace(application_home=root / "base")
            result = ProjectCommandResult(
                returncode=0,
                stdout="GITHUB_TOKEN=fixture-value\n",
                stderr="remote https://alice:URLSECRET123456@github.com/acme/private.git\n",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch(
                "base_projects.workspace_init.run_project_command",
                return_value=result,
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    workspace_init_module.clone_workspace_config_repo(
                        ctx,
                        "acme/private",
                        root / "workspace-source",
                        dry_run=False,
                    )

        self.assertNotIn("fixture-value", stdout.getvalue())
        self.assertNotIn("URLSECRET123456", stderr.getvalue())
        self.assertIn("GITHUB_TOKEN=[REDACTED]", stdout.getvalue())
        self.assertIn("https://[REDACTED]@github.com", stderr.getvalue())

    def test_workspace_init_command_is_extracted_from_engine(self) -> None:
        workspace_init = importlib.import_module("base_projects.workspace_init")

        actions = engine.project_command_actions()
        self.assertIs(
            actions.workspace_init,
            engine.workspace_init_project_command,
        )
        self.assertIs(
            engine.workspace_init_project_command.__globals__["workspace_init_command"],
            workspace_init.workspace_init_command,
        )

    def test_workspace_init_missing_source_reports_public_command_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()

            status, stdout, stderr = invoke_engine(
                [
                    "init",
                    "--owner",
                    "basefoundry",
                    "--path",
                    str(root),
                    "--workspace",
                    "basefoundry/base-workspace",
                    "--dry-run",
                ],
                base_home,
                home,
            )

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn(
            "The 'basectl workspace init' command requires the positional argument <workspace-source>. "
            "Option '--workspace' selects the local directory for member repositories, "
            "not the workspace source.",
            stderr,
        )
        self.assertNotIn("Project command 'init' requires at least", stderr)

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

    def test_workspace_init_decodes_file_url_paths_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            source = root / "Base Workspace-雪-%20"
            state_file = root / "basectl-calls"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            source.mkdir()
            write_workspace_manifest(source / "workspace.yaml")
            write_fake_basectl(base_home, state_file)
            source_url = source.as_uri()

            status, stdout, stderr = invoke_engine(
                [
                    "init",
                    source_url,
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                ],
                base_home,
                home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace source: {source_url}", stdout)
        self.assertIn(f"Workspace config repo: {source.resolve()}", stdout)
        self.assertIn(f"Workspace manifest: {(source / 'workspace.yaml').resolve()} (demo-suite)", stdout)

    def test_workspace_init_accepts_localhost_file_url_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            source = root / "base-workspace"
            state_file = root / "basectl-calls"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            source.mkdir()
            write_workspace_manifest(source / "workspace.yaml")
            write_fake_basectl(base_home, state_file)
            source_url = source.as_uri().replace("file:///", "file://localhost/", 1)

            status, stdout, stderr = invoke_engine(
                ["init", source_url, "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace config repo: {source.resolve()}", stdout)

    def test_workspace_init_rejects_remote_and_malformed_file_urls(self) -> None:
        cases = (
            (
                "file://files.example.test/private/workspace",
                "support only an empty or localhost authority",
            ),
            (
                "file:///private/tmp/Base%2Workspace",
                "malformed percent encoding",
            ),
        )
        for source_url, expected_message in cases:
            with self.subTest(source_url=source_url):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    home = root / "home"
                    base_home = root / "base"
                    workspace = root / "workspace"
                    home.mkdir()
                    base_home.mkdir()
                    workspace.mkdir()

                    status, stdout, stderr = invoke_engine(
                        ["init", source_url, "--workspace", str(workspace), "--dry-run"],
                        base_home,
                        home,
                    )

                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn(expected_message, stderr)

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

    def test_workspace_init_config_update_is_atomic_and_preserves_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            config_path = home / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("custom:\n  keep: true\n", encoding="utf-8")
            config_path.chmod(0o640)
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"

            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                workspace_init_module.write_workspace_init_user_config(workspace, manifest)

            config_content = config_path.read_text(encoding="utf-8")
            config_mode = config_path.stat().st_mode & 0o777
            temp_files = tuple(config_path.parent.glob(f".{config_path.name}.*"))

        self.assertIn("custom:\n  keep: true", config_content)
        self.assertIn(f"root: {workspace}", config_content)
        self.assertIn(f"manifest: {manifest}", config_content)
        self.assertEqual(config_mode, 0o640)
        self.assertEqual(temp_files, ())

    def test_workspace_init_config_update_preserves_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            config_path = home / ".base.d" / "config.yaml"
            target = root / "shared" / "config.yaml"
            target.parent.mkdir(parents=True)
            target.write_text("custom: keep\n", encoding="utf-8")
            target.chmod(0o640)
            config_path.parent.mkdir(parents=True)
            config_path.symlink_to(target)
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"

            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                workspace_init_module.write_workspace_init_user_config(workspace, manifest)

            config_is_symlink = config_path.is_symlink()
            config_target = config_path.resolve()
            target_content = target.read_text(encoding="utf-8")
            target_mode = target.stat().st_mode & 0o777
            temp_files = tuple(target.parent.glob(f".{target.name}.*"))

        self.assertTrue(config_is_symlink)
        self.assertEqual(config_target, target.resolve())
        self.assertIn(f"root: {workspace}", target_content)
        self.assertEqual(target_mode, 0o640)
        self.assertEqual(temp_files, ())

    def test_workspace_init_config_replace_failure_preserves_previous_content_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            config_path = home / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            original = "custom:\n  keep: true\n"
            config_path.write_text(original, encoding="utf-8")
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"

            with (
                mock.patch.dict(os.environ, {"HOME": str(home)}),
                mock.patch.object(workspace_init_module.os, "replace", side_effect=OSError("replace failed")),
            ):
                with self.assertRaisesRegex(WorkspaceManifestError, "atomically: replace failed"):
                    workspace_init_module.write_workspace_init_user_config(workspace, manifest)

            self.assertEqual(config_path.read_text(encoding="utf-8"), original)
            temp_files = tuple(config_path.parent.glob(f".{config_path.name}.*"))

        self.assertEqual(temp_files, ())

    def test_workspace_init_config_temp_write_failure_preserves_previous_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            config_path = home / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            original = "custom:\n  keep: true\n"
            config_path.write_text(original, encoding="utf-8")
            workspace = root / "workspace"
            manifest = root / "workspace.yaml"

            with (
                mock.patch.dict(os.environ, {"HOME": str(home)}),
                mock.patch.object(
                    workspace_init_module.tempfile,
                    "NamedTemporaryFile",
                    side_effect=OSError("write failed"),
                ),
            ):
                with self.assertRaisesRegex(WorkspaceManifestError, "atomically: write failed"):
                    workspace_init_module.write_workspace_init_user_config(workspace, manifest)

            self.assertEqual(config_path.read_text(encoding="utf-8"), original)

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
                    "--owner",
                    "codeforester",
                    "--path",
                    str(source),
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                    "base-workspace",
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

    def test_resolve_workspace_config_repo_path_uses_explicit_repo_name_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir) / "workspace"
            ctx = SimpleNamespace(workspace_root=workspace_root, application_home=None)
            source = workspace_init_module.WorkspaceInitSource(
                display="codeforester/base-workspace",
                repo_spec="codeforester/base-workspace",
                repo_name=None,
            )
            options = SimpleNamespace(workspace=None, workspace_config_path=None)

            with self.assertRaisesRegex(ValueError, "repo_name"):
                workspace_init_module.resolve_workspace_config_repo_path(ctx, source, options)
