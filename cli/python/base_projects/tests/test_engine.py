from __future__ import annotations

# pylint: disable=too-many-lines,too-many-public-methods

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_cli.command_protocol import loads_records
from base_cli.history import build_finished_record
from base_projects import engine, project_discovery


def write_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\npython: {{}}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_shell_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\nartifacts: []\n",
        encoding="utf-8",
    )


def write_uv_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\npython:\n  manager: uv\n",
        encoding="utf-8",
    )
    python_bin = project_root / ".venv" / "bin" / "python"
    write_ready_python_bin(python_bin)


def write_inline_uv_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\npython: {{manager: uv}}\nartifacts: []\n",
        encoding="utf-8",
    )
    python_bin = project_root / ".venv" / "bin" / "python"
    write_ready_python_bin(python_bin)


def write_ready_python_bin(python_bin: Path) -> None:
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_bin.chmod(0o755)


def write_versioned_python_bin(python_bin: Path, version: str) -> None:
    python_bin.parent.mkdir(parents=True, exist_ok=True)
    python_bin.write_text(f"#!/bin/sh\nprintf '{version}\\n'\n", encoding="utf-8")
    python_bin.chmod(0o755)


_engine_homes: list[Path] = []


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


def base_route_fields(
    base_home: Path,
    project: str,
    *,
    trust_required: bool = True,
    project_root: Path | None = None,
) -> str:
    if not _engine_homes:
        raise AssertionError("run_engine must be called before base_route_fields")
    if project == "base":
        resolved_root = base_home
        venv_dir = _engine_homes[-1] / ".base.d" / project / ".venv"
    else:
        resolved_root = project_root if project_root is not None else base_home.parent / project
        venv_dir = (resolved_root / ".venv").resolve()
    trust_value = "true" if trust_required else "false"
    return (
        f"\t__base_project_venv_dir={venv_dir}"
        "\t__base_uses_uv_manager=false"
        f"\t__base_manifest_command_trust_required={trust_value}"
    )


def uv_route_fields(project_root: Path, *, trust_required: bool = True) -> str:
    trust_value = "true" if trust_required else "false"
    return (
        f"\t__base_project_venv_dir={(project_root / '.venv').resolve()}"
        "\t__base_uses_uv_manager=true"
        f"\t__base_manifest_command_trust_required={trust_value}"
    )


def write_last_check(home: Path, project: str, checked_at: str, status: str = "ok") -> None:
    record_path = home / ".base.d" / project / "checks" / "last.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": project,
                "command": "basectl check",
                "status": status,
                "checked_at": checked_at,
            }
        ),
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


def write_runner_commands_manifest(project_root: Path, name: str) -> None:
    project_root.mkdir(parents=True)
    (project_root / "base_manifest.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "test:",
                "  command: pytest tests/",
                "  runner: uv",
                "commands:",
                "  audit:",
                "    command: pytest tests/audit",
                "    runner: uv",
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


def write_runner_demo_manifest(project_root: Path, name: str, script: str) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "base_manifest.yaml").write_text(
        f"project:\n  name: {name}\ndemo:\n  script: {script}\n  runner: uv\nartifacts: []\n",
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
    workspace_commands = {"status", "check", "doctor", "onboarding", "agent-brief", "run-commands"}
    stdout = TerminalStringIO() if any(argument in workspace_commands for argument in args) else io.StringIO()
    stderr = io.StringIO()
    if user_config is not None:
        config_path = home / ".base.d" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
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
        _engine_homes.append(Path(home_dir))
        return invoke_engine(args, base_home, _engine_homes[-1], user_config=user_config, extra_env=extra_env)


def run_engine_with_home(args: list[str], base_home: Path, home: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.dict(os.environ, {"HOME": str(home), "BASE_HOME": str(base_home)}):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class ProjectDiscoveryTests(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_command_protocol_covers_project_command_bridge_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "space λ demo"
            nested = project_root / "docs"
            demo_script = project_root / "demo" / "demo λ.sh"
            activation_script = project_root / "scripts" / "activate λ.sh"
            demo_script.parent.mkdir(parents=True)
            activation_script.parent.mkdir(parents=True)
            nested.mkdir()
            demo_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            demo_script.chmod(0o755)
            activation_script.write_text("export DEMO=1\n", encoding="utf-8")
            manifest_path = project_root / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        '  command: "pytest tests/\\tunit"',
                        "commands:",
                        "  dev:",
                        '    command: "printf λ done"',
                        "    runner: uv",
                        "demo:",
                        '  script: "demo/demo λ.sh"',
                        "activate:",
                        "  source:",
                        '    - "scripts/activate λ.sh"',
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, stderr = run_engine(["resolve", "demo", "--format", "command-protocol"], base_home)
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "project-route")
            self.assertEqual(records[0]["project_root"], str(project_root.resolve()))
            self.assertTrue(records[0]["manifest_command_trust_required"])

            status, stdout, stderr = run_engine(
                ["test-command", "demo", "--format", "command-protocol"], base_home
            )
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "project-command")
            self.assertEqual(records[0]["command"], "pytest tests/\tunit")
            self.assertIsNone(records[0]["runner"])

            status, stdout, stderr = run_engine(
                ["run-command", "demo", "dev", "--format", "command-protocol"], base_home
            )
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "project-command")
            self.assertEqual(records[0]["command"], "printf λ done")
            self.assertEqual(records[0]["runner"], "uv")

            status, stdout, stderr = run_engine(
                ["run-commands", "demo", "--format", "command-protocol"], base_home
            )
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "named-command")
            self.assertEqual([record["command_name"] for record in records], ["test", "dev"])

            status, stdout, stderr = run_engine(
                ["demo-script", "demo", "--format", "command-protocol"], base_home
            )
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "demo")
            self.assertEqual(records[0]["demo_script"], str(demo_script.resolve()))

            status, stdout, stderr = run_engine(
                ["activation-sources", "demo", "--format", "command-protocol"], base_home
            )
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "activation-source")
            self.assertEqual(records[0]["source_path"], str(activation_script.resolve()))

            status, stdout, stderr = run_engine(["list", "--format", "command-protocol"], base_home)
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "project-list-entry")
            self.assertEqual(records[0]["project_name"], "demo")

            status, stdout, stderr = run_engine(
                ["manifest", str(manifest_path), "--format", "command-protocol"], base_home
            )
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "project-reference")
            self.assertEqual(records[0]["manifest_path"], str(manifest_path.resolve()))

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["current", "--format", "command-protocol"], base_home)
            finally:
                os.chdir(old_cwd)
            self.assertEqual((status, stderr), (0, ""))
            _, records = loads_records(stdout, "project-reference")
            self.assertEqual(records[0]["project_name"], "demo")

    def test_project_discovery_implementation_is_split_from_engine(self) -> None:
        engine_path = Path(engine.__file__)
        discovery_path = engine_path.with_name("project_discovery.py")

        self.assertTrue(discovery_path.exists())
        self.assertIn("def discover_projects_cached", discovery_path.read_text(encoding="utf-8"))
        self.assertNotIn("def discover_projects_cached", engine_path.read_text(encoding="utf-8"))

    def test_workspace_pull_command_is_split_from_engine(self) -> None:
        engine_path = Path(engine.__file__)
        pull_command_path = engine_path.with_name("workspace_pull_command.py")

        self.assertTrue(pull_command_path.exists())
        self.assertIn("def workspace_pull_command", pull_command_path.read_text(encoding="utf-8"))
        self.assertNotIn("def workspace_pull_command", engine_path.read_text(encoding="utf-8"))

    def test_project_discovery_does_not_import_workspace_reports(self) -> None:
        discovery_path = Path(project_discovery.__file__)

        self.assertNotIn("workspace_reports", discovery_path.read_text(encoding="utf-8"))

    def test_main_reports_config_errors_without_traceback(self) -> None:
        status, _stdout, stderr = run_engine(
            ["list"],
            Path(__file__).resolve().parents[4],
            user_config="workspace: [not-a-mapping]\n",
        )

        self.assertEqual(status, 1)
        self.assertIn("workspace must be a mapping", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_discovers_projects_under_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            write_manifest(workspace / "zeta", "zeta")
            write_manifest(workspace / "alpha", "alpha")
            (workspace / "notes").mkdir()

            projects = project_discovery.discover_projects(workspace)

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

    def test_projects_list_supports_csv_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "custom"
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(
                ["list", "--workspace", str(workspace), "--format", "csv"],
                base_home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, f"demo,{(workspace / 'demo').resolve()}\n")

    def test_projects_list_supports_yaml_format(self) -> None:
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "custom"
            base_home = Path(tmpdir) / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(
                ["list", "--workspace", str(workspace), "--format", "yaml"],
                base_home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(yaml.safe_load(stdout), [{"name": "demo", "path": str((workspace / "demo").resolve())}])

    def test_workspace_status_reports_manifest_and_venv_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_manifest(workspace / "base", "base")
            write_manifest(workspace / "demo", "demo")
            python_bin = home / ".base.d" / "base" / ".venv" / "bin" / "python"
            write_ready_python_bin(python_bin)
            write_last_check(home, "base", "2026-06-17T14:30:00Z")

            status, stdout, stderr = invoke_engine(["status", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace: {workspace.resolve()} (2 projects)", stdout)
        self.assertIn("base                 ok     ready          valid    2026-06-17", stdout)
        self.assertIn("demo                 warn   missing        valid    -", stdout)
        self.assertIn("1 project(s) need attention", stdout)

    def test_workspace_status_reports_uv_project_venv_ready_without_base_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_uv_manifest(workspace / "bankbuddy", "bankbuddy")

            status, stdout, stderr = invoke_engine(["status", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("bankbuddy            ok     ready          valid    -", stdout)
        self.assertIn("All discovered projects look ok.", stdout)

    def test_workspace_status_reports_shell_only_project_venv_not_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            project_root = workspace / "shell-only"
            write_shell_manifest(project_root, "shell-only")

            status, stdout, stderr = invoke_engine(
                ["status", "--workspace", str(workspace), "--format", "json"],
                base_home,
                home,
            )
            self.assertFalse((project_root / ".venv").exists())

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["projects"][0]["status"], "ok")
        self.assertEqual(payload["projects"][0]["venv"], "not_applicable")
        self.assertEqual(payload["projects"][0]["issues"], [])

    def test_workspace_status_text_aligns_shell_only_project_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            project_root = workspace / "shell-only"
            write_shell_manifest(project_root, "shell-only")

            status, stdout, stderr = invoke_engine(["status", "--workspace", str(workspace)], base_home, home)

        lines = stdout.splitlines()
        header = next(line for line in lines if line.startswith("PROJECT"))
        project_line = next(line for line in lines if line.startswith("shell-only"))
        manifest_column = header.index("MANIFEST")
        last_check_column = header.index("LAST CHECK")
        path_column = header.index("PATH")

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(project_line[header.index("VENV") : manifest_column].rstrip(), "not_applicable")
        self.assertEqual(project_line[manifest_column : manifest_column + len("valid")], "valid")
        self.assertEqual(project_line[last_check_column], "-")
        self.assertEqual(project_line[path_column:], str(project_root.resolve()))

    def test_workspace_status_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")
            write_last_check(home, "demo", "2026-06-17T14:30:00Z", status="error")

            status, stdout, stderr = invoke_engine(
                ["status", "--workspace", str(workspace), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(stdout.startswith("{\n"))
        self.assertIn('  "workspace": ', stdout)
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertEqual(payload["project_count"], 1)
        self.assertEqual(payload["projects"][0]["name"], "demo")
        self.assertEqual(payload["projects"][0]["status"], "warn")
        self.assertEqual(payload["projects"][0]["venv"], "missing")
        self.assertEqual(payload["projects"][0]["manifest"], "valid")
        self.assertEqual(
            payload["projects"][0]["last_check"],
            {
                "checked_at": "2026-06-17T14:30:00Z",
                "status": "error",
            },
        )
        self.assertIn("project virtual environment missing", payload["projects"][0]["issues"][0])

    def test_workspace_status_debug_logs_default_discovery_scan_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = workspace / "base"
            home.mkdir()
            write_manifest(base_home, "base")
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = invoke_engine(
                ["--debug", "status", "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertIn(f"Workspace status root: {workspace.resolve()} (source: BASE_HOME parent).", stderr)
        self.assertIn(
            "Workspace status manifest: none supplied or configured; scanning immediate child directories "
            f"under {workspace.resolve()} for base_manifest.yaml.",
            stderr,
        )

    def test_workspace_status_json_reports_uv_project_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            project_root = workspace / "bankbuddy"
            home.mkdir()
            base_home.mkdir()
            write_uv_manifest(project_root, "bankbuddy")
            python_bin = project_root / ".venv" / "bin" / "python"
            write_versioned_python_bin(python_bin, "3.12")

            status, stdout, stderr = invoke_engine(
                ["status", "--workspace", str(workspace), "--format", "json"],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        runtime = payload["projects"][0]["python_runtime"]
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(runtime["manager"], "uv")
        self.assertEqual(runtime["version"], "3.12")
        self.assertEqual(runtime["python"], str(python_bin.resolve()))
        self.assertEqual(runtime["venv"], str(python_bin.parent.parent.resolve()))

    def test_workspace_status_reports_invalid_manifest_without_stopping_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")
            broken_root = workspace / "broken"
            broken_root.mkdir(parents=True)
            (broken_root / "base_manifest.yaml").write_text("project: [", encoding="utf-8")

            status, stdout, stderr = invoke_engine(["status", "--workspace", str(workspace)], base_home, home)

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn("broken               error  unknown        invalid", stdout)
        self.assertIn("demo                 warn   missing        valid", stdout)
        self.assertIn("2 project(s) need attention", stdout)

    def test_projects_list_reuses_project_cache_when_manifests_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            with mock.patch(
                "base_projects.project_discovery.read_project", wraps=project_discovery.read_project
            ) as read_project_mock:
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

            with mock.patch(
                "base_projects.project_discovery.read_project", wraps=project_discovery.read_project
            ) as read_project_mock:
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

    def test_projects_list_dry_run_does_not_write_discovery_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            with mock.patch("base_projects.project_discovery.write_project_cache") as write_cache:
                status, stdout, stderr = run_engine(
                    ["list", "--workspace", str(workspace), "--dry-run"],
                    base_home,
                )

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("demo\t", stdout)
        write_cache.assert_not_called()

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
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"{base_route_fields(base_home, 'demo', trust_required=False)}\n",
        )

    def test_projects_resolve_populates_history_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_manifest(project_root, "demo")
            outside = workspace / "outside"
            outside.mkdir()
            captured: list[tuple[object, ...]] = []

            with (
                mock.patch("base_cli.app.current_working_dir", return_value=outside),
                mock.patch(
                    "base_cli.app.write_finished_record",
                    side_effect=lambda *args: captured.append(args),
                ),
            ):
                status, _stdout, stderr = run_engine(["resolve", "demo"], base_home)

            self.assertEqual((status, stderr), (0, ""))
            self.assertEqual(len(captured), 1)
            record = build_finished_record(*captured[0])

        self.assertEqual(record["project"], "demo")
        self.assertEqual(record["project_root"], str(project_root.resolve()))
        self.assertEqual(record["manifest"], str((project_root / "base_manifest.yaml").resolve()))

    def test_projects_resolve_prints_python_route_metadata_for_inline_uv_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_inline_uv_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["resolve", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"{uv_route_fields(project_root, trust_required=False)}\n",
        )

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

        route_fields = base_route_fields(
            base_home,
            "demo",
            trust_required=False,
            project_root=project_root,
        )
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{manifest_path.resolve()}"
            f"{route_fields}\n",
        )

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

        route_fields = base_route_fields(
            base_home,
            "demo",
            trust_required=False,
            project_root=explicit_root,
        )
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{explicit_root.resolve()}\t{(explicit_root / 'base_manifest.yaml').resolve()}"
            f"{route_fields}\n",
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

        route_fields = base_route_fields(
            base_home,
            "demo",
            trust_required=False,
            project_root=project_root,
        )
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"{route_fields}\n",
        )

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
        self.assertEqual(
            stdout,
            f"base\t{base_home.resolve()}\t{(base_home / 'base_manifest.yaml').resolve()}"
            f"{base_route_fields(base_home, 'base', trust_required=False)}\n",
        )

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
        self.assertEqual(
            stdout,
            f"base\t{base_home.resolve()}\t{(base_home / 'base_manifest.yaml').resolve()}"
            f"{base_route_fields(base_home, 'base', trust_required=False)}\n",
        )

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
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/"
            f"{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_test_command_marks_manifest_command_trust_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_test_manifest(project_root, "demo", "pytest tests/")

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("__base_manifest_command_trust_required=true", stdout)

    def test_projects_test_command_prints_python_route_metadata_for_inline_uv_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            project_root.mkdir(parents=True)
            (project_root / "base_manifest.yaml").write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python: {manager: uv}",
                        "test:",
                        "  command: pytest tests/",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tpytest tests/\t__base_project_venv_dir={(project_root / '.venv').resolve()}"
            "\t__base_uses_uv_manager=true"
            "\t__base_manifest_command_trust_required=true\n",
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
            f"base\t{base_home.resolve()}\t{(base_home / 'base_manifest.yaml').resolve()}\t./bin/base-test"
            f"{base_route_fields(base_home, 'base')}\n",
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
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tmise run unit"
            f"{base_route_fields(base_home, 'demo')}\n",
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

    def test_projects_resolve_marks_activation_trust_required_only_when_sources_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            activation_script = project_root / ".base" / "activate.sh"
            write_activation_manifest(project_root, "demo", [".base/activate.sh"])
            activation_script.parent.mkdir()
            activation_script.write_text("export DEMO=1\n", encoding="utf-8")

            status, stdout, stderr = run_engine(["resolve", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("__base_manifest_command_trust_required=true", stdout)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            write_manifest(workspace / "demo", "demo")

            status, stdout, stderr = run_engine(["resolve", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("__base_manifest_command_trust_required=false", stdout)

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
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/"
            f"{base_route_fields(base_home, 'demo')}\n",
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
            f"\tuvicorn app:app --reload{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_run_command_prints_python_route_metadata_for_inline_uv_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            project_root.mkdir(parents=True)
            (project_root / "base_manifest.yaml").write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python: {manager: uv}",
                        "commands:",
                        "  dev: uvicorn app:app --reload",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, stderr = run_engine(["run-command", "demo", "dev"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tuvicorn app:app --reload\t__base_project_venv_dir={(project_root / '.venv').resolve()}"
            "\t__base_uses_uv_manager=true"
            "\t__base_manifest_command_trust_required=true\n",
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
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}\tpytest tests/"
            f"{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_run_command_prints_runner_when_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_runner_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["run-command", "demo", "audit"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tpytest tests/audit\tuv{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_test_command_prints_runner_when_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_runner_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["test-command", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\tpytest tests/\tuv{base_route_fields(base_home, 'demo')}\n",
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
            f"\t{script.resolve()}{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_demo_script_prints_python_route_metadata_for_inline_uv_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            script = project_root / "demo" / "demo.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o755)
            (project_root / "base_manifest.yaml").write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python: {manager: uv}",
                        "demo:",
                        "  script: ./demo/demo.sh",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, stderr = run_engine(["demo-script", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\t{script.resolve()}\t__base_project_venv_dir={(project_root / '.venv').resolve()}"
            "\t__base_uses_uv_manager=true"
            "\t__base_manifest_command_trust_required=true\n",
        )

    def test_projects_demo_script_prints_runner_when_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            script = project_root / "demo" / "demo.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o755)
            write_runner_demo_manifest(project_root, "demo", "./demo/demo.sh")

            status, stdout, stderr = run_engine(["demo-script", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\t{script.resolve()}\tuv{base_route_fields(base_home, 'demo')}\n",
        )

    def test_projects_demo_script_defaults_to_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            nested = project_root / "docs"
            script = project_root / "demo" / "demo.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script.chmod(0o755)
            write_demo_manifest(project_root, "demo", "./demo/demo.sh")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                status, stdout, stderr = run_engine(["demo-script"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            f"\t{script.resolve()}{base_route_fields(base_home, 'demo')}\n",
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

    def test_projects_run_commands_lists_runners_when_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo"
            write_runner_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(["run-commands", "demo"], base_home)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            "\ttest\tpytest tests/\tuv\n"
            f"demo\t{project_root.resolve()}\t{(project_root / 'base_manifest.yaml').resolve()}"
            "\taudit\tpytest tests/audit\tuv\n",
        )

    def test_projects_run_commands_json_is_stable_and_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            project_root = workspace / "demo with spaces"
            write_runner_commands_manifest(project_root, "demo")

            status, stdout, stderr = run_engine(
                ["run-commands", "demo", "--format", "json"],
                base_home,
            )

        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(
            json.loads(stdout),
            {
                "schema_version": 1,
                "project": {
                    "name": "demo",
                    "root": str(project_root.resolve()),
                    "manifest_path": str((project_root / "base_manifest.yaml").resolve()),
                },
                "commands": [
                    {"name": "test", "command": "pytest tests/", "runner": "uv"},
                    {"name": "audit", "command": "pytest tests/audit", "runner": "uv"},
                ],
            },
        )

    def test_projects_run_command_respects_current_legacy_and_explicit_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            current_root = workspace / "current"
            other_root = workspace / "api"
            nested = current_root / "docs"
            write_commands_manifest(current_root, "current")
            write_commands_manifest(other_root, "api")
            nested.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(nested)
                current_status, current_stdout, current_stderr = run_engine(["run-command", "dev"], base_home)
                legacy_status, legacy_stdout, legacy_stderr = run_engine(
                    ["run-command", "api", "dev"],
                    base_home,
                )
                explicit_status, explicit_stdout, explicit_stderr = run_engine(
                    ["run-command", "dev", "--project", "api"],
                    base_home,
                )
            finally:
                os.chdir(old_cwd)

        self.assertEqual((current_status, current_stderr), (0, ""))
        self.assertTrue(current_stdout.startswith(f"current\t{current_root.resolve()}\t"))
        self.assertEqual((legacy_status, legacy_stderr), (0, ""))
        self.assertTrue(legacy_stdout.startswith(f"api\t{other_root.resolve()}\t"))
        self.assertEqual((explicit_status, explicit_stderr), (0, ""))
        self.assertTrue(explicit_stdout.startswith(f"api\t{other_root.resolve()}\t"))

    def test_projects_run_command_collision_favors_registered_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            current_root = workspace / "current"
            other_root = workspace / "api"
            write_commands_manifest(current_root, "current")
            write_commands_manifest(other_root, "api")
            manifest_path = current_root / "base_manifest.yaml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    "  dev: uvicorn app:app --reload",
                    "  api: printf current-api\n  dev: uvicorn app:app --reload",
                ),
                encoding="utf-8",
            )

            old_cwd = Path.cwd()
            try:
                os.chdir(current_root)
                collision_status, _collision_stdout, collision_stderr = run_engine(
                    ["run-command", "api"],
                    base_home,
                )
                explicit_status, explicit_stdout, explicit_stderr = run_engine(
                    ["run-command", "api", "--project", "current"],
                    base_home,
                )
            finally:
                os.chdir(old_cwd)

        self.assertEqual(collision_status, 2)
        self.assertIn("Command name is required for project 'api'", collision_stderr)
        self.assertEqual((explicit_status, explicit_stderr), (0, ""))
        self.assertIn("\tprintf current-api", explicit_stdout)

    def test_projects_run_command_missing_current_project_is_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                status, stdout, stderr = run_engine(["run-command", "dev"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No base_manifest.yaml found", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_projects_run_command_invalid_current_manifest_is_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            base_home = workspace / "base"
            base_home.mkdir()
            (workspace / "base_manifest.yaml").write_text("project: [\n", encoding="utf-8")

            old_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                status, stdout, stderr = run_engine(["run-command", "dev"], base_home)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertNotIn("Traceback", stderr)

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
                project_discovery.discover_projects(workspace)

if __name__ == "__main__":
    unittest.main()
