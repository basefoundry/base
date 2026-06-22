from __future__ import annotations

from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path

from .errors import ArtifactError
from .manifest import yaml

BUILTIN_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "lib" / "base" / "artifact-registry.yaml"
SUPPORTED_MANAGERS = {"homebrew", "pip"}
SUPPORTED_TARGETS = {"project-venv", "system"}
SUPPORTED_VERSION_POLICIES = {"latest-only", "requested"}
SUPPORTED_CHECK_KINDS = {"homebrew_package", "python_import"}
ARTIFACT_ENTRY_KEYS = {
    "type",
    "name",
    "manager",
    "package",
    "target",
    "version_policy",
    "check",
    "metadata",
}
CHECK_ENTRY_KEYS = {"kind"}
REQUIRED_ARTIFACT_ENTRY_KEYS = {
    "type",
    "name",
    "manager",
    "package",
    "target",
    "version_policy",
    "check",
}


@dataclass(frozen=True)
class ArtifactDefinition:
    name: str
    artifact_type: str
    manager: str
    package: str
    target: str
    version_policy: str = ""
    check_kind: str = ""
    registry_source: str = ""


@lru_cache(maxsize=None)
def load_builtin_artifact_definitions() -> dict[tuple[str, str], ArtifactDefinition]:
    return load_artifact_definitions(BUILTIN_REGISTRY_PATH)


def load_artifact_definitions(path: Path) -> dict[tuple[str, str], ArtifactDefinition]:
    data = _read_registry(path)
    artifact_data = _registry_artifact_data(path, data)

    definitions: dict[tuple[str, str], ArtifactDefinition] = {}
    for index, entry in enumerate(artifact_data, start=1):
        definition = _parse_artifact_entry(path, index, entry)
        key = (definition.artifact_type, definition.name)
        if key in definitions:
            raise ArtifactError(
                f"Artifact registry '{path}' artifacts[{index}] declares "
                f"duplicate artifact definition: {definition.artifact_type}/{definition.name}."
            )
        definitions[key] = definition
    return definitions


def _read_registry(path: Path) -> dict[object, object]:
    if yaml is None:
        raise ArtifactError("PyYAML is required to read Base's built-in artifact registry.")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ArtifactError(f"Unable to read artifact registry '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ArtifactError(f"Artifact registry '{path}' is invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ArtifactError(f"Artifact registry '{path}' must be a YAML mapping.")
    return data


def _registry_artifact_data(path: Path, data: dict[object, object]) -> list[object]:
    if data.get("version") != 1:
        raise ArtifactError(f"Artifact registry '{path}' must declare version: 1.")

    artifact_data = data.get("artifacts")
    if not isinstance(artifact_data, list):
        raise ArtifactError(f"Artifact registry '{path}' must declare artifacts as a list.")
    return artifact_data


def _parse_artifact_entry(path: Path, index: int, entry: object) -> ArtifactDefinition:
    if not isinstance(entry, dict):
        raise ArtifactError(f"Artifact registry '{path}' artifacts[{index}] must be a mapping.")

    entry_path = f"Artifact registry '{path}' artifacts[{index}]"
    _validate_artifact_keys(entry_path, entry)
    check = _validate_check_entry(entry_path, entry["check"])

    artifact_type = _required_string(entry_path, entry, "type")
    name = _required_string(entry_path, entry, "name")
    manager = _required_string(entry_path, entry, "manager")
    package = _required_string(entry_path, entry, "package")
    target = _required_string(entry_path, entry, "target")
    version_policy = _required_string(entry_path, entry, "version_policy")
    check_kind = _required_string(f"{entry_path}.check", check, "kind")
    _validate_supported_values(entry_path, manager, target, version_policy, check_kind)

    return ArtifactDefinition(
        name=name,
        artifact_type=artifact_type,
        manager=manager,
        package=package,
        target=target,
        version_policy=version_policy,
        check_kind=check_kind,
        registry_source=str(path),
    )


def _validate_artifact_keys(context: str, entry: dict[object, object]) -> None:
    unknown_keys = sorted(set(entry) - ARTIFACT_ENTRY_KEYS)
    if unknown_keys:
        raise ArtifactError(f"{context} has unsupported keys: {', '.join(unknown_keys)}.")
    missing_keys = sorted(REQUIRED_ARTIFACT_ENTRY_KEYS - set(entry))
    if missing_keys:
        raise ArtifactError(f"{context} is missing required keys: {', '.join(missing_keys)}.")


def _validate_check_entry(context: str, check: object) -> dict[object, object]:
    check_path = f"{context}.check"
    if not isinstance(check, dict):
        raise ArtifactError(f"{check_path} must be a mapping.")
    unknown_keys = sorted(set(check) - CHECK_ENTRY_KEYS)
    if unknown_keys:
        raise ArtifactError(f"{check_path} has unsupported keys: {', '.join(unknown_keys)}.")
    if "kind" not in check:
        raise ArtifactError(f"{check_path} is missing required keys: kind.")
    return check


def _validate_supported_values(
    context: str,
    manager: str,
    target: str,
    version_policy: str,
    check_kind: str,
) -> None:
    if manager not in SUPPORTED_MANAGERS:
        raise ArtifactError(f"{context} has unsupported manager '{manager}'.")
    if target not in SUPPORTED_TARGETS:
        raise ArtifactError(f"{context} has unsupported target '{target}'.")
    if version_policy not in SUPPORTED_VERSION_POLICIES:
        raise ArtifactError(f"{context} has unsupported version_policy '{version_policy}'.")
    if check_kind not in SUPPORTED_CHECK_KINDS:
        raise ArtifactError(f"{context}.check has unsupported check kind '{check_kind}'.")


def _required_string(context: str, data: dict[object, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ArtifactError(f"{context}.{key} must be a non-empty string.")
    return value.strip()


def get_artifact_definition(artifact_type: str, name: str) -> ArtifactDefinition | None:
    definition = load_builtin_artifact_definitions().get((artifact_type, name))
    if definition is not None:
        return definition

    if artifact_type == "python-package":
        return ArtifactDefinition(
            name=name,
            artifact_type=artifact_type,
            manager="pip",
            package=name,
            target="project-venv",
            version_policy="requested",
            check_kind="python_import",
            registry_source="<python-package fallback>",
        )

    return None
