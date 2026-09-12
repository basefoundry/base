from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from base_projects import engine
from base_setup import engine as setup_engine
from base_trust.trust_store import ManifestCommandTrustStore, compute_trust_identity_for_manifest


@pytest.fixture(name="runtime_project")
def runtime_project_fixture(tmp_path, monkeypatch):
    home = tmp_path / "home"
    base = tmp_path / "base"
    workspace = tmp_path / "workspace"
    project = workspace / "demo"
    home.mkdir()
    defaults = base / "lib" / "base" / "default_manifest.yaml"
    defaults.parent.mkdir(parents=True)
    defaults.write_text("project:\n  name: defaults\nartifacts: []\n", encoding="utf-8")
    project.mkdir(parents=True)
    manifest = project / "base_manifest.yaml"
    manifest.write_text(
        "project:\n  name: demo\npython: {}\ntest:\n  command: 'true'\n"
        "  requirements: requirements.txt\nartifacts: []\n",
        encoding="utf-8",
    )
    (project / "requirements.txt").write_text("pip\n", encoding="utf-8")
    workspace_manifest = tmp_path / "workspace.yaml"
    workspace_manifest.write_text(
        "schema_version: 1\nworkspace:\n  name: demo\nrepos:\n  - name: demo\n", encoding="utf-8",
    )
    python_bin = project / ".venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    marker = project / "runtime-probed"
    python_bin.write_text(
        '#!/bin/sh\nprintf probe >> "$(dirname "$0")/../../runtime-probed"\nprintf "3.13\\n"\n',
        encoding="utf-8",
    )
    python_bin.chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("BASE_HOME", str(base))
    for variable in ("BASE_PROJECT", "BASE_PROJECT_ROOT", "BASE_PROJECT_MANIFEST", "BASE_PROJECT_VENV_DIR"):
        monkeypatch.delenv(variable, raising=False)
    return workspace, workspace_manifest, manifest, marker


def invoke(main, arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(arguments)
    return result, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize("command", ["status", "check", "doctor", "onboarding"])
@pytest.mark.parametrize("approved", [False, True])
def test_workspace_inspection_does_not_execute_runtime(runtime_project, command, approved):
    workspace, workspace_manifest, manifest, marker = runtime_project
    if approved:
        ManifestCommandTrustStore().allow(compute_trust_identity_for_manifest(manifest), base_version="fixture")

    result, stdout, _stderr = invoke(engine.main, [
        command, "--workspace", str(workspace), "--manifest", str(workspace_manifest), "--format", "json", "--yes",
    ])

    assert result == 0
    assert not marker.exists()
    document = json.loads(stdout)
    assert "unverified" in json.dumps(document) or "needs_verification" in json.dumps(document)


@pytest.mark.parametrize("action", ["check", "doctor"])
def test_project_inspection_does_not_execute_runtime(runtime_project, action):
    _workspace, _workspace_manifest, manifest, marker = runtime_project
    result, stdout, _stderr = invoke(setup_engine.main, [
        "--action", action, "--manifest", str(manifest), "--format", "json",
    ])

    assert result == 0
    assert not marker.exists()
    assert "unverified" in stdout


def test_test_preflight_requires_approval_before_runtime_probe(runtime_project):
    workspace, _workspace_manifest, _manifest, marker = runtime_project
    result, _stdout, stderr = invoke(engine.main, [
        "test-command", "demo", "--workspace", str(workspace), "--test-preflight",
    ])

    assert result == 1
    assert not marker.exists()
    assert "trust" in stderr.lower()


@pytest.mark.parametrize("command", ["check", "doctor"])
def test_workspace_runtime_verification_requires_explicit_option(runtime_project, command):
    workspace, workspace_manifest, _manifest, marker = runtime_project
    result, stdout, _stderr = invoke(engine.main, [
        command, "--workspace", str(workspace), "--manifest", str(workspace_manifest), "--format", "json",
        "--verify-project-runtime",
    ])

    assert result == 0
    assert marker.is_file()
    assert "unverified" not in stdout


@pytest.mark.parametrize("action", ["check", "doctor"])
def test_project_runtime_verification_requires_explicit_option(runtime_project, action):
    _workspace, _workspace_manifest, manifest, marker = runtime_project
    result, stdout, _stderr = invoke(setup_engine.main, [
        "--action", action, "--manifest", str(manifest), "--format", "json", "--verify-project-runtime",
    ])

    assert result == 0
    assert marker.is_file()
    assert "unverified" not in stdout


def test_approved_test_preflight_can_verify_runtime(runtime_project):
    workspace, _workspace_manifest, manifest, marker = runtime_project
    ManifestCommandTrustStore().allow(compute_trust_identity_for_manifest(manifest), base_version="fixture")
    result, _stdout, _stderr = invoke(engine.main, [
        "test-command", "demo", "--workspace", str(workspace), "--test-preflight",
    ])

    assert result == 0
    assert marker.is_file()


def test_status_rejects_runtime_execution_option(runtime_project):
    workspace, _workspace_manifest, _manifest, marker = runtime_project
    result, _stdout, stderr = invoke(engine.main, [
        "status", "--workspace", str(workspace), "--verify-project-runtime",
    ])

    assert result == 2
    assert not marker.exists()
    assert "only supported for workspace check and doctor" in stderr


@pytest.mark.parametrize("action", ["check", "doctor"])
def test_explicit_verification_reports_broken_runtime(runtime_project, action):
    _workspace, _workspace_manifest, manifest, marker = runtime_project
    python_bin = manifest.parent / ".venv" / "bin" / "python"
    python_bin.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")

    result, stdout, _stderr = invoke(setup_engine.main, [
        "--action", action, "--manifest", str(manifest), "--format", "json", "--verify-project-runtime",
    ])

    assert result == 1
    assert "BASE-P050" in stdout
    assert "missing or incomplete" in stdout
    assert not marker.exists()


@pytest.mark.parametrize("delegate", ["brew", "mise", "uv"])
def test_static_inspection_does_not_execute_project_tool_configuration(runtime_project, monkeypatch, delegate):
    _workspace, _workspace_manifest, manifest, marker = runtime_project
    project = manifest.parent
    tools = project / "tools"
    tools.mkdir()
    tool = tools / delegate
    tool.write_text(f'#!/bin/sh\nprintf probe >> "{marker}"\nexit 0\n', encoding="utf-8")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(tools), prepend=":")
    monkeypatch.setenv("BASE_PLATFORM", "macos")
    if delegate == "brew":
        (project / "Brewfile").write_text('brew "git"\n', encoding="utf-8")
        declaration = "brewfile: Brewfile\npython: {}\n"
        finding = "BASE-P012"
    elif delegate == "mise":
        (project / ".mise.toml").write_text('[tools]\npython = "3.13"\n', encoding="utf-8")
        declaration = "mise: .mise.toml\npython: {}\n"
        finding = "BASE-P022"
    else:
        (project / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")
        (project / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        declaration = "python:\n  manager: uv\n"
        finding = "BASE-P155"
    manifest.write_text(f"project:\n  name: demo\n{declaration}artifacts: []\n", encoding="utf-8")

    result, stdout, _stderr = invoke(setup_engine.main, [
        "--action", "check", "--manifest", str(manifest), "--format", "json",
    ])

    assert result == 0, (stdout, _stderr)
    assert not marker.exists()
    assert finding in stdout
    assert "unverified" in stdout
