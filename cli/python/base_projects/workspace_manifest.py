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


CURRENT_WORKSPACE_MANIFEST_SCHEMA_VERSION = 1


class WorkspaceManifestError(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceManifestRepo:
    name: str
    url: str | None = None
    default_branch: str | None = None
    required: bool = True


@dataclass(frozen=True)
class WorkspaceManifest:
    path: Path
    name: str
    repos: tuple[WorkspaceManifestRepo, ...]
    schema_version: int = CURRENT_WORKSPACE_MANIFEST_SCHEMA_VERSION


def read_workspace_manifest(path: Path) -> WorkspaceManifest:
    if yaml is None:
        raise WorkspaceManifestError(
            "PyYAML is required to read workspace manifests. "
            "Run 'basectl setup' to install Base Python bootstrap dependencies."
        ) from _yaml_import_error

    resolved_path = path.expanduser().resolve()
    try:
        data = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkspaceManifestError(f"{resolved_path}: unable to read workspace manifest: {exc}") from exc
    except yaml.YAMLError as exc:
        raise WorkspaceManifestError(f"{resolved_path}: invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise WorkspaceManifestError(f"{resolved_path}: workspace manifest must be a YAML mapping.")

    allowed_top_level = {"schema_version", "workspace", "repos"}
    unknown_top_level = sorted(set(data) - allowed_top_level)
    if unknown_top_level:
        raise WorkspaceManifestError(
            f"{resolved_path}: unsupported top-level keys: {', '.join(unknown_top_level)}."
        )

    schema_version = _read_schema_version(resolved_path, data.get("schema_version"))
    workspace_name = _read_workspace_name(resolved_path, data.get("workspace"))
    repos = _read_repos(resolved_path, data.get("repos"))

    return WorkspaceManifest(
        path=resolved_path,
        name=workspace_name,
        repos=repos,
        schema_version=schema_version,
    )


def _read_schema_version(path: Path, schema_version_data: Any) -> int:
    if schema_version_data is None:
        raise WorkspaceManifestError(f"{path}: schema_version is required.")
    if isinstance(schema_version_data, bool) or not isinstance(schema_version_data, int):
        raise WorkspaceManifestError(f"{path}: schema_version must be an integer.")
    if schema_version_data < 1:
        raise WorkspaceManifestError(f"{path}: schema_version must be greater than or equal to 1.")
    if schema_version_data > CURRENT_WORKSPACE_MANIFEST_SCHEMA_VERSION:
        raise WorkspaceManifestError(
            f"{path}: schema_version {schema_version_data} is newer than supported schema version "
            f"{CURRENT_WORKSPACE_MANIFEST_SCHEMA_VERSION}. Upgrade Base to read this workspace manifest."
        )
    return schema_version_data


def _read_workspace_name(path: Path, workspace_data: Any) -> str:
    if not isinstance(workspace_data, dict):
        raise WorkspaceManifestError(f"{path}: workspace must be a mapping.")

    allowed_workspace_keys = {"name"}
    unknown_workspace_keys = sorted(set(workspace_data) - allowed_workspace_keys)
    if unknown_workspace_keys:
        raise WorkspaceManifestError(f"{path}: unsupported workspace keys: {', '.join(unknown_workspace_keys)}.")

    name = workspace_data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise WorkspaceManifestError(f"{path}: workspace.name is required.")
    return name.strip()


def _read_repos(path: Path, repos_data: Any) -> tuple[WorkspaceManifestRepo, ...]:
    if not isinstance(repos_data, list):
        raise WorkspaceManifestError(f"{path}: repos is required and must be a list.")

    repos = tuple(_read_repo(path, index, repo_data) for index, repo_data in enumerate(repos_data, start=1))
    return _validate_unique_repo_names(path, repos)


def _read_repo(path: Path, index: int, repo_data: Any) -> WorkspaceManifestRepo:
    if not isinstance(repo_data, dict):
        raise WorkspaceManifestError(f"{path}: repos[{index}] must be a mapping.")

    allowed_repo_keys = {"name", "url", "default_branch", "required"}
    unknown_repo_keys = sorted(set(repo_data) - allowed_repo_keys)
    if unknown_repo_keys:
        raise WorkspaceManifestError(
            f"{path}: repos[{index}] has unsupported keys: {', '.join(unknown_repo_keys)}."
        )

    name = _read_repo_name(path, index, repo_data.get("name"))
    url = _read_optional_string(path, f"repos[{index}].url", repo_data.get("url"))
    default_branch = _read_optional_string(
        path,
        f"repos[{index}].default_branch",
        repo_data.get("default_branch"),
    )
    required = _read_required(path, index, repo_data.get("required"))

    return WorkspaceManifestRepo(
        name=name,
        url=url,
        default_branch=default_branch,
        required=required,
    )


def _read_repo_name(path: Path, index: int, name_data: Any) -> str:
    if not isinstance(name_data, str) or not name_data.strip():
        raise WorkspaceManifestError(f"{path}: repos[{index}].name is required.")

    name = name_data.strip()
    if name in (".", "..") or "/" in name or "\\" in name:
        raise WorkspaceManifestError(f"{path}: repos[{index}].name must be a directory name, not a path.")
    return name


def _read_optional_string(path: Path, field: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceManifestError(f"{path}: {field} must be a non-empty string when provided.")
    return value.strip()


def _read_required(path: Path, index: int, required_data: Any) -> bool:
    if required_data is None:
        return True
    if not isinstance(required_data, bool):
        raise WorkspaceManifestError(f"{path}: repos[{index}].required must be a boolean.")
    return required_data


def _validate_unique_repo_names(
    path: Path,
    repos: tuple[WorkspaceManifestRepo, ...],
) -> tuple[WorkspaceManifestRepo, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for repo in repos:
        if repo.name in seen:
            duplicates.append(repo.name)
        else:
            seen.add(repo.name)
    if duplicates:
        raise WorkspaceManifestError(f"{path}: duplicate repo names: {', '.join(sorted(set(duplicates)))}.")
    return repos
