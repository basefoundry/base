from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    yaml = None
    _yaml_import_error = exc
else:
    _yaml_import_error = None


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactRequest:
    artifact_type: str
    name: str
    version: str


@dataclass(frozen=True)
class BaseManifest:
    path: Path
    project_name: str
    artifacts: tuple[ArtifactRequest, ...]


def discover_manifest(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    while True:
        candidate = current / "base_manifest.yaml"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def read_manifest(path: Path) -> BaseManifest:
    if yaml is None:
        raise ManifestError(
            "PyYAML is required to read base_manifest.yaml. "
            "Run 'basectl setup' to install Base Python bootstrap dependencies."
        ) from _yaml_import_error

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping.")

    allowed_top_level = {"project", "artifacts"}
    unknown_top_level = sorted(set(data) - allowed_top_level)
    if unknown_top_level:
        raise ManifestError(f"{path}: unsupported top-level keys: {', '.join(unknown_top_level)}.")

    project_name = _read_project_name(path, data.get("project"))
    artifacts = _read_artifacts(path, data.get("artifacts", []))

    return BaseManifest(path=path, project_name=project_name, artifacts=tuple(artifacts))


def _read_project_name(path: Path, project_data: Any) -> str:
    if not isinstance(project_data, dict):
        raise ManifestError(f"{path}: project must be a mapping.")

    allowed_project_keys = {"name"}
    unknown_project_keys = sorted(set(project_data) - allowed_project_keys)
    if unknown_project_keys:
        raise ManifestError(f"{path}: unsupported project keys: {', '.join(unknown_project_keys)}.")

    project_name = project_data.get("name")
    if not isinstance(project_name, str) or not project_name:
        raise ManifestError(f"{path}: project.name is required.")
    return project_name


def _read_artifacts(path: Path, artifacts_data: Any) -> list[ArtifactRequest]:
    if artifacts_data is None:
        return []
    if not isinstance(artifacts_data, list):
        raise ManifestError(f"{path}: artifacts must be a list.")

    artifacts: list[ArtifactRequest] = []
    for index, artifact_data in enumerate(artifacts_data, start=1):
        artifacts.append(_read_artifact(path, artifact_data, index))
    return artifacts


def _read_artifact(path: Path, artifact_data: Any, index: int) -> ArtifactRequest:
    if not isinstance(artifact_data, dict):
        raise ManifestError(f"{path}: artifacts[{index}] must be a mapping.")

    allowed_artifact_keys = {"type", "name", "version"}
    unknown_artifact_keys = sorted(set(artifact_data) - allowed_artifact_keys)
    if unknown_artifact_keys:
        raise ManifestError(
            f"{path}: artifacts[{index}] has unsupported keys: {', '.join(unknown_artifact_keys)}."
        )

    missing = sorted(key for key in allowed_artifact_keys if not artifact_data.get(key))
    if missing:
        raise ManifestError(f"{path}: artifacts[{index}] is missing required keys: {', '.join(missing)}.")

    artifact_type = artifact_data["type"]
    name = artifact_data["name"]
    version = artifact_data["version"]
    if not all(isinstance(value, str) for value in (artifact_type, name, version)):
        raise ManifestError(f"{path}: artifacts[{index}] type, name, and version must be strings.")

    return ArtifactRequest(
        artifact_type=artifact_type,
        name=name,
        version=version,
    )
