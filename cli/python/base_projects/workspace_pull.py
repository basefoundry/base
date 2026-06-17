from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import read_workspace_manifest


MAX_WORKSPACE_MANIFEST_SOURCE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class WorkspaceManifestPullResult:
    source: str
    target: Path
    manifest: WorkspaceManifest
    status: str
    changed: bool


def pull_workspace_manifest(source: str, target: Path, *, dry_run: bool) -> WorkspaceManifestPullResult:
    content = fetch_workspace_manifest_source(source)
    manifest = validate_workspace_manifest_content(content, source)
    existing_content = read_existing_manifest(target)
    status = workspace_manifest_change_status(existing_content, content, dry_run=dry_run)
    changed = existing_content != content

    if changed and not dry_run:
        write_manifest_atomically(target, content)

    return WorkspaceManifestPullResult(
        source=source,
        target=target,
        manifest=manifest,
        status=status,
        changed=changed,
    )


def read_existing_manifest(target: Path) -> bytes | None:
    if not target.is_file():
        return None
    try:
        return target.read_bytes()
    except OSError as exc:
        raise WorkspaceManifestError(f"Unable to read local workspace manifest '{target}': {exc}") from exc


def workspace_manifest_change_status(existing_content: bytes | None, content: bytes, *, dry_run: bool) -> str:
    if existing_content == content:
        return "up to date"
    if existing_content is None:
        return "would create" if dry_run else "created"
    return "would update" if dry_run else "updated"


def fetch_workspace_manifest_source(source: str) -> bytes:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        try:
            # This command fetches an explicit user-configured manifest source.
            with urlopen(source, timeout=30) as response:  # nosec B310
                return enforce_workspace_manifest_source_size(
                    source,
                    response.read(MAX_WORKSPACE_MANIFEST_SOURCE_BYTES + 1),
                )
        except OSError as exc:
            raise WorkspaceManifestError(f"Unable to fetch workspace manifest source '{source}': {exc}") from exc

    if parsed.scheme == "file":
        path = Path(unquote(parsed.path)).expanduser()
        return read_workspace_manifest_source_file(source, path)

    if parsed.scheme and parsed.scheme not in {"", "file"}:
        raise WorkspaceManifestError(
            f"Unsupported workspace manifest source '{source}'. Expected a local path, file:// URL, or http(s) URL."
        )

    return read_workspace_manifest_source_file(source, Path(source).expanduser())


def read_workspace_manifest_source_file(source: str, path: Path) -> bytes:
    try:
        with path.open("rb") as source_file:
            return enforce_workspace_manifest_source_size(
                source,
                source_file.read(MAX_WORKSPACE_MANIFEST_SOURCE_BYTES + 1),
            )
    except OSError as exc:
        raise WorkspaceManifestError(f"Unable to fetch workspace manifest source '{source}': {exc}") from exc


def enforce_workspace_manifest_source_size(source: str, content: bytes) -> bytes:
    if len(content) > MAX_WORKSPACE_MANIFEST_SOURCE_BYTES:
        raise WorkspaceManifestError(
            f"Workspace manifest source '{source}' exceeds the "
            f"{MAX_WORKSPACE_MANIFEST_SOURCE_BYTES} byte limit."
        )
    return content


def validate_workspace_manifest_content(content: bytes, source: str) -> WorkspaceManifest:
    if not content:
        raise WorkspaceManifestError(f"Fetched workspace manifest from '{source}' is empty.")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("wb", suffix="-workspace.yaml", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        return read_workspace_manifest(temp_path)
    except WorkspaceManifestError as exc:
        raise WorkspaceManifestError(f"Fetched workspace manifest from '{source}' is invalid: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def write_manifest_atomically(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=target.parent, prefix=f".{target.name}.", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        os.replace(temp_path, target)
    except OSError as exc:
        raise WorkspaceManifestError(f"Unable to write workspace manifest '{target}': {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
