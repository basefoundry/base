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
    except OSError as exc:
        raise ManifestError(f"{path}: unable to read manifest: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping.")

    unknown_top_level = sorted(set(data) - MANIFEST_TOP_LEVEL_KEYS)
    if unknown_top_level:
        raise ManifestError(f"{path}: unsupported top-level keys: {', '.join(unknown_top_level)}.")

    return data
