from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import base_cli
from base_cli.paths import discover_manifest
from base_projects.engine import Project, ProjectDiscoveryError, find_project, read_project, resolve_workspace_root
from base_setup.manifest import ManifestError, TestConfig, read_manifest


app = base_cli.App(name="base_test")


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option("--workspace", help="Workspace directory to scan. Defaults to BASE_HOME's parent.")
@base_cli.option("--dry-run", is_flag=True, help="Print the test command without running it.")
def run(ctx: base_cli.Context, project: str | None, workspace: str | None, dry_run: bool) -> int:
    try:
        resolved_project = resolve_project(ctx, project, workspace)
        test_config = read_test_config(resolved_project)
    except (ManifestError, ProjectDiscoveryError, TestRunnerError) as exc:
        ctx.log.error(str(exc))
        return 1

    command = command_for_test(test_config)
    display = format_command(command, shell=test_config.command is not None)

    if dry_run:
        print(f"[DRY-RUN] Would run in {resolved_project.root}: {display}")
        return 0

    ctx.log.info("Running tests for project '%s': %s", resolved_project.name, display)
    return run_test_command(command, resolved_project.root, shell=test_config.command is not None)


class TestRunnerError(RuntimeError):
    pass


def resolve_project(ctx: base_cli.Context, project: str | None, workspace: str | None) -> Project:
    if project:
        workspace_root = resolve_workspace_root(ctx, workspace)
        return find_project(workspace_root, project)

    manifest_path = discover_manifest(Path.cwd())
    if manifest_path is None:
        raise TestRunnerError("Project name is required when no base_manifest.yaml is found from the current directory.")
    return read_project(manifest_path)


def read_test_config(project: Project) -> TestConfig:
    manifest = read_manifest(project.manifest_path)
    if manifest.test is None:
        raise TestRunnerError(
            f"{project.manifest_path}: test is not configured. Add test.command or test.mise to base_manifest.yaml."
        )
    return manifest.test


def command_for_test(test_config: TestConfig) -> str | list[str]:
    if test_config.command is not None:
        return test_config.command
    if test_config.mise is not None:
        return ["mise", "run", test_config.mise]
    raise TestRunnerError("test is not configured.")


def format_command(command: str | list[str], shell: bool) -> str:
    if shell:
        return str(command)
    return shlex.join(command)


def run_test_command(command: str | list[str], cwd: Path, shell: bool) -> int:
    try:
        completed = subprocess.run(command, cwd=cwd, shell=shell, check=False)
    except FileNotFoundError as exc:
        executable = command[0] if isinstance(command, list) else str(command)
        raise TestRunnerError(f"Required test command '{executable}' was not found on PATH.") from exc
    return completed.returncode
