from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import base_cli
import click
from base_cli.paths import base_cache_root


app = base_cli.App(name="base_clean")


@dataclass(frozen=True)
class CleanCandidate:
    path: Path
    category: str
    age_seconds: int


def main(argv: list[str] | None = None) -> int:
    try:
        result = app.click_command.main(args=argv, standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--older-than", help="Remove runtime artifacts older than an age such as 30d.")
@base_cli.option("--keep-last", help="Keep the newest N log files per CLI log directory.")
@base_cli.option("--dry-run", is_flag=True, help="Print what would be removed without deleting anything.")
def run(ctx: base_cli.Context, older_than: str | None, keep_last: str | None, dry_run: bool) -> int:
    if not older_than and not keep_last:
        ctx.log.error("One of '--older-than' or '--keep-last' is required.")
        return 2

    cache_root = base_cache_root()
    ctx.log.debug("Scanning Base cache root '%s'.", cache_root)

    candidates: list[CleanCandidate] = []
    if older_than:
        try:
            threshold_seconds = parse_age(older_than)
        except ValueError as exc:
            ctx.log.error(str(exc))
            return 2
        cutoff = time.time() - threshold_seconds
        candidates.extend(find_clean_candidates(cache_root, cutoff, ctx.log))

    if keep_last:
        try:
            keep_count = parse_keep_last(keep_last)
        except ValueError as exc:
            ctx.log.error(str(exc))
            return 2
        candidates.extend(find_log_retention_candidates(cache_root, keep_count, ctx.log))

    unique_candidates = tuple(deduplicate_candidates(candidates))

    if not unique_candidates:
        ctx.log.info("No Base runtime artifacts matched the clean criteria.")
        return 0

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
    return 0


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
    cli_root = cache_root / "cli"
    if logger is not None:
        logger.debug("Scanning Base CLI runtime root '%s'.", cli_root)
    if not cli_root.is_dir():
        return []

    candidates: list[CleanCandidate] = []
    for cli_dir in sorted(cli_root.iterdir(), key=lambda path: path.name):
        if not cli_dir.is_dir():
            continue
        candidates.extend(find_category_candidates(cli_dir / "logs", "log", cutoff, logger))
        candidates.extend(find_category_candidates(cli_dir / "tmp", "temp", cutoff, logger))
        candidates.extend(find_category_candidates(cli_dir / "cache", "cache", cutoff, logger))
    return sorted(candidates, key=lambda candidate: str(candidate.path))


def find_log_retention_candidates(
    cache_root: Path,
    keep_count: int,
    logger: object | None = None,
) -> list[CleanCandidate]:
    cli_root = cache_root / "cli"
    if logger is not None:
        logger.debug("Scanning Base CLI log retention root '%s'.", cli_root)
    if not cli_root.is_dir():
        return []

    candidates: list[CleanCandidate] = []
    for cli_dir in sorted(cli_root.iterdir(), key=lambda path: path.name):
        if not cli_dir.is_dir():
            continue
        candidates.extend(find_log_retention_candidates_for_dir(cli_dir / "logs", keep_count, logger))
    return sorted(candidates, key=lambda candidate: str(candidate.path))


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
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            candidates.append(CleanCandidate(path=path, category=category, age_seconds=int(time.time() - mtime)))
    return candidates


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
