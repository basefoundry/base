from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class IdeDefinition:
    name: str
    label: str
    cli: str
    cask: str
    settings_app_dir: str


IDE_DEFINITIONS = {
    "vscode": IdeDefinition(
        name="vscode",
        label="VS Code",
        cli="code",
        cask="visual-studio-code",
        settings_app_dir="Code",
    ),
    "cursor": IdeDefinition(
        name="cursor",
        label="Cursor",
        cli="cursor",
        cask="cursor",
        settings_app_dir="Cursor",
    ),
}

SUPPORTED_IDES = frozenset(IDE_DEFINITIONS)
PROJECT_AUTO_SETTING_KEYS = frozenset({"python.defaultInterpreterPath"})


def parse_ide_extensions(context: str, extensions_data: Any) -> tuple[str, ...]:
    if extensions_data is None:
        return ()
    if not isinstance(extensions_data, list):
        raise ValueError(f"{context} must be a list when provided.")

    extensions: list[str] = []
    for index, extension in enumerate(extensions_data, start=1):
        if not isinstance(extension, str) or not extension.strip():
            raise ValueError(f"{context}[{index}] must be a non-empty string.")
        extensions.append(extension.strip())
    return tuple(extensions)


def parse_ide_settings(
    context: str,
    settings_data: Any,
    *,
    auto_setting_keys: frozenset[str] | None = None,
) -> dict[str, Any]:
    if settings_data is None:
        return {}
    if not isinstance(settings_data, dict):
        raise ValueError(f"{context} must be a mapping when provided.")

    settings: dict[str, Any] = {}
    for key, value in settings_data.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{context} keys must be non-empty strings.")
        if auto_setting_keys is not None and value == "auto" and key not in auto_setting_keys:
            raise ValueError(f"{context}.{key} does not support the special value 'auto'.")
        try:
            json.dumps(value)
        except TypeError as exc:
            raise ValueError(f"{context}.{key} must be JSON-serializable.") from exc
        settings[key] = value
    return settings
