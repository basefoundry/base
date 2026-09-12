"""Static evidence and explicit execution consent for project inspection."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from .checks import ArtifactCheck
from .manifest_model import BaseManifest


def runtime_verification_command(manifest_path: Path) -> str:
    return shlex.join([
        "basectl", "check", "--manifest", str(manifest_path.resolve()), "--verify-project-runtime",
    ])


def unverified_runtime_check(
    manifest: BaseManifest, name: str, finding_id: str, *, details: dict[str, object] | None = None,
) -> ArtifactCheck:
    return ArtifactCheck(
        name=name,
        ok=False,
        status="warn",
        message=f"{name} is unverified; static inspection does not execute project runtimes or configuration.",
        fix=f"Review the project runtime and configuration, then run '{runtime_verification_command(manifest.path)}'.",
        finding_id=finding_id,
        details={**(details or {}), "verification": "unverified"},
    )


def executable_interpreter_present(python_bin: Path) -> bool:
    return python_bin.is_file() and os.access(python_bin, os.X_OK)


def project_venv_ready(venv_dir: Path) -> bool:
    python_bin = venv_dir / "bin" / "python"
    if not executable_interpreter_present(python_bin):
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


def project_environment_check(
    manifest: BaseManifest, venv_dir: Path, *, verify_project_runtime: bool = False,
) -> ArtifactCheck:
    uses_uv = manifest.python.manager == "uv"
    name = "uv project virtualenv" if uses_uv else "project_virtualenv"
    finding_id = "BASE-P154" if uses_uv else "BASE-P050"
    present = executable_interpreter_present(venv_dir / "bin" / "python")
    ready = present and (not verify_project_runtime or project_venv_ready(venv_dir))
    if not ready:
        return ArtifactCheck(
            name=name,
            ok=False,
            message=f"Project virtual environment is missing or incomplete at '{venv_dir}'.",
            fix=(
                f"Run 'uv sync' from '{manifest.path.parent}'." if uses_uv else
                f"Run 'basectl setup {manifest.project_name} --recreate-venv' "
                "to recreate the project virtual environment."
            ),
            finding_id=finding_id,
            status="warn" if uses_uv and not present else "error",
        )
    if not verify_project_runtime:
        return unverified_runtime_check(manifest, name, finding_id, details={"venv": str(venv_dir)})
    return ArtifactCheck(
        name=name,
        ok=True,
        message=f"Project virtual environment is ready at '{venv_dir}'.",
        fix="",
        finding_id=finding_id,
        details={"verification": "verified"},
    )
