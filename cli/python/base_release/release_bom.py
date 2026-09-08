from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
RESULTS = {"passed", "failed", "not_tested"}
SOURCE_MODES = {"release", "tag", "moving"}


class ReleaseBomError(ValueError):
    """Raised when a release BOM is malformed or fails its release gate."""


def load_bom(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReleaseBomError(f"could not read BOM {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseBomError(f"BOM {path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ReleaseBomError("BOM document must be a JSON object")
    return value


# pylint: disable=too-many-branches,too-many-statements
def validate_bom(
    document: dict[str, Any],
    *,
    expected_repository: str | None = None,
    expected_version: str | None = None,
    expected_commit: str | None = None,
) -> None:
    if document.get("schema_version") != 1:
        raise ReleaseBomError("schema_version must be 1")

    release = _mapping(document, "release")
    release_repository = _repository(release, "repository", "release")
    release_version = _string(release, "version", "release.version")
    release_tag = _string(release, "tag", "release.tag")
    release_commit = _commit(release, "commit", "release.commit")
    if not TAG_RE.fullmatch(release_tag) or release_tag != f"v{release_version}":
        raise ReleaseBomError("release.tag must be v<release.version>")
    if expected_repository is not None and release["repository"] != expected_repository:
        raise ReleaseBomError(
            f"release.repository {release['repository']!r} does not match {expected_repository!r}"
        )
    if expected_version is not None and release_version != expected_version:
        raise ReleaseBomError(
            f"release.version {release_version!r} does not match {expected_version!r}"
        )
    if expected_commit is not None and release_commit != expected_commit:
        raise ReleaseBomError("release.commit does not match the reviewed release commit")

    components = document.get("components")
    if not isinstance(components, list) or not components:
        raise ReleaseBomError("components must be a non-empty array")
    component_repositories: set[str] = set()
    for index, component in enumerate(components):
        path = f"components[{index}]"
        row = _mapping_value(component, path)
        repository = _repository(row, "repository", path)
        if repository in component_repositories:
            raise ReleaseBomError(f"{path}.repository is duplicated: {repository}")
        component_repositories.add(repository)
        _string(row, "version", f"{path}.version")
        source_mode = _string(row, "source_mode", f"{path}.source_mode")
        if source_mode not in SOURCE_MODES:
            raise ReleaseBomError(f"{path}.source_mode must be one of: {', '.join(sorted(SOURCE_MODES))}")
        commit = _commit(row, "commit", path)
        required = _boolean(row, "required", path)
        _string(row, "api_schema_version", f"{path}.api_schema_version")
        platforms = row.get("platforms")
        if not isinstance(platforms, list) or not platforms or not all(
            isinstance(platform, str) and platform.strip() for platform in platforms
        ):
            raise ReleaseBomError(f"{path}.platforms must be a non-empty array of strings")
        result = _string(row, "result", f"{path}.result")
        if result not in RESULTS:
            raise ReleaseBomError(f"{path}.result must be one of: {', '.join(sorted(RESULTS))}")
        evidence = _string(row, "evidence", f"{path}.evidence")
        if required:
            if source_mode == "moving":
                raise ReleaseBomError(f"{path} cannot require a moving source")
            if result != "passed":
                raise ReleaseBomError(f"{path} is required but result is {result!r}")
            if not evidence:
                raise ReleaseBomError(f"{path}.evidence is required")
        if source_mode == "moving" and row.get("tag") is not None:
            raise ReleaseBomError(f"{path}.tag must be omitted for moving sources")
        if source_mode != "moving":
            tag = _string(row, "tag", f"{path}.tag")
            if not TAG_RE.fullmatch(tag):
                raise ReleaseBomError(f"{path}.tag must be an immutable vX.Y.Z tag")
        if commit != commit.lower():
            raise ReleaseBomError(f"{path}.commit must use lowercase hexadecimal")
    if release_repository not in component_repositories:
        raise ReleaseBomError("release.repository must be declared in components")

    combinations = document.get("combinations")
    if not isinstance(combinations, list) or not combinations:
        raise ReleaseBomError("combinations must be a non-empty array")
    required_combination = False
    required_release_combination = False
    for index, combination in enumerate(combinations):
        path = f"combinations[{index}]"
        row = _mapping_value(combination, path)
        _string(row, "name", f"{path}.name")
        participants = row.get("participants")
        if not isinstance(participants, list) or not participants:
            raise ReleaseBomError(f"{path}.participants must be a non-empty array")
        if not all(isinstance(participant, str) for participant in participants):
            raise ReleaseBomError(f"{path}.participants must contain repository strings")
        if len(set(participants)) < 2:
            raise ReleaseBomError(f"{path}.participants must contain at least two repositories")
        unknown = sorted(set(participants) - component_repositories)
        if unknown:
            raise ReleaseBomError(f"{path}.participants references unknown components: {unknown}")
        _string(row, "platform", f"{path}.platform")
        required = _boolean(row, "required", path)
        result = _string(row, "result", f"{path}.result")
        if result not in RESULTS:
            raise ReleaseBomError(f"{path}.result must be one of: {', '.join(sorted(RESULTS))}")
        evidence = _string(row, "evidence", f"{path}.evidence")
        if required:
            required_combination = True
            if release_repository in participants:
                required_release_combination = True
            if result != "passed":
                raise ReleaseBomError(f"{path} is required but result is {result!r}")
            if not evidence:
                raise ReleaseBomError(f"{path}.evidence is required")
    if not required_combination:
        raise ReleaseBomError("at least one required combination must be declared")
    if not required_release_combination:
        raise ReleaseBomError("at least one required combination must include release.repository")


def validate_bom_file(
    path: Path,
    *,
    expected_repository: str | None = None,
    expected_version: str | None = None,
    expected_commit: str | None = None,
) -> None:
    validate_bom(
        load_bom(path),
        expected_repository=expected_repository,
        expected_version=expected_version,
        expected_commit=expected_commit,
    )


def canonical_bom_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode(
        "utf-8"
    )


def bom_digest(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bom_bytes(document)).hexdigest()


def _mapping(document: dict[str, Any], key: str) -> dict[str, Any]:
    return _mapping_value(document.get(key), key)


def _mapping_value(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReleaseBomError(f"{path} must be an object")
    return value


def _string(row: dict[str, Any], key: str, path: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReleaseBomError(f"{path} must be a non-empty string")
    return value


def _repository(row: dict[str, Any], key: str = "repository", path: str = "") -> str:
    value = _string(row, key, f"{path + '.' if path else ''}{key}")
    if "/" not in value or value.startswith("/") or value.endswith("/"):
        raise ReleaseBomError(f"{path + '.' if path else ''}{key} must use owner/name format")
    return value


def _commit(row: dict[str, Any], key: str, path: str) -> str:
    value = _string(row, key, f"{path}.{key}")
    if not FULL_SHA_RE.fullmatch(value.lower()):
        raise ReleaseBomError(f"{path}.{key} must be a full 40-character SHA")
    return value


def _boolean(row: dict[str, Any], key: str, path: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise ReleaseBomError(f"{path}.{key} must be a boolean")
    return value
