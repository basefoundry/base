from __future__ import annotations

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


MANIFEST_TOP_LEVEL_KEYS = {
    "schema_version",
    "project",
    "brewfile",
    "mise",
    "ide",
    "artifacts",
    "test",
    "health",
    "commands",
    "activate",
    "python",
    "github",
    "demo",
    "build",
    "release",
}


def read_manifest_mapping(path: Path) -> dict[Any, Any]:
    if yaml is None:
        raise ManifestError(
            "PyYAML is required to read base_manifest.yaml. "
            "Run 'basectl setup' to install Base Python bootstrap dependencies."
        ) from _yaml_import_error

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeError as exc:
        raise ManifestError(f"{path}: manifest must use UTF-8 encoding: {exc}") from exc
    except OSError as exc:
        raise ManifestError(f"{path}: unable to read manifest: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping.")

    validate_mapping_keys(data, path)

    unknown_top_level = sorted(set(data) - MANIFEST_TOP_LEVEL_KEYS)
    if unknown_top_level:
        raise ManifestError(f"{path}: unsupported top-level keys: {', '.join(unknown_top_level)}.")

    return data


def validate_mapping_keys(data: Any, path: Path) -> None:
    """Validate nested keys before schema readers sort or join them.

    YAML aliases can share or cycle through containers. Visit each container
    once so key validation neither recurses forever nor repeats shared work.
    """
    pending = [(data, "manifest")]
    visited: set[int] = set()
    while pending:
        value, location = pending.pop()
        if not isinstance(value, (dict, list)) or id(value) in visited:
            continue
        visited.add(id(value))
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise ManifestError(
                        f"{path}: {location} mapping keys must be strings; got {type(key).__name__}."
                    )
                pending.append((child, f"{location}.{key}"))
        else:
            pending.extend((child, f"{location}[{index}]") for index, child in enumerate(value))
