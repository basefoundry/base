from __future__ import annotations

from pathlib import Path
from typing import Any

from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import ReleaseConfig
from base_setup.manifest_model import ReleaseGithubConfig
from base_setup.manifest_model import ReleaseHomebrewConfig
from base_setup.manifest_reader_common import read_optional_runner
from base_setup.manifest_schema import GITHUB_REPOSITORY_RE
from base_setup.manifest_schema import HOMEBREW_PACKAGE_RE
from base_setup.manifest_schema import has_control_line_break
from base_setup.release_title import release_title_template_error


def read_release_config(path: Path, release_data: Any) -> ReleaseConfig | None:
    if release_data is None:
        return None
    if not isinstance(release_data, dict):
        raise ManifestError(f"{path}: release must be a mapping when provided.")

    allowed_keys = {"version_file", "changelog", "tag_prefix", "github", "homebrew", "runner"}
    unknown_keys = sorted(set(release_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: release has unsupported keys: {', '.join(unknown_keys)}.")

    version_file = _read_release_relative_path(
        path,
        "release.version_file",
        release_data.get("version_file", "VERSION"),
    )
    changelog = _read_release_relative_path(
        path,
        "release.changelog",
        release_data.get("changelog", "CHANGELOG.md"),
    )
    tag_prefix = _read_release_string(path, "release.tag_prefix", release_data.get("tag_prefix", "v"))
    github = _read_release_github(path, release_data.get("github"))
    homebrew = _read_release_homebrew(path, release_data.get("homebrew"))

    return ReleaseConfig(
        version_file=version_file,
        changelog=changelog,
        tag_prefix=tag_prefix,
        github=github,
        homebrew=homebrew,
        runner=read_optional_runner(path, "release.runner", release_data.get("runner")),
    )


def _read_release_github(path: Path, github_data: Any) -> ReleaseGithubConfig:
    if not isinstance(github_data, dict):
        raise ManifestError(f"{path}: release.github must be a mapping.")

    allowed_keys = {"repository", "release_title"}
    unknown_keys = sorted(set(github_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: release.github has unsupported keys: {', '.join(unknown_keys)}.")

    repository = _read_release_repository(path, "release.github.repository", github_data.get("repository"))
    release_title = _read_release_title(
        path,
        "release.github.release_title",
        github_data.get("release_title", "{repository} v{version}"),
    )
    return ReleaseGithubConfig(repository=repository, release_title=release_title)


def _read_release_homebrew(path: Path, homebrew_data: Any) -> ReleaseHomebrewConfig | None:
    if homebrew_data is None:
        return None
    if not isinstance(homebrew_data, dict):
        raise ManifestError(f"{path}: release.homebrew must be a mapping when provided.")

    allowed_keys = {"required", "tap_repository", "formula_path", "package"}
    unknown_keys = sorted(set(homebrew_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: release.homebrew has unsupported keys: {', '.join(unknown_keys)}.")

    required = homebrew_data.get("required", True)
    if not isinstance(required, bool):
        raise ManifestError(f"{path}: release.homebrew.required must be a boolean when provided.")

    tap_repository = _read_optional_release_repository(
        path,
        "release.homebrew.tap_repository",
        homebrew_data.get("tap_repository"),
    )
    formula_path = _read_optional_release_relative_path(
        path,
        "release.homebrew.formula_path",
        homebrew_data.get("formula_path"),
    )
    package = _read_optional_homebrew_package(
        path,
        "release.homebrew.package",
        homebrew_data.get("package"),
    )

    if required:
        missing = [
            field_name
            for field_name, field_value in (
                ("tap_repository", tap_repository),
                ("formula_path", formula_path),
                ("package", package),
            )
            if field_value is None
        ]
        if missing:
            raise ManifestError(
                f"{path}: release.homebrew required fields are missing: {', '.join(missing)}."
            )

    return ReleaseHomebrewConfig(
        required=required,
        tap_repository=tap_repository,
        formula_path=formula_path,
        package=package,
    )


def _read_release_repository(path: Path, field_name: str, value: Any) -> str:
    repository = _read_release_string(path, field_name, value)
    if not GITHUB_REPOSITORY_RE.fullmatch(repository):
        raise ManifestError(f"{path}: {field_name} must use owner/name format.")
    return repository


def _read_optional_release_repository(path: Path, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _read_release_repository(path, field_name, value)


def _read_optional_homebrew_package(path: Path, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    package = _read_release_string(path, field_name, value)
    if not HOMEBREW_PACKAGE_RE.fullmatch(package):
        raise ManifestError(f"{path}: {field_name} must use owner/tap/formula format.")
    return package


def _read_release_relative_path(path: Path, field_name: str, value: Any) -> str:
    release_path = _read_release_string(path, field_name, value)
    parsed_path = Path(release_path)
    if parsed_path.is_absolute() or ".." in parsed_path.parts:
        raise ManifestError(f"{path}: {field_name} must be a relative path inside the project.")
    return release_path


def _read_optional_release_relative_path(path: Path, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _read_release_relative_path(path, field_name, value)


def _read_release_string(path: Path, field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{path}: {field_name} must be a non-empty string.")
    value = value.strip()
    if has_control_line_break(value):
        raise ManifestError(f"{path}: {field_name} must not contain control line breaks.")
    return value


def _read_release_title(path: Path, field_name: str, value: Any) -> str:
    title = _read_release_string(path, field_name, value)
    if error := release_title_template_error(title):
        raise ManifestError(f"{path}: {field_name} {error}")
    return title
