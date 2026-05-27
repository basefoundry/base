from __future__ import annotations

import os
import time
import uuid
from pathlib import Path


def base_state_root(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".base.d"


def base_cache_root(home: Path | None = None) -> Path:
    value = os.environ.get("BASE_CACHE_DIR")
    if value:
        return Path(value).expanduser()
    return (home or Path.home()) / ".cache" / "base"


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
