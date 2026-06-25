from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ProjectConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectConfig:
    areas: tuple[str, ...] = ()
    initiatives: tuple[str, ...] = ()
    issue_defaults: dict[str, str] = field(default_factory=dict)


ALLOWED_PROJECT_KEYS = {"areas", "initiatives", "issue_defaults"}
ALLOWED_DEFAULT_KEYS = {"status", "priority", "size", "area", "initiative", "assignee"}


def read_project_config(path: Path) -> ProjectConfig:
    data = read_yaml_mapping(path)
    if not data:
        return ProjectConfig(issue_defaults={})
    project = data.get("project", {})
    if not isinstance(project, dict):
        raise ProjectConfigError(f"{path}: project must be a mapping.")
    unexpected = set(project) - ALLOWED_PROJECT_KEYS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ProjectConfigError(f"{path}: project contains unsupported keys: {names}.")
    return ProjectConfig(
        areas=read_string_list(path, project, "areas"),
        initiatives=read_string_list(path, project, "initiatives"),
        issue_defaults=read_issue_defaults(path, project),
    )


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime packaging
        raise ProjectConfigError("PyYAML is required to read GitHub Project config.") from exc
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectConfigError(f"{path}: unable to read GitHub Project config: {exc.strerror}.") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ProjectConfigError(f"{path}: invalid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ProjectConfigError(f"{path}: expected mapping at document root.")
    unexpected = set(data) - {"project"}
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ProjectConfigError(f"{path}: unsupported top-level keys: {names}.")
    return data


def read_string_list(path: Path, project: dict[str, Any], key: str) -> tuple[str, ...]:
    raw = project.get(key, [])
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ProjectConfigError(f"{path}: project.{key} must be a list of strings.")
    values: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            raise ProjectConfigError(f"{path}: project.{key}[{index}] must be a non-empty string.")
        cleaned = value.strip()
        if cleaned not in seen:
            values.append(cleaned)
            seen.add(cleaned)
    return tuple(values)


def read_issue_defaults(path: Path, project: dict[str, Any]) -> dict[str, str]:
    raw = project.get("issue_defaults", {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ProjectConfigError(f"{path}: project.issue_defaults must be a mapping.")
    unexpected = set(raw) - ALLOWED_DEFAULT_KEYS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ProjectConfigError(f"{path}: project.issue_defaults contains unsupported keys: {names}.")
    defaults: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str) or not value.strip():
            raise ProjectConfigError(f"{path}: project.issue_defaults.{key} must be a non-empty string.")
        defaults[key] = value.strip()
    return defaults
