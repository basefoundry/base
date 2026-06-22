from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any


class GithubManifestError(ValueError):
    pass


@dataclass(frozen=True)
class GithubPrRequiredSectionsConfig:
    default: tuple[str, ...] = ()
    labels: dict[str, tuple[str, ...]] = field(default_factory=dict)
    paths: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class GithubPrConfig:
    template: str | None = None
    required_sections: GithubPrRequiredSectionsConfig = field(default_factory=GithubPrRequiredSectionsConfig)


@dataclass(frozen=True)
class GithubConfig:
    pr: GithubPrConfig | None = None


def read_github_config(path: Path, github_data: Any) -> GithubConfig:
    if github_data is None:
        return GithubConfig()
    if not isinstance(github_data, dict):
        raise GithubManifestError(f"{path}: github must be a mapping when provided.")

    allowed_keys = {"pr"}
    unknown_keys = sorted(set(github_data) - allowed_keys)
    if unknown_keys:
        raise GithubManifestError(f"{path}: github has unsupported keys: {', '.join(unknown_keys)}.")

    return GithubConfig(pr=_read_github_pr(path, github_data.get("pr")))


def _read_github_pr(path: Path, pr_data: Any) -> GithubPrConfig | None:
    if pr_data is None:
        return None
    if not isinstance(pr_data, dict):
        raise GithubManifestError(f"{path}: github.pr must be a mapping when provided.")

    allowed_keys = {"template", "required_sections"}
    unknown_keys = sorted(set(pr_data) - allowed_keys)
    if unknown_keys:
        raise GithubManifestError(f"{path}: github.pr has unsupported keys: {', '.join(unknown_keys)}.")

    return GithubPrConfig(
        template=_read_github_pr_template(path, pr_data.get("template")),
        required_sections=_read_github_pr_required_sections(path, pr_data.get("required_sections")),
    )


def _read_github_pr_template(path: Path, template_data: Any) -> str | None:
    if template_data is None:
        return None
    template = _read_string(path, "github.pr.template", template_data)
    parsed_path = Path(template)
    if parsed_path.is_absolute() or ".." in parsed_path.parts:
        raise GithubManifestError(f"{path}: github.pr.template must be a relative path inside the project.")
    return template


def _read_github_pr_required_sections(path: Path, sections_data: Any) -> GithubPrRequiredSectionsConfig:
    if sections_data is None:
        return GithubPrRequiredSectionsConfig()
    if not isinstance(sections_data, dict):
        raise GithubManifestError(f"{path}: github.pr.required_sections must be a mapping when provided.")

    allowed_keys = {"default", "labels", "paths"}
    unknown_keys = sorted(set(sections_data) - allowed_keys)
    if unknown_keys:
        raise GithubManifestError(
            f"{path}: github.pr.required_sections has unsupported keys: {', '.join(unknown_keys)}."
        )

    return GithubPrRequiredSectionsConfig(
        default=_read_section_list(
            path,
            "github.pr.required_sections.default",
            sections_data.get("default", []),
        ),
        labels=_read_section_map(
            path,
            "github.pr.required_sections.labels",
            sections_data.get("labels", {}),
        ),
        paths=_read_section_map(
            path,
            "github.pr.required_sections.paths",
            sections_data.get("paths", {}),
        ),
    )


def _read_section_map(path: Path, field_name: str, sections_data: Any) -> dict[str, tuple[str, ...]]:
    if sections_data is None:
        return {}
    if not isinstance(sections_data, dict):
        raise GithubManifestError(f"{path}: {field_name} must be a mapping when provided.")

    section_map: dict[str, tuple[str, ...]] = {}
    for key_data, section_list_data in sections_data.items():
        if not isinstance(key_data, str) or not key_data.strip():
            raise GithubManifestError(f"{path}: {field_name} keys must be non-empty strings.")
        key = key_data.strip()
        if _has_control_line_break(key):
            raise GithubManifestError(f"{path}: {field_name}.{key} must not contain control line breaks.")
        section_map[key] = _read_section_list(path, f"{field_name}.{key}", section_list_data)
    return section_map


def _read_section_list(path: Path, field_name: str, sections_data: Any) -> tuple[str, ...]:
    if sections_data is None:
        return ()
    if not isinstance(sections_data, list):
        raise GithubManifestError(f"{path}: {field_name} must be a list when provided.")

    sections: list[str] = []
    seen: set[str] = set()
    for index, section_data in enumerate(sections_data, start=1):
        if not isinstance(section_data, str) or not section_data.strip():
            raise GithubManifestError(f"{path}: {field_name}[{index}] must be a non-empty string.")
        section = section_data.strip()
        if _has_control_line_break(section):
            raise GithubManifestError(f"{path}: {field_name}[{index}] must not contain control line breaks.")
        if section in seen:
            raise GithubManifestError(f"{path}: {field_name}[{index}] duplicates '{section}'.")
        seen.add(section)
        sections.append(section)
    return tuple(sections)


def _read_string(path: Path, field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GithubManifestError(f"{path}: {field_name} must be a non-empty string.")
    value = value.strip()
    if _has_control_line_break(value):
        raise GithubManifestError(f"{path}: {field_name} must not contain control line breaks.")
    return value


def _has_control_line_break(value: str) -> bool:
    return any(separator in value for separator in ("\0", "\n", "\r"))
