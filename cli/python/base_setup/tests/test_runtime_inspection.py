from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from base_projects import workspace_report_common
from base_projects import workspace_statuses
from base_setup import runtime_inspection
from base_setup import uv


def test_project_interpreter_static_checks_share_one_nonexecuting_probe(tmp_path: Path) -> None:
    python_bin = tmp_path / "venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_bin.chmod(0o755)

    with mock.patch(
        "base_setup.runtime_inspection.process.run_check",
        side_effect=AssertionError("static interpreter inspection must not execute it"),
    ) as run:
        assert runtime_inspection.executable_interpreter_present(python_bin)
        assert workspace_statuses.executable_interpreter_present(python_bin)
        assert uv.uv_project_venv_ready(python_bin.parent.parent)
        run.assert_not_called()

    assert workspace_report_common.project_venv_ready is runtime_inspection.project_venv_ready


@pytest.mark.parametrize(
    "failure",
    [
        OSError("cannot execute interpreter"),
        subprocess.TimeoutExpired(["python"], timeout=5),
    ],
)
def test_project_venv_probe_returns_false_for_execution_failures(
    tmp_path: Path, failure: Exception
) -> None:
    python_bin = tmp_path / "venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_bin.chmod(0o755)

    with mock.patch("base_setup.runtime_inspection.process.run_check", side_effect=failure) as run:
        assert not runtime_inspection.project_venv_ready(python_bin.parent.parent)

    assert run.call_args.kwargs["timeout_seconds"] == 5


def test_project_venv_probe_returns_false_for_nonzero_interpreter(tmp_path: Path) -> None:
    python_bin = tmp_path / "venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    python_bin.chmod(0o755)
    with mock.patch("base_setup.runtime_inspection.process.run_check", return_value=False):
        assert not runtime_inspection.project_venv_ready(python_bin.parent.parent)


def test_static_interpreter_check_fails_closed_on_filesystem_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python_bin = tmp_path / "venv" / "bin" / "python"

    def denied(_path: Path) -> bool:
        raise OSError("denied")

    monkeypatch.setattr(Path, "is_file", denied)

    assert not runtime_inspection.executable_interpreter_present(python_bin)
