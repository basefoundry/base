from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^(?!\.{1,2}/)[^/\s]+/(?!\.{1,2}$)[^/\s]+$")
VERSION_CORE = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
PRERELEASE_IDENTIFIER = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER_RE = re.compile(
    rf"^{VERSION_CORE}(?:-{PRERELEASE_IDENTIFIER}(?:\.{PRERELEASE_IDENTIFIER})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
TAG_RE = re.compile(rf"^v{VERSION_CORE}$")
RESULTS = {"passed", "failed", "not_tested"}
SOURCE_MODES = {"release", "tag", "moving"}
DIGEST_LINE_RE = re.compile(r"^(?P<digest>[0-9a-f]{64})  (?P<name>[^/\n]+)$")
TOP_LEVEL_KEYS = frozenset({"schema_version", "release", "components", "combinations"})
RELEASE_KEYS = frozenset({"repository", "version", "tag", "commit"})
COMPONENT_KEYS = frozenset(
    {
        "repository",
        "version",
        "tag",
        "commit",
        "source_mode",
        "api_schema_version",
        "platforms",
        "required",
        "result",
        "evidence",
    }
)
COMBINATION_KEYS = frozenset({"name", "participants", "platform", "required", "result", "evidence"})


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
    _reject_unknown_keys(document, "BOM", TOP_LEVEL_KEYS)
    if document.get("schema_version") != 1:
        raise ReleaseBomError("schema_version must be 1")

    release = _mapping(document, "release")
    _reject_unknown_keys(release, "release", RELEASE_KEYS)
    release_repository = _repository(release, "repository", "release")
    release_version = _version(release, "release")
    release_tag = _string(release, "tag", "release.tag")
    release_commit = _commit(release, "commit", "release.commit")
    if not TAG_RE.fullmatch(release_tag) or release_tag != f"v{release_version}":
        raise ReleaseBomError("release.tag must be v<release.version>")
    if expected_repository is not None and release_repository.casefold() != expected_repository.casefold():
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
    component_platforms: dict[str, set[str]] = {}
    for index, component in enumerate(components):
        path = f"components[{index}]"
        row = _mapping_value(component, path)
        _reject_unknown_keys(row, path, COMPONENT_KEYS)
        repository = _repository(row, "repository", path)
        repository_key = repository.casefold()
        if repository_key in component_repositories:
            raise ReleaseBomError(f"{path}.repository is duplicated: {repository}")
        component_repositories.add(repository_key)
        version = _version(row, path)
        source_mode = _string(row, "source_mode", f"{path}.source_mode")
        if source_mode not in SOURCE_MODES:
            raise ReleaseBomError(f"{path}.source_mode must be one of: {', '.join(sorted(SOURCE_MODES))}")
        commit = _commit(row, "commit", path)
        if repository_key == release_repository.casefold() and commit != release_commit:
            raise ReleaseBomError(f"{path}.commit must match release.commit")
        required = _boolean(row, "required", path)
        _string(row, "api_schema_version", f"{path}.api_schema_version")
        platforms = row.get("platforms")
        if not isinstance(platforms, list) or not platforms or not all(
            isinstance(platform, str) and platform.strip() for platform in platforms
        ):
            raise ReleaseBomError(f"{path}.platforms must be a non-empty array of strings")
        component_platforms[repository_key] = set(platforms)
        result = _string(row, "result", f"{path}.result")
        if result not in RESULTS:
            raise ReleaseBomError(f"{path}.result must be one of: {', '.join(sorted(RESULTS))}")
        _string(row, "evidence", f"{path}.evidence")
        if required:
            if source_mode == "moving":
                raise ReleaseBomError(f"{path} cannot require a moving source")
            if result != "passed":
                raise ReleaseBomError(f"{path} is required but result is {result!r}")
        if source_mode == "moving" and row.get("tag") is not None:
            raise ReleaseBomError(f"{path}.tag must be omitted for moving sources")
        if source_mode != "moving":
            tag = _string(row, "tag", f"{path}.tag")
            if not TAG_RE.fullmatch(tag):
                raise ReleaseBomError(f"{path}.tag must be an immutable vX.Y.Z tag")
            if tag != f"v{version}":
                raise ReleaseBomError(f"{path}.tag must be v<{path}.version>")
    if release_repository.casefold() not in component_repositories:
        raise ReleaseBomError("release.repository must be declared in components")

    combinations = document.get("combinations")
    if not isinstance(combinations, list) or not combinations:
        raise ReleaseBomError("combinations must be a non-empty array")
    required_combination = False
    required_release_combination = False
    for index, combination in enumerate(combinations):
        path = f"combinations[{index}]"
        row = _mapping_value(combination, path)
        _reject_unknown_keys(row, path, COMBINATION_KEYS)
        _string(row, "name", f"{path}.name")
        participants = row.get("participants")
        if not isinstance(participants, list) or not participants:
            raise ReleaseBomError(f"{path}.participants must be a non-empty array")
        if not all(isinstance(participant, str) for participant in participants):
            raise ReleaseBomError(f"{path}.participants must contain repository strings")
        if len(set(participant.casefold() for participant in participants)) < 2:
            raise ReleaseBomError(f"{path}.participants must contain at least two repositories")
        participant_keys = {participant.casefold() for participant in participants}
        unknown = sorted(participant_keys - component_repositories)
        if unknown:
            raise ReleaseBomError(f"{path}.participants references unknown components: {unknown}")
        platform = _string(row, "platform", f"{path}.platform")
        unsupported = sorted(key for key in participant_keys if platform not in component_platforms[key])
        if unsupported:
            raise ReleaseBomError(f"{path}.platform {platform!r} is not declared by participants: {unsupported}")
        required = _boolean(row, "required", path)
        result = _string(row, "result", f"{path}.result")
        if result not in RESULTS:
            raise ReleaseBomError(f"{path}.result must be one of: {', '.join(sorted(RESULTS))}")
        _string(row, "evidence", f"{path}.evidence")
        if required:
            required_combination = True
            if release_repository.casefold() in participant_keys:
                required_release_combination = True
            if result != "passed":
                raise ReleaseBomError(f"{path} is required but result is {result!r}")
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


def bom_digest_sidecar_path(bom_path: Path) -> Path:
    """Return the stable sidecar path for a BOM output path."""
    if bom_path.suffix == ".json":
        return bom_path.with_suffix(".sha256")
    return bom_path.with_name(f"{bom_path.name}.sha256")


def write_bom_digest_sidecar(bom_path: Path, digest: str | None = None) -> Path:
    """Write the BOM's SHA-256 digest and referenced filename to its sidecar."""
    if digest is None:
        digest = hashlib.sha256(bom_path.read_bytes()).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ReleaseBomError("BOM digest must be a lowercase 64-character SHA-256 value")
    sidecar_path = bom_digest_sidecar_path(bom_path)
    sidecar_path.write_text(f"{digest}  {bom_path.name}\n", encoding="utf-8")
    return sidecar_path


def read_bom_digest_sidecar(bom_path: Path, *, bom_bytes: bytes | None = None) -> str:
    """Validate and return a BOM digest sidecar's recorded digest."""
    sidecar_path = bom_digest_sidecar_path(bom_path)
    line = sidecar_path.read_text(encoding="utf-8").strip("\n")
    match = DIGEST_LINE_RE.fullmatch(line)
    if match is None or match.group("name") != bom_path.name:
        raise ReleaseBomError(
            f"BOM digest sidecar {sidecar_path} must contain '<sha256>  {bom_path.name}'"
        )
    actual_digest = hashlib.sha256(bom_bytes if bom_bytes is not None else bom_path.read_bytes()).hexdigest()
    if match.group("digest") != actual_digest:
        raise ReleaseBomError(f"BOM digest sidecar {sidecar_path} does not match {bom_path}")
    return match.group("digest")


def _mapping(document: dict[str, Any], key: str) -> dict[str, Any]:
    return _mapping_value(document.get(key), key)


def _mapping_value(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReleaseBomError(f"{path} must be an object")
    return value


def _reject_unknown_keys(row: dict[str, Any], path: str, allowed_keys: frozenset[str]) -> None:
    unknown_keys = sorted(set(row) - allowed_keys)
    if unknown_keys:
        raise ReleaseBomError(f"{path} has unsupported keys: {', '.join(unknown_keys)}")


def _string(row: dict[str, Any], key: str, path: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReleaseBomError(f"{path} must be a non-empty string")
    return value


def _repository(row: dict[str, Any], key: str = "repository", path: str = "") -> str:
    value = _string(row, key, f"{path + '.' if path else ''}{key}")
    if not REPOSITORY_RE.fullmatch(value):
        raise ReleaseBomError(f"{path + '.' if path else ''}{key} must use owner/name format")
    return value


def _version(row: dict[str, Any], path: str) -> str:
    value = _string(row, "version", f"{path}.version")
    if not SEMVER_RE.fullmatch(value):
        raise ReleaseBomError(f"{path}.version must be a strict SemVer value")
    return value


def _commit(row: dict[str, Any], key: str, path: str) -> str:
    value = _string(row, key, f"{path}.{key}")
    if not FULL_SHA_RE.fullmatch(value):
        raise ReleaseBomError(f"{path}.{key} must be a lowercase full 40-character SHA")
    return value


def _boolean(row: dict[str, Any], key: str, path: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise ReleaseBomError(f"{path}.{key} must be a boolean")
    return value
