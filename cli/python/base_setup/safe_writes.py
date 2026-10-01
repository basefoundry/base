from __future__ import annotations

from pathlib import Path


def ensure_safe_write_path(path: Path) -> None:
    """Reject symlinked targets and parent components before a write."""
    target = path.expanduser()
    if target.is_symlink():
        raise OSError(f"{target} is a symlink; refusing to write through it.")

    parent = target.parent
    while True:
        if parent.is_symlink():
            raise OSError(f"{parent} is a symlink; refusing to write through it.")
        if parent.exists() or parent == parent.parent:
            return
        parent = parent.parent
