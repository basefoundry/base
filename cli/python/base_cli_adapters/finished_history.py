from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .history import (
    optional_int,
    optional_string,
    parse_finished_history_record_line,
)


@dataclass(frozen=True)
class FinishedHistoryFields:
    payload: dict[str, Any]
    run_id: str
    command: str
    raw_command: str | None
    project: str | None
    status: str
    exit_code: int | None
    ended_at: str
    sort_time: datetime
    log_path: str | None
    scope: str | None


def project_finished_history_payload(payload: dict[str, Any]) -> FinishedHistoryFields | None:
    run_id = optional_string(payload.get("run_id"))
    command = optional_string(payload.get("command"))
    status = optional_string(payload.get("status"))
    if not run_id or not command or not status:
        return None

    ended_at = optional_string(payload.get("ended_at")) or optional_string(payload.get("started_at")) or ""
    return FinishedHistoryFields(
        payload=payload,
        run_id=run_id,
        command=command,
        raw_command=optional_string(payload.get("raw_command")),
        project=optional_string(payload.get("project")),
        status=status,
        exit_code=optional_int(payload.get("exit_code")),
        ended_at=ended_at,
        sort_time=parse_finished_history_timestamp(ended_at),
        log_path=optional_string(payload.get("log_path")),
        scope=optional_string(payload.get("scope")),
    )


def parse_finished_history_timestamp(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def iter_finished_history_payloads(
    path: Path,
    logger: Any | None = None,
    *,
    ignored_line_message: str = "Ignoring malformed history line %s in '%s'.",
) -> Iterator[tuple[int, dict[str, Any]]]:
    if not path.is_file():
        return

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            payload = parse_finished_history_record_line(line)
            if payload is None:
                if logger is not None:
                    logger.debug(ignored_line_message, line_number, path)
                continue
            yield line_number, payload


def record_table_width(
    records: list[dict[str, Any]],
    columns: tuple[tuple[str, str], ...],
    minimum_widths: Iterable[int],
) -> int:
    minimum_width_values = tuple(minimum_widths)
    widths = []
    for index, (header, key) in enumerate(columns):
        values = [str(record.get(key, "")) for record in records]
        minimum_width = minimum_width_values[index] if index < len(minimum_width_values) else 0
        widths.append(max(len(header), minimum_width, *(len(value) for value in values)))
    return sum(widths) + 2 * (len(columns) - 1)
