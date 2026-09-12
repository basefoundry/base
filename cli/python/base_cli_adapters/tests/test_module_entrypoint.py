from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import base_cli
import pytest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "module_entrypoint.py"


@pytest.mark.parametrize("arguments", [["current"], ["manifest", "base_manifest.yaml"]])
def test_owned_module_loading_preserves_cwd_and_arguments(tmp_path, arguments):
    manifest = tmp_path / "base_manifest.yaml"
    manifest.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
    (tmp_path / "base_projects.py").write_text('raise RuntimeError("project module loaded")\n', encoding="utf-8")
    (tmp_path / "sitecustomize.py").write_text('raise RuntimeError("project startup loaded")\n', encoding="utf-8")
    environment = {
        **os.environ,
        "HOME": str(tmp_path),
        "BASE_CLI_RUNTIME_SOURCE_ROOT": str(Path(base_cli.__file__).resolve().parents[1]),
        "PYTHONPATH": str(tmp_path),
    }
    completed = subprocess.run(
        [sys.executable, "-I", str(ENTRYPOINT), "base_projects", *arguments],
        cwd=tmp_path, env=environment, text=True, capture_output=True, check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith(f"demo\t{tmp_path.resolve()}\t{manifest.resolve()}")
    assert "project startup loaded" not in completed.stderr


def test_entrypoint_refuses_nonisolated_python(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(ENTRYPOINT), "base_projects", "--help"],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert completed.returncode == 2
    assert "requires Python's -I option" in completed.stderr


@pytest.mark.parametrize("module", ["base_projects", "base_cli_adapters.run_index"])
def test_entrypoint_reports_incompatible_selected_provider(tmp_path, module):
    import shutil  # pylint: disable=import-outside-toplevel

    provider_root = tmp_path / "selected provider"
    shutil.copytree(Path(base_cli.__file__).resolve().parent, provider_root / "base_cli")
    with (provider_root / "base_cli/_runtime.py").open("a", encoding="utf-8") as stream:
        stream.write("\nrefresh_run_bundle_index = None\n")
    arguments = ["--help"] if module == "base_projects" else [str(tmp_path / "runs")]
    completed = subprocess.run(
        [sys.executable, "-I", str(ENTRYPOINT), module, *arguments],
        env={**os.environ, "BASE_CLI_SOURCE": "explicit", "BASE_CLI_RUNTIME_SOURCE_ROOT": str(provider_root)},
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert completed.returncode == 1
    assert "refresh_run_bundle_index" in completed.stderr
    assert str(provider_root) in completed.stderr
    assert "v0.4.3" in completed.stderr
    assert "BASE_CLI_SOURCE_DIR" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert not (tmp_path / "runs").exists()


@pytest.mark.skipif(os.name == "nt", reason="Bash provider routing is a POSIX launcher contract")
@pytest.mark.parametrize("source", ["explicit", "sibling", "pip"])
def test_resolved_provider_routes_run_the_same_preflight(tmp_path, source):
    runtime_home = tmp_path / "base"
    runtime_home.mkdir()
    provider_root = Path(base_cli.__file__).resolve().parents[1]
    environment = {key: value for key, value in os.environ.items() if key not in {
        "BASE_HOME", "BASE_CLI_SOURCE_DIR", "BASE_CLI_RUNTIME_SOURCE_ROOT", "BASE_CLI_SOURCE",
    }}
    if source == "explicit":
        environment["BASE_CLI_SOURCE_DIR"] = str(provider_root)
    elif source == "sibling":
        sibling_lib = tmp_path / "base-cli/lib"
        sibling_lib.mkdir(parents=True)
        (sibling_lib / "python").symlink_to(provider_root, target_is_directory=True)
    resolver = ENTRYPOINT.parents[3] / "lib/base/base_cli_runtime.sh"
    completed = subprocess.run(
        ["bash", "-c", 'source "$1"; base_cli_runtime_prepare "$2" || exit; exec "$3" -I "$4" --check-provider',
         "provider-check", str(resolver), str(runtime_home), sys.executable, str(ENTRYPOINT)],
        cwd=tmp_path, env=environment, text=True, capture_output=True, check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert f"Compatible base-cli {source} provider at " in completed.stdout
    if source == "pip":
        assert "site-packages" in completed.stdout
    elif source == "explicit":
        assert str(provider_root) in completed.stdout
    else:
        assert str(tmp_path / "base-cli/lib/python") in completed.stdout.replace("base/../", "")
