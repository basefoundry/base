from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from base_cli.command_protocol import dumps_record

from .manifest import BaseManifest
from .project_environment import project_venv_dir_override
from .uv import manifest_uses_uv_project_manager

PROJECT_VENV_LOCATION_EXTERNAL = "external"
PROJECT_VENV_LOCATION_PROJECT = "project"


@dataclass(frozen=True)
class ProjectRoute:
    project: str
    project_root: Path
    manifest_path: Path
    project_venv_dir: Path
    uses_uv_manager: bool
    requires_project_python: bool

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "project": self.project,
            "project_root": str(self.project_root),
            "manifest_path": str(self.manifest_path),
            "project_venv_dir": str(self.project_venv_dir),
            "uses_uv_manager": self.uses_uv_manager,
            "requires_project_python": self.requires_project_python,
        }

    def to_tsv(self) -> str:
        uses_uv = "true" if self.uses_uv_manager else "false"
        requires_python = "true" if self.requires_project_python else "false"
        return "\t".join(
            [
                self.project,
                str(self.project_root),
                str(self.manifest_path),
                str(self.project_venv_dir),
                uses_uv,
                requires_python,
            ]
        )

    def to_command_record(self) -> dict[str, str | bool]:
        return {
            "project_name": self.project,
            "project_root": str(self.project_root),
            "manifest_path": str(self.manifest_path),
            "project_venv_dir": str(self.project_venv_dir),
            "uses_uv_manager": self.uses_uv_manager,
            "requires_project_python": self.requires_project_python,
            "manifest_command_trust_required": False,
        }


def route_for_manifest(manifest: BaseManifest) -> ProjectRoute:
    project_root = manifest.path.parent.resolve()
    manifest_path = manifest.path.resolve()
    uses_uv_manager = manifest_uses_uv_project_manager(manifest)
    return ProjectRoute(
        project=manifest.project_name,
        project_root=project_root,
        manifest_path=manifest_path,
        project_venv_dir=project_venv_dir(
            manifest.project_name,
            project_root=project_root,
            uses_uv_manager=uses_uv_manager,
            venv_location=manifest.python.venv_location,
        ),
        uses_uv_manager=uses_uv_manager,
        requires_project_python=manifest_requires_project_python(manifest),
    )


def manifest_requires_project_python(manifest: BaseManifest) -> bool:
    """Return whether the manifest explicitly owns a project Python runtime."""

    if manifest.python_declared:
        return True
    return any(artifact.artifact_type == "python-package" for artifact in manifest.artifacts)


def project_venv_dir(
    project: str,
    project_root: Path | None = None,
    uses_uv_manager: bool = False,
    venv_location: str = PROJECT_VENV_LOCATION_PROJECT,
) -> Path:
    override = project_venv_dir_override(project)
    if project != "base" and override is not None:
        return override
    if project != "base" and project_root is not None and (
        uses_uv_manager or venv_location == PROJECT_VENV_LOCATION_PROJECT
    ):
        return project_root / ".venv"
    return Path.home() / ".base.d" / project / ".venv"


def route_to_text(route: ProjectRoute, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(route.to_json(), indent=2)
    if output_format == "text":
        return route.to_tsv()
    if output_format == "command-protocol":
        return dumps_record("project-setup-route", route.to_command_record())
    raise ValueError(f"Unsupported route output format '{output_format}'. Expected text, json, or command-protocol.")
