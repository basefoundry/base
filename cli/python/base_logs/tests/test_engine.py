from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_logs import engine


def write_log(cache_root: Path, cli_name: str, run_id: str, text: str) -> Path:
    path = cache_root / "cli" / cli_name / "logs" / f"{run_id}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_history_line(cache_root: Path, payload: dict | str) -> None:
    path = cache_root / "history" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{text}\n")


def invoke(args: list[str], cache_root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class BaseLogsTests(unittest.TestCase):
    def test_recent_logs_sorts_by_run_id_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            old_path = write_log(cache_root, "base_projects", "20260601T010000_aaaaaaaa", "INFO old\n")
            new_path = write_log(cache_root, "base_clean", "20260601T010100_bbbbbbbb", "INFO new\n")

            entries = engine.recent_logs(cache_root)

        self.assertEqual([entry.path for entry in entries], [new_path, old_path])
        self.assertEqual([entry.command for entry in entries], ["clean", "projects"])

    def test_base_setup_command_is_inferred_from_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            check_path = write_log(
                cache_root,
                "base_setup",
                "20260601T010000_aaaaaaaa",
                "2026-06-01 01:00:00 DEBUG argv=['base_setup', '--action', 'check']\n",
            )
            setup_path = write_log(
                cache_root,
                "base_setup",
                "20260601T010100_bbbbbbbb",
                "2026-06-01 01:01:00 DEBUG argv=['base_setup']\n",
            )

            entries = engine.recent_logs(cache_root)
            check_entries = engine.recent_logs(cache_root, command_filter="check")

        self.assertEqual({entry.path: entry.command for entry in entries}, {check_path: "check", setup_path: "setup"})
        self.assertEqual([entry.path for entry in check_entries], [check_path])

    def test_status_comes_from_last_log_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_log(
                cache_root,
                "base_setup",
                "20260601T010000_aaaaaaaa",
                "\n".join(
                    [
                        "2026-06-01 01:00:00 INFO start",
                        "2026-06-01 01:00:01 ERROR failed",
                    ]
                ),
            )

            entries = engine.recent_logs(cache_root)

        self.assertEqual(entries[0].status, "error")

    def test_history_status_overrides_last_log_line_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            run_id = "20260601T010000_aaaaaaaa"
            log_path = write_log(
                cache_root,
                "base_release",
                run_id,
                "\n".join(
                    [
                        "2026-06-01 01:00:00 INFO preparing release",
                        "2026-06-01 01:00:01 INFO wrote release plan",
                    ]
                ),
            )
            write_history_line(cache_root, "{not json")
            write_history_line(
                cache_root,
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "event": "finished",
                    "command": "release",
                    "raw_command": "base_release",
                    "ended_at": "2026-06-01T01:00:02Z",
                    "exit_code": 2,
                    "status": "error",
                    "log_path": str(log_path),
                },
            )

            entries = engine.recent_logs(cache_root)
            display_filtered = engine.recent_logs(cache_root, command_filter="release")
            raw_filtered = engine.recent_logs(cache_root, command_filter="base_release")

        self.assertEqual(entries[0].status, "error")
        self.assertEqual([entry.path for entry in display_filtered], [log_path])
        self.assertEqual([entry.path for entry in raw_filtered], [log_path])

    def test_history_status_can_match_by_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            log_path = write_log(
                cache_root,
                "base_clean",
                "20260601T010000_aaaaaaaa",
                "2026-06-01 01:00:01 INFO clean finished\n",
            )
            write_history_line(
                cache_root,
                {
                    "schema_version": 1,
                    "run_id": "history-only-run-id",
                    "event": "finished",
                    "command": "clean",
                    "ended_at": "2026-06-01T01:00:02Z",
                    "exit_code": 1,
                    "status": "error",
                    "log_path": str(log_path),
                },
            )

            entries = engine.recent_logs(cache_root)

        self.assertEqual(entries[0].status, "error")

    def test_default_output_lists_recent_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_log(cache_root, "base_clean", "20260601T010000_aaaaaaaa", "INFO clean\n")

            status, stdout, stderr = invoke([], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("TIME", stdout)
        self.assertIn("COMMAND", stdout)
        self.assertIn("clean", stdout)
        self.assertIn("20260601T010000_aaaaaaaa", stdout)

    def test_path_prints_most_recent_matching_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            older = write_log(cache_root, "base_clean", "20260601T010000_aaaaaaaa", "INFO clean\n")
            newer = write_log(cache_root, "base_projects", "20260601T010100_bbbbbbbb", "INFO projects\n")

            status, stdout, stderr = invoke(["--path"], cache_root)
            filter_status, filter_stdout, filter_stderr = invoke(["--command", "clean", "--path"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout.strip(), str(newer))
        self.assertEqual(filter_status, 0)
        self.assertEqual(filter_stderr, "")
        self.assertEqual(filter_stdout.strip(), str(older))

    def test_empty_log_set_is_not_an_error_for_table_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke([], Path(tmpdir))

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("No Base CLI logs found", stdout)

    def test_debug_uses_base_cli_without_creating_self_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            status, stdout, stderr = invoke(["--debug"], cache_root)

        self.assertEqual(status, 0)
        self.assertIn("No Base CLI logs found", stdout)
        self.assertIn(" DEBUG ", stderr)
        self.assertIn("cli=base_logs", stderr)
        self.assertFalse((cache_root / "cli" / "base_logs").exists())

    def test_path_errors_when_no_log_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke(["--path"], Path(tmpdir))

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No Base CLI logs found", stderr)

    def test_action_options_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_log(cache_root, "base_clean", "20260601T010000_aaaaaaaa", "INFO clean\n")

            status, stdout, stderr = invoke(["--path", "--open"], cache_root)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Choose only one", stderr)

    def test_invalid_count_options_report_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke(["--limit", "0"], Path(tmpdir))
            line_status, line_stdout, line_stderr = invoke(["--lines", "abc", "--tail"], Path(tmpdir))

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Option '--limit' must be greater than zero", stderr)
        self.assertEqual(line_status, 2)
        self.assertEqual(line_stdout, "")
        self.assertIn("Option '--lines' must be a positive integer", line_stderr)
