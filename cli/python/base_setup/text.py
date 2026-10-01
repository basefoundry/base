from __future__ import annotations

from pathlib import Path


def read_utf8_text(path: Path) -> str:
    """Read a repository-owned text file using Base's explicit UTF-8 contract."""
    return path.read_text(encoding="utf-8")
