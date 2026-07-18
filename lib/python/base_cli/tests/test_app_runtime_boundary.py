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

    assert layout.owner_root == Path("/tmp/base-cache/base")
    assert layout.run_root == Path("/tmp/base-cache/base/runs/run-123")
    assert layout.state_dir == Path("/tmp/base-cache/base")
    assert layout.log_dir == Path("/tmp/base-cache/base/runs/run-123/logs")
    assert layout.cache_dir == Path("/tmp/base-cache/base/cache/components/demo")
    assert layout.temp_dir == Path("/tmp/base-cache/base/runs/run-123/tmp/demo/run-123")


def test_runtime_helpers_stay_out_of_public_api() -> None:
    assert "_runtime" not in base_cli.__all__
    assert "runtime_layout" not in base_cli.__all__


def test_runtime_layout_is_checkout_scoped_for_project_owner() -> None:
    runtime = importlib.import_module("base_cli._runtime")
    layout = runtime.runtime_layout(
        Path("/tmp/base-cache"),
        "native-cli",
        "run-123",
        owner="project",
        project_name="banyanlabs",
        project_root=Path("/work/banyanlabs"),
    )

    assert layout.owner_root.parent.parent == Path("/tmp/base-cache/projects")
    assert layout.owner_root.parent.name == "banyanlabs"
    assert layout.run_root == layout.owner_root / "runs" / "run-123"
    assert layout.log_dir == layout.run_root / "logs"


def test_runtime_layout_places_inherited_base_children_under_internal_logs() -> None:
    runtime = importlib.import_module("base_cli._runtime")
    parent = Path("/tmp/base-cache/base/runs/parent")
    layout = runtime.runtime_layout(
        Path("/tmp/base-cache"),
        "base_projects",
        "child",
        inherited_run_root=parent,
    )

    assert layout.run_root == parent
    assert layout.log_dir == parent / "logs" / "internal" / "base_projects"
    assert layout.temp_dir == parent / "tmp" / "base_projects" / "child"


def test_runtime_directory_helpers_are_split_from_app_module() -> None:
    app_source = Path(app.__file__).read_text(encoding="utf-8")

    assert "def runtime_layout" not in app_source
    assert "def create_runtime_directory" not in app_source
    assert "def prune_log_files" not in app_source
