from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import base_cli
from base_cli import app


def test_runtime_layout_names_base_cli_directories() -> None:
    assert importlib.util.find_spec("base_cli._runtime") is not None
    runtime = importlib.import_module("base_cli._runtime")
    layout = runtime.runtime_layout(Path("/tmp/base-cache"), "demo", "run-123")

    assert layout.state_dir == Path("/tmp/base-cache/cli/demo")
    assert layout.log_dir == Path("/tmp/base-cache/cli/demo/logs")
    assert layout.cache_dir == Path("/tmp/base-cache/cli/demo/cache")
    assert layout.temp_dir == Path("/tmp/base-cache/cli/demo/tmp/run-123")


def test_runtime_helpers_stay_out_of_public_api() -> None:
    assert "_runtime" not in base_cli.__all__
    assert "runtime_layout" not in base_cli.__all__


def test_runtime_directory_helpers_are_split_from_app_module() -> None:
    app_source = Path(app.__file__).read_text(encoding="utf-8")

    assert "def runtime_layout" not in app_source
    assert "def create_runtime_directory" not in app_source
    assert "def prune_log_files" not in app_source
