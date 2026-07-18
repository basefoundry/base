from __future__ import annotations

import shutil
import time
import json
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.paths import base_cache_root


app = base_cli.App(name="base_clean")


@dataclass(frozen=True)
class CleanCandidate:
    path: Path
    category: str
    age_seconds: int


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option(
    "--older-than",
    help="Remove runtime artifacts older than an age such as 30d, 12h, 45m, or 60s.",
)
@base_cli.option("--keep-last", help="Keep the newest N run bundles per owner namespace.")
@base_cli.option("--dry-run", is_flag=True, help="Print what would be removed without deleting anything.")
def run(ctx: base_cli.Context, older_than: str | None, keep_last: str | None, dry_run: bool) -> int:
    if not older_than and not keep_last:
        ctx.log.error("One of '--older-than' or '--keep-last' is required.")
        return base_cli.ExitCode.USAGE_ERROR

    cache_root = base_cache_root()
    ctx.log.debug("Scanning Base cache root '%s'.", cache_root)

    candidates: list[CleanCandidate] = []
    if older_than:
        try:
            threshold_seconds = parse_age(older_than)
        except ValueError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
        cutoff = time.time() - threshold_seconds
        candidates.extend(find_clean_candidates(cache_root, cutoff, ctx.log))

    if keep_last:
        try:
            keep_count = parse_keep_last(keep_last)
        except ValueError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
        candidates.extend(find_log_retention_candidates(cache_root, keep_count, ctx.log))

    unique_candidates = tuple(deduplicate_candidates(candidates))

    if not unique_candidates:
        ctx.log.info("No Base runtime artifacts matched the clean criteria.")
        return base_cli.ExitCode.SUCCESS

    for candidate in unique_candidates:
        action = "Would remove" if dry_run else "Removing"
        print(f"{action}\t{candidate.category}\t{candidate.path}")
        if not dry_run:
            remove_path(candidate.path)

    ctx.log.info(
        "%s %s Base runtime artifact(s).",
        "Would remove" if dry_run else "Removed",
        len(unique_candidates),
    )
    return base_cli.ExitCode.SUCCESS


def parse_age(value: str) -> int:
    units = {
        "d": 24 * 60 * 60,
        "h": 60 * 60,
        "m": 60,
        "s": 1,
    }
    if len(value) < 2:
        raise ValueError("Option '--older-than' must be an age such as 30d, 12h, 45m, or 60s.")

    number = value[:-1]
    unit = value[-1].lower()
    if unit not in units or not number.isdigit():
        raise ValueError("Option '--older-than' must be an age such as 30d, 12h, 45m, or 60s.")

    amount = int(number)
    if amount <= 0:
        raise ValueError("Option '--older-than' must be greater than zero.")
    return amount * units[unit]


def parse_keep_last(value: str) -> int:
    if not value.isdigit():
        raise ValueError("Option '--keep-last' must be a positive integer.")
    amount = int(value)
    if amount <= 0:
        raise ValueError("Option '--keep-last' must be greater than zero.")
    return amount


def find_clean_candidates(cache_root: Path, cutoff: float, logger: object | None = None) -> list[CleanCandidate]:
    candidates: list[CleanCandidate] = []
    for owner_root in runtime_owner_roots(cache_root):
        if logger is not None:
            logger.debug("Scanning runtime owner root '%s'.", owner_root)
        candidates.extend(find_category_candidates(owner_root / "runs", "run", cutoff, logger))
        candidates.extend(find_category_candidates(owner_root / "cache" / "components", "cache", cutoff, logger))
    return sorted(candidates, key=lambda candidate: str(candidate.path))


def find_log_retention_candidates(
    cache_root: Path,
    keep_count: int,
    logger: object | None = None,
) -> list[CleanCandidate]:
    candidates: list[CleanCandidate] = []
    for owner_root in runtime_owner_roots(cache_root):
        runs_root = owner_root / "runs"
        if logger is not None:
            logger.debug("Scanning run retention artifacts in '%s'.", runs_root)
        if not runs_root.is_dir():
            continue
        run_dirs = []
        for path in sorted(runs_root.iterdir(), key=lambda item: item.name):
            if not path.is_dir() or run_is_running(path):
                continue
            try:
                run_dirs.append((path, run_metadata_mtime(path)))
            except OSError:
                continue
        retained = {path for path, _mtime in sorted(run_dirs, key=lambda item: (item[1], item[0].name), reverse=True)[:keep_count]}
        candidates.extend(
            CleanCandidate(path=path, category="run", age_seconds=int(time.time() - mtime))
            for path, mtime in run_dirs
            if path not in retained
        )
    return sorted(candidates, key=lambda candidate: str(candidate.path))


def runtime_owner_roots(cache_root: Path) -> list[Path]:
    roots = []
    base_root = cache_root / "base"
    if base_root.is_dir():
        roots.append(base_root)
    roots.extend(path for path in sorted((cache_root / "projects").glob("*/*"), key=str) if path.is_dir())
    return roots


def run_is_running(run_root: Path) -> bool:
    metadata = run_root / "run.json"
    if not metadata.is_file():
        return False
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(payload, dict) and payload.get("status") == "running"


def find_log_retention_candidates_for_dir(
    logs_dir: Path,
    keep_count: int,
    logger: object | None = None,
) -> list[CleanCandidate]:
    if logger is not None:
        logger.debug("Scanning log retention artifacts in '%s'.", logs_dir)
    if not logs_dir.is_dir():
        return []

    log_files = []
    for path in sorted(logs_dir.glob("*.log"), key=lambda item: item.name):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        log_files.append((path, stat.st_mtime))

    retained = sorted(log_files, key=lambda item: (item[1], item[0].name), reverse=True)[:keep_count]
    retained_paths = {path for path, _mtime in retained}
    return [
        CleanCandidate(path=path, category="log", age_seconds=int(time.time() - mtime))
        for path, mtime in log_files
        if path not in retained_paths
    ]


def deduplicate_candidates(candidates: list[CleanCandidate]) -> list[CleanCandidate]:
    unique = {candidate.path: candidate for candidate in candidates}
    return sorted(unique.values(), key=lambda candidate: str(candidate.path))


def find_category_candidates(
    category_root: Path,
    category: str,
    cutoff: float,
    logger: object | None = None,
) -> list[CleanCandidate]:
    if logger is not None:
        logger.debug("Scanning %s runtime artifacts in '%s'.", category, category_root)
    if not category_root.is_dir():
        return []

    candidates = []
    for path in sorted(category_root.iterdir(), key=lambda item: item.name):
        try:
            mtime = run_metadata_mtime(path) if category == "run" else path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            candidates.append(CleanCandidate(path=path, category=category, age_seconds=int(time.time() - mtime)))
    return candidates


def run_metadata_mtime(path: Path) -> float:
    metadata = path / "run.json"
    try:
        if metadata.is_file():
            return metadata.stat().st_mtime
        return path.stat().st_mtime
    except OSError:
        return path.stat().st_mtime


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
