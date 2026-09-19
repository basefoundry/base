from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from base_cli_adapters.finished_history import iter_finished_history_payloads
from base_cli_adapters.finished_history import project_finished_history_payload
from base_cli_adapters.finished_history import record_table_width


def test_finished_history_projection_shares_fallback_and_optional_fields() -> None:
    payload = {
        "event": "finished",
        "schema_version": 1,
        "run_id": "20260601T010000_abcdefgh",
        "command": "check",
        "status": "error",
        "exit_code": 1,
        "started_at": "2026-06-01T01:00:00Z",
    }

    projected = project_finished_history_payload(payload)

    assert projected is not None
    assert projected.payload is payload
    assert projected.run_id == payload["run_id"]
    assert projected.command == "check"
    assert projected.project is None
    assert projected.raw_command is None
    assert projected.ended_at == payload["started_at"]
    assert projected.sort_time == datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
    assert projected.log_path is None
    assert projected.scope is None


def test_finished_history_iterator_keeps_line_numbers_and_reader_diagnostic(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "runs.jsonl"
    payload = {
        "event": "finished",
        "schema_version": 1,
        "run_id": "20260601T010000_abcdefgh",
        "command": "check",
        "status": "ok",
    }
    history_path.write_text(f"{{broken\n{json.dumps(payload)}\n", encoding="utf-8")
    logger = Mock()

    records = list(
        iter_finished_history_payloads(
            history_path,
            logger,
            ignored_line_message="Skipping record line %s from '%s'.",
        )
    )

    assert records == [(2, payload)]
    logger.debug.assert_called_once_with("Skipping record line %s from '%s'.", 1, history_path)


def test_shared_history_table_width_preserves_long_values_and_minimums() -> None:
    records = [{"command": "a very long command", "status": "ok"}]
    columns = (("COMMAND", "command"), ("STATUS", "status"))

    assert record_table_width(records, columns, (12, 6)) == len("a very long command") + 6 + 2
