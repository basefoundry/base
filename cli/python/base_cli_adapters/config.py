from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from base_cli import ConfigurationError
from base_cli.config import load_yaml_file as load_cli_yaml_file
from base_setup.ide_schema import parse_ide_extensions
from base_setup.ide_schema import parse_ide_settings

from base_setup.ide_schema import SUPPORTED_IDES

from .paths import base_state_root


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
class UserWorkspaceConfig:
    root: Path | None
    manifest: Path | None = None
    manifest_source: str | None = None


@dataclass(frozen=True)
class UserGithubConfig:
    default_owner: str | None
    clone_protocol: str | None


@dataclass(frozen=True)
class UserConfig:
    raw: dict[str, Any]
    ide: UserIdeConfig
    workspace: UserWorkspaceConfig = UserWorkspaceConfig(root=None)
    github: UserGithubConfig = UserGithubConfig(default_owner=None, clone_protocol=None)


def user_config_path(home: Path | None = None) -> Path:
    return base_state_root(home) / "config.yaml"


def load_yaml_file(path: Path) -> dict[str, Any]:
    return load_cli_yaml_file(path)


def load_user_config(home: Path | None = None) -> dict[str, Any]:
    return load_yaml_file(user_config_path(home))


def read_user_config(
    home: Path | None = None,
    *,
    supported_ides: frozenset[str] | None = SUPPORTED_IDES,
) -> UserConfig:
    try:
        raw = load_user_config(home)
        path = user_config_path(home)
        return UserConfig(
            raw=raw,
            workspace=_read_user_workspace_config(path, raw.get("workspace")),
            github=_read_user_github_config(path, raw.get("github")),
            ide=_read_user_ide_config(path, raw.get("ide"), supported_ides=supported_ides),
        )
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc


def _validate_mapping_keys(path: Path, section: str, mapping: dict[Any, Any]) -> None:
    if any(not isinstance(key, str) or not key.strip() for key in mapping):
        raise ValueError(f"{path}: {section} keys must be non-empty strings.")


def _read_user_workspace_config(path: Path, workspace_data: Any) -> UserWorkspaceConfig:
    if workspace_data is None:
        return UserWorkspaceConfig(root=None)
    if not isinstance(workspace_data, dict):
        raise ValueError(f"{path}: workspace must be a mapping when provided.")

    _validate_mapping_keys(path, "workspace", workspace_data)
    allowed_keys = {"root", "manifest", "manifest_source"}
    unknown_keys = sorted(set(workspace_data) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"{path}: workspace has unsupported keys: {', '.join(unknown_keys)}.")

    return UserWorkspaceConfig(
        root=_optional_path(path, "workspace.root", workspace_data.get("root")),
        manifest=_optional_path(path, "workspace.manifest", workspace_data.get("manifest")),
        manifest_source=_optional_non_empty_string(
            path,
            "workspace.manifest_source",
            workspace_data.get("manifest_source"),
        ),
    )


def _read_user_github_config(path: Path, github_data: Any) -> UserGithubConfig:
    if github_data is None:
        return UserGithubConfig(default_owner=None, clone_protocol=None)
    if not isinstance(github_data, dict):
        raise ValueError(f"{path}: github must be a mapping when provided.")

    _validate_mapping_keys(path, "github", github_data)
    allowed_keys = {"default_owner", "clone_protocol"}
    unknown_keys = sorted(set(github_data) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"{path}: github has unsupported keys: {', '.join(unknown_keys)}.")

    return UserGithubConfig(
        default_owner=_optional_github_owner(path, github_data.get("default_owner")),
        clone_protocol=_optional_github_clone_protocol(path, github_data.get("clone_protocol")),
    )


def _optional_github_owner(path: Path, value: Any) -> str | None:
    owner = _optional_non_empty_string(path, "github.default_owner", value)
    if owner is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", owner):
        raise ValueError(
            f"{path}: github.default_owner must start with a letter or digit and contain only "
            "letters, digits, and dash."
        )
    return owner


def _optional_github_clone_protocol(path: Path, value: Any) -> str | None:
    protocol = _optional_non_empty_string(path, "github.clone_protocol", value)
    if protocol is None:
        return None
    if protocol not in {"ssh", "https"}:
        raise ValueError(f"{path}: github.clone_protocol must be 'ssh' or 'https'.")
    return protocol


def _optional_path(path: Path, key: str, value: Any) -> Path | None:
    if value is None:
        return None
    candidate = _optional_non_empty_string(path, key, value)
    if candidate is None:
        return None

    candidate_path = Path(candidate).expanduser()
    if not candidate_path.is_absolute():
        raise ValueError(f"{path}: {key} must be an absolute path or start with '~'.")
    return candidate_path.resolve(strict=False)


def _optional_non_empty_string(path: Path, key: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {key} must be a non-empty string when provided.")
    return value.strip()


def _read_user_ide_config(
    path: Path,
    ide_data: Any,
    *,
    supported_ides: frozenset[str] | None,
) -> UserIdeConfig:
    if ide_data is None:
        return UserIdeConfig(enabled=None, preferences={})
    if not isinstance(ide_data, dict):
        raise ValueError(f"{path}: ide must be a mapping when provided.")

    _validate_mapping_keys(path, "ide", ide_data)

    unknown_keys = sorted(set(ide_data) - supported_ides - {"enabled"}) if supported_ides is not None else []
    if unknown_keys:
        raise ValueError(f"{path}: unsupported ide keys: {', '.join(unknown_keys)}.")

    enabled = _optional_bool(path, "ide.enabled", ide_data.get("enabled"))
    preferences = {
        ide_name: _read_user_ide_preference(path, ide_name, ide_data.get(ide_name))
        for ide_name in sorted(set(ide_data) - {"enabled"})
        if ide_name in ide_data
    }
    return UserIdeConfig(enabled=enabled, preferences=preferences)


def _read_user_ide_preference(path: Path, ide_name: str, preference_data: Any) -> UserIdePreference:
    if preference_data is None:
        preference_data = {}
    if not isinstance(preference_data, dict):
        raise ValueError(f"{path}: ide.{ide_name} must be a mapping when provided.")

    _validate_mapping_keys(path, f"ide.{ide_name}", preference_data)
    allowed_keys = {"enabled", "install", "extra_extensions", "settings"}
    unknown_keys = sorted(set(preference_data) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"{path}: ide.{ide_name} has unsupported keys: {', '.join(unknown_keys)}.")

    return UserIdePreference(
        enabled=_optional_bool(path, f"ide.{ide_name}.enabled", preference_data.get("enabled")),
        install=_optional_bool(path, f"ide.{ide_name}.install", preference_data.get("install")),
        extra_extensions=parse_ide_extensions(
            f"{path}: ide.{ide_name}.extra_extensions",
            preference_data.get("extra_extensions", []),
        ),
        settings=parse_ide_settings(
            f"{path}: ide.{ide_name}.settings",
            preference_data.get("settings", {}),
        ),
    )


def _optional_bool(path: Path, key: str, value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{path}: {key} must be a boolean when provided.")
    return value


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
