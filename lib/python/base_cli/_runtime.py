from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .paths import runtime_owner_root, runtime_run_directory_name


@dataclass(frozen=True)
class RuntimeLayout:
    owner_root: Path
    run_root: Path
    state_dir: Path
    log_dir: Path
    cache_dir: Path
    temp_dir: Path


# pylint: disable=too-many-arguments
def runtime_layout(
    cache_root: Path,
    cli_name: str,
    run_id: str,
    *,
    owner: str = "base",
    project_name: str | None = None,
    project_root: Path | None = None,
    inherited_run_root: Path | None = None,
) -> RuntimeLayout:
    owner_root = runtime_owner_root(cache_root, owner, project_name, project_root)
    run_root = inherited_run_root or owner_root / "runs" / runtime_run_directory_name(run_id, cli_name, project_name)
    state_dir = owner_root
    # Every public invocation owns one run bundle and one diagnostic log.
    # Child processes inherit that bundle instead of creating component logs.
    log_dir = run_root / "logs"
    return RuntimeLayout(
        owner_root=owner_root,
        run_root=run_root,
        state_dir=state_dir,
        log_dir=log_dir,
        cache_dir=owner_root / "cache" / "components" / cli_name,
        temp_dir=run_root / "tmp" / cli_name / run_id,
    )


def create_runtime_directory(path: Path, cache_root: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(_runtime_directory_error(path, cache_root, exc)) from exc


def prune_log_files(
    log_dir: Path,
    current_log_file: Path,
    max_log_files: int,
    logger: logging.Logger,
) -> None:
    candidates: list[tuple[str, Path]] = []
    for path in log_dir.rglob("*.log"):
        if _same_path(path, current_log_file):
            continue
        candidates.append((path.name, path))

    excess_count = len(candidates) + 1 - max_log_files
    if excess_count <= 0:
        return

    for _, path in sorted(candidates)[:excess_count]:
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Could not prune log file '%s': %s", path, exc)


def _runtime_directory_error(path: Path, cache_root: Path, exc: OSError) -> str:
    return (
        f"Unable to create Base runtime directory '{path}': {exc}. "
        f"Check permissions on that directory. If the Base cache root '{cache_root}' is unusable, "
        "set BASE_CACHE_DIR to a writable directory."
    )


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()
