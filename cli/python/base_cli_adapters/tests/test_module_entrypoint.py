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
