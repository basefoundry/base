from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_history import engine


def write_history_line(cache_root: Path, payload: dict | str) -> None:
    path = cache_root / "history" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{text}\n")


# pylint: disable=too-many-arguments
def history_record(
    run_id: str,
    command: str,
    *,
    project: str = "demo",
    status: str = "ok",
    exit_code: int = 0,
    ended_at: str = "2026-06-10T10:15:00Z",
    log_path: str = "~/logs/run.log",
) -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "event": "finished",
        "command": command,
        "raw_command": f"base_{command}",
        "argv": ["basectl", command],
        "project": project,
        "ended_at": ended_at,
        "exit_code": exit_code,
        "status": status,
        "log_path": log_path,
    }


def invoke(args: list[str], cache_root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class BaseHistoryTests(unittest.TestCase):
    def test_recent_history_ignores_malformed_lines_and_sorts_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(
                cache_root,
                history_record(
                    "older",
                    "check",
                    ended_at="2026-06-10T10:10:00Z",
                ),
            )
            write_history_line(cache_root, "{not json")
            write_history_line(
                cache_root,
                history_record(
                    "newer",
                    "setup",
                    ended_at="2026-06-10T10:15:00Z",
                    status="error",
                    exit_code=1,
                ),
            )

            records = engine.recent_history(cache_root)

        self.assertEqual([record.run_id for record in records], ["newer", "older"])
        self.assertEqual([record.command for record in records], ["setup", "check"])

    def test_text_output_lists_recent_history_and_missing_log_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(
                cache_root,
                history_record(
                    "run-1",
                    "check",
                    status="error",
                    exit_code=2,
                    log_path=str(cache_root / "cli" / "base_setup" / "logs" / "missing.log"),
                ),
            )

            status, stdout, stderr = invoke([], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("TIME", stdout)
        self.assertIn("COMMAND", stdout)
        self.assertIn("PROJECT", stdout)
        self.assertIn("check", stdout)
        self.assertIn("error", stdout)
        self.assertIn("missing", stdout)

    def test_json_output_filters_history_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(
                cache_root,
                history_record(
                    "run-1",
                    "check",
                    project="demo",
                    status="error",
                    exit_code=1,
                    ended_at="2026-06-10T10:10:00Z",
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "run-2",
                    "setup",
                    project="base",
                    status="ok",
                    exit_code=0,
                    ended_at="2026-06-10T10:15:00Z",
                ),
            )

            status, stdout, stderr = invoke(
                ["--project", "demo", "--command", "check", "--status", "error", "--format", "json"],
                cache_root,
            )
            payload = json.loads(stdout)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["run_id"], "run-1")
        self.assertEqual(payload[0]["project"], "demo")
        self.assertEqual(payload[0]["status"], "error")
        self.assertFalse(payload[0]["log_exists"])

    def test_empty_history_set_is_not_an_error_for_table_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke([], Path(tmpdir))

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("No Base command history found", stdout)

    def test_invalid_options_report_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke(["--limit", "0"], Path(tmpdir))
            format_status, _format_stdout, format_stderr = invoke(["--format", "yaml"], Path(tmpdir))

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Option '--limit' must be greater than zero", stderr)
        self.assertEqual(format_status, 2)
        self.assertIn("Unsupported output format 'yaml'", format_stderr)

    def test_click_usage_errors_use_delegated_display_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stderr = io.StringIO()
            env = {
                "BASE_CACHE_DIR": tmpdir,
                "BASE_CLI_DISPLAY_COMMAND": "basectl history",
            }
            with mock.patch.dict(os.environ, env):
                with redirect_stderr(stderr):
                    status = engine.main(["unexpected"])

        self.assertEqual(status, 2)
        self.assertIn("Usage: basectl history", stderr.getvalue())
        self.assertNotIn("python -m base_history", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
