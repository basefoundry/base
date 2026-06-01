from __future__ import annotations

# pylint: disable=too-many-public-methods

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_test_manifest(project_root: Path, name: str, command: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ntest:\n  command: {command}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_mise_test_manifest(project_root: Path, name: str, task: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ntest:\n  mise: {task}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_commands_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "test:",
                "  command: pytest tests/",
                "commands:",
                "  dev: uvicorn app:app --reload",
                "  lint: ruff check .",
                "artifacts: []",
            ]
        ),
        encoding="utf-8",
    )


def write_demo_manifest(project_root: Path, name: str, script: str) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ndemo:\n  script: {script}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_activation_manifest(project_root: Path, name: str, sources: list[str]) -> None:
    project_root.mkdir(parents=True)
    source_lines = "\n".join(f"    - {source}" for source in sources)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\nactivate:\n  source:\n{source_lines}\nartifacts: []\n",
        encoding="utf-8",
    )


def invoke_engine(
    args: list[str],
    base_home: Path,
    home: Path,
    user_config: str | None = None,
    extra_env: dict[str, str] | None = None,
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
    if extra_env is not None:
        env.update(extra_env)
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def run_engine(
    args: list[str],
    base_home: Path,
    user_config: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as home_dir:
        return invoke_engine(args, base_home, Path(home_dir), user_config=user_config, extra_env=extra_env)


def run_engine_with_home(args: list[str], base_home: Path, home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_HOME": str(base_home)}):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class ProjectDiscoveryTests(unittest.TestCase):
    def test_discovers_projects_under_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            write_manifest(workspace / "zeta", "zeta")
            write_manifest(workspace / "alpha", "alpha")
            (workspace / "notes").mkdir()

            projects = engine.discover_projects(workspace)

        self.assertEqual([project.name for project in projects], ["alpha", "zeta"])

    def test_projects_list_defaults_to_base_home_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            write_manifest(base_home, "base")
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(["list"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"base\t{base_home.resolve()}", stdout)
        self.assertIn(f"demo\t{(workspace / 'demo').resolve()}", stdout)

    def test_projects_list_supports_workspace_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "custom"
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(["list", "--workspace", str(workspace)], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{(workspace / 'demo').resolve()}\n")

    def test_projects_list_prefers_configured_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "configured-workspace"
            base_home = root / "homebrew" / "base" / "libexec"
            base_home.mkdir(parents=True)
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(
                ["list"],
                base_home,
                user_config=f"workspace:\n  root: {workspace}\n",
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{(workspace / 'demo').resolve()}\n")

    def test_projects_list_workspace_override_wins_over_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            configured_workspace = root / "configured"
            explicit_workspace = root / "explicit"
            base_home = root / "homebrew" / "base" / "libexec"
            base_home.mkdir(parents=True)
            write_manifest(configured_workspace / "configured-demo", "configured-demo")
            write_manifest(explicit_workspace / "explicit-demo", "explicit-demo")

            status, stdout, stderr = run_engine(
                ["list", "--workspace", str(explicit_workspace)],
                base_home,
                user_config=f"workspace:\n  root: {configured_workspace}\n",
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"explicit-demo\t{(explicit_workspace / 'explicit-demo').resolve()}\n")

    def test_projects_list_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "custom"
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(
                ["list", "--workspace", str(workspace), "--format", "json"],
                base_home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), [{"name": "demo", "path": str((workspace / "demo").resolve())}])

    def test_projects_list_reuses_project_cache_when_manifests_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            with mock.patch("base_projects.engine.read_project", wraps=engine.read_project) as read_project_mock:
                status, stdout, stderr = invoke_engine(["list", "--workspace", str(workspace)], base_home, home)
                self.assertEqual(status, 0)
                self.assertEqual(stderr, "")
                self.assertEqual(stdout, f"demo\t{(workspace / 'demo').resolve()}\n")

                status, stdout, stderr = invoke_engine(["list", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{(workspace / 'demo').resolve()}\n")
        self.assertEqual(read_project_mock.call_count, 1)

    def test_projects_list_invalidates_project_cache_when_manifest_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo")

            with mock.patch("base_projects.engine.read_project", wraps=engine.read_project) as read_project_mock:
                status, stdout, stderr = invoke_engine(["list", "--workspace", str(workspace)], base_home, home)
                self.assertEqual(status, 0)
                self.assertEqual(stderr, "")
                self.assertEqual(stdout, f"demo\t{project_root.resolve()}\n")

                manifest = project_root / "base_manifest.yaml"
                manifest.write_text("project:\n  name: renamed\nartifacts: []\n", encoding="utf-8")
                stat_result = manifest.stat()
                os.utime(manifest, ns=(stat_result.st_atime_ns, stat_result.st_mtime_ns + 1_000_000_000))
                status, stdout, stderr = invoke_engine(["list", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"renamed\t{project_root.resolve()}\n")
        self.assertEqual(read_project_mock.call_count, 2)

    def test_projects_list_rejects_unknown_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, _stdout, stderr = run_engine(["list", "--format", "xml"], base_home)

        self.assertEqual(status, 2)
        self.assertIn("Unsupported output format 'xml'", stderr)

    def test_projects_resolve_prints_project_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["resolve", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\n")

    def test_projects_resolve_uses_active_project_manifest_without_workspace_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_home = root / "base"
            base_home.mkdir()
            project_root = root / "active" / "demo"
            manifest_path = project_root / "base_manifest.yaml"
            write_manifest(project_root, "demo")

            with mock.patch(
                "base_projects.engine.discover_projects_cached",
                side_effect=AssertionError("workspace scan should not run"),
            ):
                status, stdout, stderr = run_engine(
                    ["resolve", "demo"],
                    base_home,
                    extra_env={
                        "BASE_PROJECT": "demo",
                        "BASE_PROJECT_MANIFEST": str(manifest_path),
                    },
                )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{manifest_path.resolve()}\n")

    def test_projects_resolve_explicit_workspace_wins_over_active_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_home = root / "base"
            base_home.mkdir()
            active_root = root / "active" / "demo"
            explicit_workspace = root / "explicit"
            explicit_root = explicit_workspace / "demo"
            write_manifest(active_root, "demo")
            write_manifest(explicit_root, "demo")

            status, stdout, stderr = run_engine(
                ["resolve", "demo", "--workspace", str(explicit_workspace)],
                base_home,
                extra_env={
                    "BASE_PROJECT": "demo",
                    "BASE_PROJECT_MANIFEST": str(active_root / "base_manifest.yaml"),
                },
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{explicit_root.resolve()}\t{(explicit_root / 'base_manifest.yaml').resolve()}\n",
        )

    def test_projects_resolve_rejects_active_project_manifest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_home = root / "base"
            base_home.mkdir()
            project_root = root / "active" / "demo"
            write_manifest(project_root, "other")

            status, _stdout, stderr = run_engine(
                ["resolve", "demo"],
                base_home,
                extra_env={
                    "BASE_PROJECT": "demo",
                    "BASE_PROJECT_MANIFEST": str(project_root / "base_manifest.yaml"),
                },
            )

        self.assertEqual(status, 1)
        self.assertIn("BASE_PROJECT is 'demo' but BASE_PROJECT_MANIFEST points to project 'other'", stderr)

    def test_projects_resolve_prefers_configured_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "configured-workspace"
            base_home = root / "homebrew" / "base" / "libexec"
            base_home.mkdir(parents=True)
            project_root = workspace / "demo"
            write_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(
                ["resolve", "demo"],
                base_home,
                user_config=f"workspace:\n  root: {workspace}\n",
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\n")

    def test_projects_resolve_base_uses_base_home_without_workspace_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            other_base = workspace / "base-worktree"
            write_manifest(base_home, "base")
            write_manifest(other_base, "base")

            status, stdout, stderr = run_engine(["resolve", "base"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"base\t{base_home.resolve()}\t{(base_home / 'base_manifest.yaml').resolve()}\n")

    def test_projects_resolve_base_uses_base_home_with_configured_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "configured-workspace"
            base_home = root / "homebrew" / "base" / "libexec"
            other_base = workspace / "base"
            write_manifest(base_home, "base")
            write_manifest(other_base, "base")

            status, stdout, stderr = run_engine(
                ["resolve", "base"],
                base_home,
                user_config=f"workspace:\n  root: {workspace}\n",
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"base\t{base_home.resolve()}\t{(base_home / 'base_manifest.yaml').resolve()}\n")

    def test_projects_test_command_prints_project_details_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_test_manifest(project_root, "demo", "pytest tests/")

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/\n",
        )

    def test_projects_test_command_for_base_uses_base_home_without_workspace_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            other_base = workspace / "base-worktree"
            write_test_manifest(base_home, "base", "./bin/base-test")
            write_test_manifest(other_base, "base", "false")

            status, stdout, stderr = run_engine(["test-command", "base"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"base\t{base_home.resolve()}\t{(base_home / 'base_manifest.yaml').resolve()}\t./bin/base-test\n",
        )

    def test_projects_test_command_prints_mise_task_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_mise_test_manifest(project_root, "demo", "unit")

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tmise run unit\n",
        )

    def test_projects_activation_sources_prints_validated_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            first_source = project_root / ".base" / "activate.sh"
            second_source = project_root / "scripts" / "local-env.sh"
            write_activation_manifest(project_root, "demo", [".base/activate.sh", "scripts/local-env.sh"])
            first_source.parent.mkdir()
            second_source.parent.mkdir()
            first_source.write_text("export DEMO=1\n", encoding="utf-8")
            second_source.write_text("export LOCAL_ENV=1\n", encoding="utf-8")

            status, stdout, stderr = run_engine(["activation-sources", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"{first_source.resolve()}\n{second_source.resolve()}\n")

    def test_projects_activation_sources_uses_active_project_manifest_without_workspace_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_home = root / "base"
            base_home.mkdir()
            project_root = root / "active" / "demo"
            activation_script = project_root / ".base" / "activate.sh"
            write_activation_manifest(project_root, "demo", [".base/activate.sh"])
            activation_script.parent.mkdir()
            activation_script.write_text("export DEMO=1\n", encoding="utf-8")

            with mock.patch(
                "base_projects.engine.discover_projects_cached",
                side_effect=AssertionError("workspace scan should not run"),
            ):
                status, stdout, stderr = run_engine(
                    ["activation-sources", "demo"],
                    base_home,
                    extra_env={
                        "BASE_PROJECT": "demo",
                        "BASE_PROJECT_MANIFEST": str(project_root / "base_manifest.yaml"),
                    },
                )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"{activation_script.resolve()}\n")

    def test_projects_activation_sources_supports_empty_manifest_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(["activation-sources", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, "")

    def test_projects_activation_sources_rejects_unsafe_paths(self) -> None:
        cases = {
            "absolute": ("/tmp/base-activate.sh", "must be a relative path"),
            "outside": ("../outside.sh", "resolves outside the project root"),
            "missing": ("missing.sh", "does not exist"),
            "directory": ("scripts", "is not a file"),
        }
        for name, (source_path, expected_error) in cases.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    workspace = Path(tmpdir)
                    base_home = workspace / "base"
                    base_home.mkdir()
                    project_root = workspace / "demo"
                    write_activation_manifest(project_root, "demo", [source_path])
                    if name == "directory":
                        (project_root / "scripts").mkdir()

                    status, _stdout, stderr = run_engine(["activation-sources", "demo"], base_home)

                self.assertEqual(status, 1)
                self.assertIn(expected_error, stderr)

    def test_projects_activation_sources_requires_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()

        status, _stdout, stderr = run_engine(["activation-sources"], base_home)

        self.assertEqual(status, 2)
        self.assertIn("Project command 'activation-sources' requires at least 1 argument", stderr)

    def test_test_command_rejects_invalid_config_without_assert(self) -> None:
        with self.assertRaisesRegex(ValueError, "TestConfig must have command or mise set"):
            engine.test_command(engine.TestConfig())

    def test_projects_test_command_defaults_to_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs"
            write_test_manifest(project_root, "demo", "pytest tests/")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["test-command"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/\n",
        )

    def test_projects_test_command_requires_manifest_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare test.command or test.mise", stderr)

    def test_projects_run_command_prints_project_details_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["run-command", "demo", "dev"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            "\tuvicorn app:app --reload\n",
        )

    def test_projects_run_command_test_delegates_to_test_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["run-command", "demo", "test"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/\n",
        )

    def test_projects_run_command_reports_unknown_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_commands_manifest(project_root, "demo")

            status, _stdout, stderr = run_engine(["run-command", "demo", "serve"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare command 'serve'", stderr)

    def test_projects_demo_script_prints_project_details_and_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            script = project_root / "demo" / "demo.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o755)
            write_demo_manifest(project_root, "demo", "./demo/demo.sh")

            status, stdout, stderr = run_engine(["demo-script", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\t{script.resolve()}\n",
        )

    def test_projects_demo_script_requires_demo_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["demo-script", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("No demo declared for project 'demo'", stderr)

    def test_projects_demo_script_rejects_missing_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_demo_manifest(project_root, "demo", "./demo/demo.sh")

            status, _stdout, stderr = run_engine(["demo-script", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not exist", stderr)

    def test_projects_run_commands_lists_test_and_manifest_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["run-commands", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\ttest\tpytest tests/\n"
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            "\tdev\tuvicorn app:app --reload\n"
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            "\tlint\truff check .\n",
        )

    def test_projects_run_commands_defaults_to_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs"
            write_commands_manifest(project_root, "demo")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["run-commands"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("\ttest\tpytest tests/\n", stdout)
        self.assertIn("\tdev\tuvicorn app:app --reload\n", stdout)

    def test_projects_run_commands_requires_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, _stdout, stderr = run_engine(["run-commands", "demo"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("does not declare runnable commands", stderr)

    def test_projects_manifest_prints_project_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            manifest_path = project_root / "base_manifest.yaml"
            write_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["manifest", str(manifest_path)], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{manifest_path.resolve()}\n")

    def test_projects_manifest_requires_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()

            status, _stdout, stderr = run_engine(["manifest"], base_home)

        self.assertEqual(status, 2)
        self.assertIn("Manifest path is required", stderr)

    def test_projects_current_prints_nearest_project_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs" / "notes"
            write_manifest(project_root, "demo")
            nested.mkdir(parents=True)

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["current"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\n")

    def test_projects_current_reports_missing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            outside = workspace / "outside"
            outside.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(outside)
                status, _stdout, stderr = run_engine(["current"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 1)
        self.assertIn("No base_manifest.yaml found", stderr)

    def test_projects_resolve_reports_missing_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            status, _stdout, stderr = run_engine(["resolve", "missing"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("Project 'missing' was not found", stderr)

    def test_projects_list_reports_invalid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            bad = workspace / "bad"
            bad.mkdir()
            (bad / "base_manifest.yaml").write_text("project: []\n", encoding="utf-8")

            status, _stdout, stderr = run_engine(["list"], base_home)

        self.assertEqual(status, 1)
        self.assertIn("project must be a mapping", stderr)

    def test_projects_list_rejects_duplicate_project_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            write_manifest(workspace / "one", "demo")
            write_manifest(workspace / "two", "demo")

            with self.assertRaisesRegex(engine.ProjectDiscoveryError, "Duplicate project names"):
                engine.discover_projects(workspace)

if __name__ == "__main__":
    unittest.main()
