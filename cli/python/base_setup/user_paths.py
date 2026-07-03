from __future__ import annotations

import os
from pathlib import Path


def user_local_bin() -> Path:
    return Path.home() / ".local" / "bin"


def prepend_user_local_bin_to_path() -> None:
    bin_dir = str(user_local_bin())
    current_path = os.environ.get("PATH", "")
    path_entries = current_path.split(os.pathsep) if current_path else []
    if bin_dir not in path_entries:
        os.environ["PATH"] = os.pathsep.join([bin_dir, *path_entries]) if path_entries else bin_dir
