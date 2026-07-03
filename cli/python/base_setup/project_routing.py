from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .manifest import BaseManifest
from .project_environment import project_venv_dir_override
from .uv import manifest_uses_uv_project_manager


@dataclass(frozen=True)
class ProjectRoute:
    project: str
    project_root: Path
    manifest_path: Path
    project_venv_dir: Path
    uses_uv_manager: bool

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "project": self.project,
            "project_root": str(self.project_root),
            "manifest_path": str(self.manifest_path),
            "project_venv_dir": str(self.project_venv_dir),
            "uses_uv_manager": self.uses_uv_manager,
        }

    def to_tsv(self) -> str:
        uses_uv = "true" if self.uses_uv_manager else "false"
        return "\t".join(
            [
                self.project,
                str(self.project_root),
                str(self.manifest_path),
                str(self.project_venv_dir),
                uses_uv,
            ]
        )


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
        ),
        uses_uv_manager=uses_uv_manager,
    )


def project_venv_dir(project: str, project_root: Path | None = None, uses_uv_manager: bool = False) -> Path:
    override = project_venv_dir_override(project)
    if project != "base" and override is not None:
        return override
    if project != "base" and uses_uv_manager and project_root is not None:
        return project_root / ".venv"
    return Path.home() / ".base.d" / project / ".venv"


def route_to_text(route: ProjectRoute, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(route.to_json(), indent=2)
    if output_format == "text":
        return route.to_tsv()
    raise ValueError(f"Unsupported route output format '{output_format}'. Expected text or json.")
