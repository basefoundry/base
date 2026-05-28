from __future__ import annotations

from dataclasses import dataclass
import os
import json
from pathlib import Path
from typing import Any

from .paths import base_state_root


SUPPORTED_IDES = {"vscode", "cursor"}


@dataclass(frozen=True)
class UserIdePreference:
    enabled: bool | None
    install: bool | None
    extra_extensions: tuple[str, ...]
    settings: dict[str, Any]


@dataclass(frozen=True)
class UserIdeConfig:
    enabled: bool | None
    preferences: dict[str, UserIdePreference]


@dataclass(frozen=True)
class UserConfig:
    raw: dict[str, Any]
    ide: UserIdeConfig


def user_config_path(home: Path | None = None) -> Path:
    return base_state_root(home) / "config.yaml"


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load base_cli configuration.") from exc

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Config file '{path}' contains invalid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file '{path}' must contain a YAML mapping.")
    return data


def load_user_config(home: Path | None = None) -> dict[str, Any]:
    return load_yaml_file(user_config_path(home))


def read_user_config(home: Path | None = None) -> UserConfig:
    raw = load_user_config(home)
    return UserConfig(raw=raw, ide=_read_user_ide_config(user_config_path(home), raw.get("ide")))


def _read_user_ide_config(path: Path, ide_data: Any) -> UserIdeConfig:
    if ide_data is None:
        return UserIdeConfig(enabled=None, preferences={})
    if not isinstance(ide_data, dict):
        raise ValueError(f"{path}: ide must be a mapping when provided.")

    allowed_keys = SUPPORTED_IDES | {"enabled"}
    unknown_keys = sorted(set(ide_data) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"{path}: unsupported ide keys: {', '.join(unknown_keys)}.")

    enabled = _optional_bool(path, "ide.enabled", ide_data.get("enabled"))
    preferences = {
        ide_name: _read_user_ide_preference(path, ide_name, ide_data.get(ide_name))
        for ide_name in sorted(SUPPORTED_IDES)
        if ide_name in ide_data
    }
    return UserIdeConfig(enabled=enabled, preferences=preferences)


def _read_user_ide_preference(path: Path, ide_name: str, preference_data: Any) -> UserIdePreference:
    if preference_data is None:
        preference_data = {}
    if not isinstance(preference_data, dict):
        raise ValueError(f"{path}: ide.{ide_name} must be a mapping when provided.")

    allowed_keys = {"enabled", "install", "extra_extensions", "settings"}
    unknown_keys = sorted(set(preference_data) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"{path}: ide.{ide_name} has unsupported keys: {', '.join(unknown_keys)}.")

    enabled = _optional_bool(path, f"ide.{ide_name}.enabled", preference_data.get("enabled"))
    install = _optional_bool(path, f"ide.{ide_name}.install", preference_data.get("install"))
    extra_extensions = _read_extra_extensions(path, ide_name, preference_data.get("extra_extensions", []))
    settings = _read_user_ide_settings(path, ide_name, preference_data.get("settings", {}))
    return UserIdePreference(
        enabled=enabled,
        install=install,
        extra_extensions=extra_extensions,
        settings=settings,
    )


def _optional_bool(path: Path, key: str, value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{path}: {key} must be a boolean when provided.")
    return value


def _read_extra_extensions(path: Path, ide_name: str, extensions_data: Any) -> tuple[str, ...]:
    if extensions_data is None:
        return ()
    if not isinstance(extensions_data, list):
        raise ValueError(f"{path}: ide.{ide_name}.extra_extensions must be a list when provided.")

    extensions: list[str] = []
    for index, extension in enumerate(extensions_data, start=1):
        if not isinstance(extension, str) or not extension.strip():
            raise ValueError(
                f"{path}: ide.{ide_name}.extra_extensions[{index}] must be a non-empty string."
            )
        extensions.append(extension.strip())
    return tuple(extensions)


def _read_user_ide_settings(path: Path, ide_name: str, settings_data: Any) -> dict[str, Any]:
    if settings_data is None:
        return {}
    if not isinstance(settings_data, dict):
        raise ValueError(f"{path}: ide.{ide_name}.settings must be a mapping when provided.")

    settings: dict[str, Any] = {}
    for key, value in settings_data.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{path}: ide.{ide_name}.settings keys must be non-empty strings.")
        try:
            json.dumps(value)
        except TypeError as exc:
            raise ValueError(f"{path}: ide.{ide_name}.settings.{key} must be JSON-serializable.") from exc
        settings[key] = value
    return settings


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(
    project_root: Path | None,
    explicit_config: Path | None,
    home: Path | None = None,
) -> dict[str, Any]:
    root = home or Path.home()
    config: dict[str, Any] = {}
    config = merge_dicts(config, load_user_config(root))
    if project_root is not None:
        config = merge_dicts(config, load_yaml_file(project_root / ".base" / "config.yaml"))
    if explicit_config is not None:
        config = merge_dicts(config, load_yaml_file(explicit_config))

    env_config: dict[str, Any] = {}
    if "BASE_CLI_ENVIRONMENT" in os.environ:
        env_config["environment"] = os.environ["BASE_CLI_ENVIRONMENT"]
    if "BASE_CLI_LOG_LEVEL" in os.environ:
        env_config["log_level"] = os.environ["BASE_CLI_LOG_LEVEL"]
    elif os.environ.get("LOG_DEBUG", "").lower() in ("1", "true"):
        env_config["log_level"] = "debug"
    if "BASE_CLI_KEEP_TEMP" in os.environ:
        env_config["keep_temp"] = os.environ["BASE_CLI_KEEP_TEMP"].lower() == "true"
    return merge_dicts(config, env_config)
