from __future__ import annotations

import os
from pathlib import Path


def project_venv_dir_override(project: str) -> Path | None:
    override = os.environ.get("BASE_PROJECT_VENV_DIR")
    if not override:
        return None

    active_project = os.environ.get("BASE_PROJECT")
    if active_project and active_project != project:
        return None

    return Path(override).expanduser()
