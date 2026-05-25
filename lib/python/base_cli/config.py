from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load base_cli configuration.") from exc

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file '{path}' must contain a YAML mapping.")
    return data


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
    config = merge_dicts(config, load_yaml_file(root / ".base.d" / "config.yaml"))
    if project_root is not None:
        config = merge_dicts(config, load_yaml_file(project_root / ".base" / "config.yaml"))
    if explicit_config is not None:
        config = merge_dicts(config, load_yaml_file(explicit_config))

    env_config: dict[str, Any] = {}
    if "BASE_CLI_ENVIRONMENT" in os.environ:
        env_config["environment"] = os.environ["BASE_CLI_ENVIRONMENT"]
    if "BASE_CLI_LOG_LEVEL" in os.environ:
        env_config["log_level"] = os.environ["BASE_CLI_LOG_LEVEL"]
    if "BASE_CLI_KEEP_TEMP" in os.environ:
        env_config["keep_temp"] = os.environ["BASE_CLI_KEEP_TEMP"].lower() == "true"
    return merge_dicts(config, env_config)
