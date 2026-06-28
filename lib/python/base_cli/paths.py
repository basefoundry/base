from __future__ import annotations

import contextlib
import contextvars
import os
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

_WORKING_DIRECTORY_OVERRIDE: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "base_cli_working_directory_override",
    default=None,
)


def base_state_root(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".base.d"


def base_cache_root(home: Path | None = None) -> Path:
    value = os.environ.get("BASE_CACHE_DIR")
    if value:
        return Path(value).expanduser()
    root = home or Path.home()
    if sys.platform == "darwin":
        return root / "Library" / "Caches" / "base"
    return root / ".cache" / "base"


def current_working_dir() -> Path:
    return _WORKING_DIRECTORY_OVERRIDE.get() or Path.cwd()


@contextlib.contextmanager
def use_working_dir(path: Path | None) -> Iterator[None]:
    if path is None:
        yield
        return

    token = _WORKING_DIRECTORY_OVERRIDE.set(path.expanduser().resolve())
    try:
        yield
    finally:
        _WORKING_DIRECTORY_OVERRIDE.reset(token)


def make_run_id() -> str:
    timestamp = time.strftime("%Y%m%dT%H%M%S")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def normalize_cli_name(name: str) -> str:
    stem = Path(name).name
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    return stem.replace(" ", "-")


def discover_manifest(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    while True:
        candidate = current / "base_manifest.yaml"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def resolve_base_home() -> Path | None:
    value = os.environ.get("BASE_HOME")
    if not value:
        return None
    return Path(value).expanduser().resolve()
