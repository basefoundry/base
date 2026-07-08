from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from base_cli.paths import base_state_root
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_setup.manifest_model import BaseManifest
from base_setup.uv import manifest_uses_uv_project_manager


@dataclass(frozen=True)
class ProjectLastCheck:
    checked_at: str
    status: str


def project_venv_dir(manifest: BaseManifest) -> Path:
    if manifest_uses_uv_project_manager(manifest):
        return manifest.path.parent / ".venv"
    return base_state_root() / manifest.project_name / ".venv"


def project_venv_ready(venv_dir: Path) -> bool:
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.is_file():
        return False
    try:
        completed = subprocess.run(
            [str(python_bin), "-c", "import sys"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def project_last_check(project_name: str) -> ProjectLastCheck | None:
    record_path = base_state_root() / project_name / "checks" / "last.json"
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("schema_version") != 1:
        return None
    if payload.get("project") != project_name:
        return None

    checked_at = payload.get("checked_at")
    status = payload.get("status")
    if not isinstance(checked_at, str) or not isinstance(status, str):
        return None
    return ProjectLastCheck(checked_at=checked_at, status=status)


def workspace_repo_check_details(repo: WorkspaceManifestRepo, root: Path, present: bool) -> dict[str, Any]:
    details: dict[str, Any] = {
        "repository": repo.name,
        "path": str(root),
        "required": repo.required,
        "present": present,
    }
    if repo.url is not None:
        details["url"] = repo.url
    if repo.default_branch is not None:
        details["default_branch"] = repo.default_branch
    return details


def missing_repo_message(repo: WorkspaceManifestRepo, root: Path) -> str:
    requirement = "Required" if repo.required else "Optional"
    return f"{requirement} repository '{repo.name}' is missing at '{root}'."


def missing_repo_fix(repo: WorkspaceManifestRepo, root: Path) -> str:
    if repo.url:
        return f"Clone '{repo.url}' into '{root}'."
    return f"Create or clone repository '{repo.name}' into '{root}'."


def most_severe_status(*statuses: str) -> str:
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"
