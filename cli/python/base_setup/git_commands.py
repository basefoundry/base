from __future__ import annotations

import subprocess
from pathlib import Path

from . import process


def run_git(
    project_root: Path,
    arguments: list[str],
    timeout_seconds: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return process.run_capture(
        ["git", "-C", str(project_root), *arguments],
        timeout_seconds=timeout_seconds,
    )
