from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

from base_setup import artifacts


def test_python_artifact_installed_passes_timeout_to_pip_show(tmp_path: Path) -> None:
    python_bin = tmp_path / "python"
    python_bin.write_text("", encoding="utf-8")
    completed = subprocess.CompletedProcess(
        [str(python_bin), "-m", "pip", "show", "requests"],
        0,
        stdout="Name: requests\nVersion: 2.32.4\n",
        stderr="",
    )

    with mock.patch("base_setup.python_artifacts.subprocess.run", return_value=completed) as run:
        assert artifacts.python_artifact_installed(python_bin, "requests", "2.32.4")

    assert run.call_args.kwargs["timeout"] == artifacts.PYTHON_ARTIFACT_PROBE_TIMEOUT_SECONDS


def test_python_artifact_installed_returns_false_on_timeout(tmp_path: Path) -> None:
    python_bin = tmp_path / "python"
    python_bin.write_text("", encoding="utf-8")
    command = [str(python_bin), "-m", "pip", "show", "requests"]

    with mock.patch(
        "base_setup.python_artifacts.subprocess.run",
        side_effect=subprocess.TimeoutExpired(command, timeout=10),
    ):
        assert not artifacts.python_artifact_installed(python_bin, "requests", "latest")
