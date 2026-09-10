from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ProjectDiscoveryError(RuntimeError):
    pass


class ProjectNotFoundError(ProjectDiscoveryError):
    pass


@dataclass(frozen=True)
class ManifestEntry:
    path: Path
    mtime_ns: int
    size: int


def workspace_manifest_entries(workspace_root: Path) -> tuple[ManifestEntry, ...]:
    if not workspace_root.is_dir():
        raise ProjectDiscoveryError(f"Workspace '{workspace_root}' is not a directory.")

    entries: list[ManifestEntry] = []
    for candidate in sorted(workspace_root.iterdir(), key=lambda path: path.name):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "base_manifest.yaml"
        if not manifest_path.is_file():
            continue
        stat_result = manifest_path.stat()
        entries.append(
            ManifestEntry(
                path=manifest_path,
                mtime_ns=stat_result.st_mtime_ns,
                size=stat_result.st_size,
            )
        )

    return tuple(entries)


def workspace_repository_paths(workspace_root: Path) -> tuple[Path, ...]:
    """Return direct-child directories that look like Git repositories."""
    if not workspace_root.is_dir():
        raise ProjectDiscoveryError(f"Workspace '{workspace_root}' is not a directory.")

    repositories: list[Path] = []
    for candidate in sorted(workspace_root.iterdir(), key=lambda path: path.name):
        if not candidate.is_dir():
            continue
        git_marker = candidate / ".git"
        if git_marker.is_dir() or git_marker.is_file() or _looks_like_bare_repository(candidate):
            repositories.append(candidate.resolve())

    return tuple(repositories)


def _looks_like_bare_repository(candidate: Path) -> bool:
    """Recognize the stable on-disk markers created by ``git init --bare``."""
    return all(
        (
            (candidate / "HEAD").is_file(),
            (candidate / "config").is_file(),
            (candidate / "objects").is_dir(),
            (candidate / "refs").is_dir(),
        )
    )
