from __future__ import annotations

import os
from pathlib import Path

from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest


def check_demo(manifest: BaseManifest) -> list[ArtifactCheck]:
    if manifest.demo is None:
        return []

    return [
        ArtifactCheck(
            name="demo declaration",
            ok=True,
            message=f"Project '{manifest.project_name}' declares demo.script '{manifest.demo.script}'.",
            fix="",
            finding_id="BASE-P060",
        ),
        check_demo_script(manifest),
    ]


def check_demo_script(manifest: BaseManifest) -> ArtifactCheck:
    try:
        demo_script = resolve_demo_script_path(manifest)
    except ArtifactError as exc:
        return ArtifactCheck(
            name="demo script",
            ok=False,
            message=str(exc),
            fix=f"Update demo.script in '{manifest.path}'.",
            finding_id="BASE-P061",
        )

    return ArtifactCheck(
        name="demo script",
        ok=True,
        message=f"Demo script '{demo_script}' exists and is executable.",
        fix="",
        finding_id="BASE-P061",
    )


def resolve_demo_script_path(manifest: BaseManifest) -> Path:
    if manifest.demo is None:
        raise ArtifactError(f"{manifest.path}: demo is not configured.")

    demo_script = Path(manifest.demo.script)
    if demo_script.is_absolute():
        raise ArtifactError(f"{manifest.path}: demo.script must be relative to the project root.")

    project_root = manifest.path.parent.resolve()
    demo_script_path = (project_root / demo_script).resolve()
    if not demo_script_path.is_relative_to(project_root):
        raise ArtifactError(f"{manifest.path}: demo.script must stay inside the project root.")
    if not demo_script_path.exists():
        raise ArtifactError(f"{manifest.path}: demo.script '{manifest.demo.script}' does not exist.")
    if not demo_script_path.is_file():
        raise ArtifactError(f"{manifest.path}: demo.script '{manifest.demo.script}' is not a file.")
    if not os.access(demo_script_path, os.X_OK):
        raise ArtifactError(f"{manifest.path}: demo.script '{manifest.demo.script}' is not executable.")
    return demo_script_path
