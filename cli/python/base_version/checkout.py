"""Small, dependency-free checks for selecting a Git checkout root."""
from __future__ import annotations

import stat
from pathlib import Path


def git_checkout_marker(root: Path) -> bool | None:
    """Return whether an existing directory has a readable ``.git`` entry.

    ``None`` means that the path is not an accessible directory. Callers can
    then let their normal Git probe report the precise per-repository error.
    """
    try:
        root_stat = root.stat()
    except OSError:
        return None
    if not stat.S_ISDIR(root_stat.st_mode):
        return None

    try:
        (root / ".git").stat()
    except FileNotFoundError:
        return False
    except OSError:
        return None
    return True
