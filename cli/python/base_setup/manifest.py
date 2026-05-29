from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
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
    bootstrap: bool = False


@dataclass(frozen=True)
class IdeConfig:
    install: bool
    extensions: tuple[str, ...]
    settings: dict[str, Any]


@dataclass(frozen=True)
class TestConfig:
    command: str


@dataclass(frozen=True)
class BaseManifest:
    path: Path
    project_name: str
    brewfile: str | None
    artifacts: tuple[ArtifactRequest, ...]
    ide: dict[str, IdeConfig] = field(default_factory=dict)
    mise: str | None = None
    test: TestConfig | None = None


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

    allowed_top_level = {"project", "brewfile", "mise", "ide", "artifacts", "test"}
    unknown_top_level = sorted(set(data) - allowed_top_level)
    if unknown_top_level:
        raise ManifestError(f"{path}: unsupported top-level keys: {', '.join(unknown_top_level)}.")

    project_name = _read_project_name(path, data.get("project"))
    brewfile = _read_brewfile(path, data.get("brewfile"))
    mise = _read_mise(path, data.get("mise"))
    ide = _read_ide(path, data.get("ide"))
    test = _read_test(path, data.get("test"))
    artifacts = _read_artifacts(path, data.get("artifacts", []))

    return BaseManifest(
        path=path,
        project_name=project_name,
        brewfile=brewfile,
        artifacts=tuple(artifacts),
        ide=ide,
        mise=mise,
        test=test,
    )


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


def _read_brewfile(path: Path, brewfile_data: Any) -> str | None:
    if brewfile_data is None:
        return None
    if not isinstance(brewfile_data, str) or not brewfile_data.strip():
        raise ManifestError(f"{path}: brewfile must be a non-empty string when provided.")
    return brewfile_data.strip()


def _read_mise(path: Path, mise_data: Any) -> str | None:
    if mise_data is None:
        return None
    if not isinstance(mise_data, str) or not mise_data.strip():
        raise ManifestError(f"{path}: mise must be a non-empty string when provided.")
    return mise_data.strip()


def _read_ide(path: Path, ide_data: Any) -> dict[str, IdeConfig]:
    if ide_data is None:
        return {}
    if not isinstance(ide_data, dict):
        raise ManifestError(f"{path}: ide must be a mapping when provided.")

    allowed_ide_names = {"vscode", "cursor"}
    unknown_ide_names = sorted(set(ide_data) - allowed_ide_names)
    if unknown_ide_names:
        raise ManifestError(f"{path}: unsupported IDE names: {', '.join(unknown_ide_names)}.")

    ide: dict[str, IdeConfig] = {}
    for ide_name, config_data in ide_data.items():
        ide[ide_name] = _read_ide_config(path, ide_name, config_data)
    return ide


def _read_test(path: Path, test_data: Any) -> TestConfig | None:
    if test_data is None:
        return None
    if not isinstance(test_data, dict):
        raise ManifestError(f"{path}: test must be a mapping when provided.")

    allowed_keys = {"command"}
    unknown_keys = sorted(set(test_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: test has unsupported keys: {', '.join(unknown_keys)}.")

    command = test_data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ManifestError(f"{path}: test.command must be a non-empty string when provided.")
    return TestConfig(command=command.strip())


def _read_ide_config(path: Path, ide_name: str, config_data: Any) -> IdeConfig:
    if config_data is None:
        config_data = {}
    if not isinstance(config_data, dict):
        raise ManifestError(f"{path}: ide.{ide_name} must be a mapping.")

    allowed_keys = {"install", "extensions", "settings"}
    unknown_keys = sorted(set(config_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: ide.{ide_name} has unsupported keys: {', '.join(unknown_keys)}.")

    install = config_data.get("install", False)
    if not isinstance(install, bool):
        raise ManifestError(f"{path}: ide.{ide_name}.install must be a boolean when provided.")

    extensions = _read_ide_extensions(path, ide_name, config_data.get("extensions", []))
    settings = _read_ide_settings(path, ide_name, config_data.get("settings", {}))

    return IdeConfig(install=install, extensions=extensions, settings=settings)


def _read_ide_extensions(path: Path, ide_name: str, extensions_data: Any) -> tuple[str, ...]:
    if extensions_data is None:
        return ()
    if not isinstance(extensions_data, list):
        raise ManifestError(f"{path}: ide.{ide_name}.extensions must be a list when provided.")

    extensions: list[str] = []
    for index, extension in enumerate(extensions_data, start=1):
        if not isinstance(extension, str) or not extension.strip():
            raise ManifestError(
                f"{path}: ide.{ide_name}.extensions[{index}] must be a non-empty string."
            )
        extensions.append(extension.strip())
    return tuple(extensions)


def _read_ide_settings(path: Path, ide_name: str, settings_data: Any) -> dict[str, Any]:
    if settings_data is None:
        return {}
    if not isinstance(settings_data, dict):
        raise ManifestError(f"{path}: ide.{ide_name}.settings must be a mapping when provided.")

    settings: dict[str, Any] = {}
    for key, value in settings_data.items():
        if not isinstance(key, str) or not key:
            raise ManifestError(f"{path}: ide.{ide_name}.settings keys must be non-empty strings.")
        if value == "auto" and key != "python.defaultInterpreterPath":
            raise ManifestError(
                f"{path}: ide.{ide_name}.settings.{key} does not support the special value 'auto'."
            )
        try:
            json.dumps(value)
        except TypeError as exc:
            raise ManifestError(
                f"{path}: ide.{ide_name}.settings.{key} must be JSON-serializable."
            ) from exc
        settings[key] = value
    return settings


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

    required_artifact_keys = {"type", "name", "version"}
    allowed_artifact_keys = required_artifact_keys | {"bootstrap"}
    unknown_artifact_keys = sorted(set(artifact_data) - allowed_artifact_keys)
    if unknown_artifact_keys:
        raise ManifestError(
            f"{path}: artifacts[{index}] has unsupported keys: {', '.join(unknown_artifact_keys)}."
        )

    missing = sorted(key for key in required_artifact_keys if not artifact_data.get(key))
    if missing:
        raise ManifestError(f"{path}: artifacts[{index}] is missing required keys: {', '.join(missing)}.")

    artifact_type = artifact_data["type"]
    name = artifact_data["name"]
    version = artifact_data["version"]
    if not all(isinstance(value, str) for value in (artifact_type, name, version)):
        raise ManifestError(f"{path}: artifacts[{index}] type, name, and version must be strings.")
    bootstrap = artifact_data.get("bootstrap", False)
    if not isinstance(bootstrap, bool):
        raise ManifestError(f"{path}: artifacts[{index}] bootstrap must be a boolean when provided.")

    return ArtifactRequest(
        artifact_type=artifact_type,
        name=name,
        version=version,
        bootstrap=bootstrap,
    )
