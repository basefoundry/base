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
    path = cache_root / "base" / "history" / "runs.jsonl"
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
    argv: list[str] | None = None,
    scope: str | None = None,
) -> dict:
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "event": "finished",
        "command": command,
        "raw_command": f"base_{command}",
        "argv": argv or ["basectl", command],
        "project": project,
        "ended_at": ended_at,
        "exit_code": exit_code,
        "status": status,
        "log_path": log_path,
    }
    if scope is not None:
        payload["scope"] = scope
    return payload


def invoke(args: list[str], cache_root: Path) -> tuple[int, str, str]:
    stdout = TerminalStringIO()
    stderr = io.StringIO()
    with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


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
        self.assertIn("TIME (UTC)", stdout)
        self.assertIn("COMMAND", stdout)
        self.assertIn("PROJECT", stdout)
        self.assertIn("check", stdout)
        self.assertIn("error", stdout)
        self.assertIn("missing", stdout)

    def test_local_time_changes_text_label_but_json_remains_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(
                cache_root,
                history_record(
                    "run-1",
                    "check",
                    ended_at="2026-06-10T10:15:00Z",
                ),
            )

            status, stdout, stderr = invoke(["--local-time"], cache_root)
            json_status, json_stdout, json_stderr = invoke(["--local-time", "--format", "json"], cache_root)

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("TIME (LOCAL)", stdout)
        self.assertEqual((json_status, json_stderr), (0, ""))
        self.assertEqual(json.loads(json_stdout)[0]["ended_at"], "2026-06-10T10:15:00Z")

    def test_oldest_first_reverses_only_the_selected_recent_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(cache_root, history_record("old", "check", ended_at="2026-06-10T10:00:00Z"))
            write_history_line(cache_root, history_record("middle", "check", ended_at="2026-06-10T10:10:00Z"))
            write_history_line(cache_root, history_record("new", "check", ended_at="2026-06-10T10:20:00Z"))

            status, stdout, stderr = invoke(["--oldest-first", "--limit", "2", "--format", "json"], cache_root)
            payload = json.loads(stdout)

        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual([record["run_id"] for record in payload], ["middle", "new"])

    def test_time_filters_support_explicit_bounds_and_exclusive_until(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(cache_root, history_record("before", "check", ended_at="2026-06-10T09:59:59Z"))
            write_history_line(cache_root, history_record("start", "check", ended_at="2026-06-10T10:00:00Z"))
            write_history_line(cache_root, history_record("inside", "check", ended_at="2026-06-10T10:30:00Z"))
            write_history_line(cache_root, history_record("end", "check", ended_at="2026-06-10T11:00:00Z"))

            status, stdout, stderr = invoke(
                [
                    "--since",
                    "2026-06-10T10:00:00Z",
                    "--until",
                    "2026-06-10T11:00:00Z",
                    "--oldest-first",
                    "--format",
                    "json",
                ],
                cache_root,
            )
            payload = json.loads(stdout)

        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual([record["run_id"] for record in payload], ["start", "inside"])

    def test_last_duration_uses_current_time_as_an_exclusive_upper_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(cache_root, history_record("included", "check", ended_at="2026-06-10T10:00:00Z"))
            write_history_line(cache_root, history_record("excluded", "check", ended_at="2026-06-10T10:15:00Z"))
            current_time = engine.datetime(2026, 6, 10, 10, 15, tzinfo=engine.timezone.utc)

            with mock.patch("base_history.engine.utc_now", return_value=current_time):
                status, stdout, stderr = invoke(["--last", "15m", "--format", "json"], cache_root)
            payload = json.loads(stdout)

        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual([record["run_id"] for record in payload], ["included"])

    def test_short_time_forms_are_parsed_in_the_host_timezone(self) -> None:
        parsed = engine.parse_history_bound("--since", "2026-06-10 10:15")

        self.assertEqual(parsed.tzinfo, engine.timezone.utc)
        self.assertEqual(parsed.minute, 15)

    def test_invalid_time_filters_report_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            last_status, _last_stdout, last_stderr = invoke(
                ["--last", "2h", "--since", "2026-06-10T10:00:00Z"], Path(tmpdir)
            )
            malformed_status, _malformed_stdout, malformed_stderr = invoke(
                ["--since", "tomorrow"], Path(tmpdir)
            )
            reversed_status, _reversed_stdout, reversed_stderr = invoke(
                [
                    "--since",
                    "2026-06-10T11:00:00Z",
                    "--until",
                    "2026-06-10T10:00:00Z",
                ],
                Path(tmpdir),
            )

        self.assertEqual(last_status, 2)
        self.assertIn("cannot be combined", last_stderr)
        self.assertEqual(malformed_status, 2)
        self.assertIn("must be ISO-8601", malformed_stderr)
        self.assertEqual(reversed_status, 2)
        self.assertIn("must be earlier", reversed_stderr)

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

    def test_history_hides_legacy_internal_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(cache_root, history_record("primary", "test"))
            write_history_line(cache_root, history_record("child", "projects", scope="internal"))

            status, stdout, stderr = invoke([], cache_root)
        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("test", stdout)
        self.assertNotIn("projects", stdout)

    def test_empty_history_set_is_not_an_error_for_table_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke([], Path(tmpdir))

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("No Base command history found", stdout)

    def test_markdown_report_handles_empty_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            status, stdout, stderr = invoke(["--report"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("# Base Local Activity Report", stdout)
        self.assertIn("History records: 0", stdout)
        self.assertIn("No command history records found.", stdout)
        self.assertIn(str(cache_root / "base" / "history" / "runs.jsonl"), stdout)

    def test_markdown_report_labels_local_time_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(cache_root, history_record("run-1", "check"))

            status, stdout, stderr = invoke(["--report", "--local-time"], cache_root)

        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("| Time (LOCAL) | Command |", stdout)

    def test_report_json_summarizes_successful_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            log_path = cache_root / "cli" / "base_setup" / "logs" / "run-ok.log"
            log_path.parent.mkdir(parents=True)
            log_path.write_text("ok\n", encoding="utf-8")
            write_history_line(
                cache_root,
                history_record(
                    "run-ok",
                    "check",
                    status="ok",
                    exit_code=0,
                    log_path=str(log_path),
                ),
            )

            status, stdout, stderr = invoke(["--report", "--format", "json"], cache_root)
            payload = json.loads(stdout)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(
            payload["history_path"],
            str((cache_root / "base" / "history" / "runs.jsonl").resolve(strict=False)),
        )
        self.assertEqual(payload["summary"]["record_count"], 1)
        self.assertEqual(payload["summary"]["failure_count"], 0)
        self.assertEqual(payload["summary"]["status_counts"], {"error": 0, "ok": 1, "warn": 0})
        self.assertEqual(payload["command_families"], [{"command": "check", "count": 1, "failures": 0}])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["recent"][0]["log_exists"], True)

    def test_markdown_report_lists_failures_and_common_failing_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(
                cache_root,
                history_record(
                    "run-error-new",
                    "check",
                    status="error",
                    exit_code=2,
                    ended_at="2026-06-10T10:20:00Z",
                    log_path=str(cache_root / "cli" / "base_setup" / "logs" / "run-error-new.log"),
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "run-error-old",
                    "check",
                    status="error",
                    exit_code=1,
                    ended_at="2026-06-10T10:10:00Z",
                    log_path=str(cache_root / "cli" / "base_setup" / "logs" / "run-error-old.log"),
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "run-warn",
                    "setup",
                    status="warn",
                    exit_code=0,
                    ended_at="2026-06-10T10:15:00Z",
                ),
            )

            status, stdout, stderr = invoke(["--report"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Failures: 2", stdout)
        self.assertIn("- `check`: 2 failures across 2 runs", stdout)
        self.assertIn("run-error-new.log", stdout)
        self.assertIn("run-error-old.log", stdout)
        self.assertIn("## Privacy", stdout)
        self.assertIn("Raw log contents are not included", stdout)

    def test_report_redacts_arguments_and_home_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache"
            home = Path(tmpdir) / "home"
            home.mkdir()
            secret = "super-secret-value"
            write_history_line(
                cache_root,
                history_record(
                    "run-secret",
                    "setup",
                    status="error",
                    exit_code=1,
                    log_path=str(home / ".cache" / "base" / "cli" / "base_setup" / "logs" / "run-secret.log"),
                    argv=[
                        "basectl",
                        "setup",
                        "--token",
                        secret,
                        f"DATABASE_PASSWORD={secret}",
                        str(home / "work" / "demo"),
                        f"https://user:{secret}@example.com/private.git",
                    ],
                ),
            )

            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                status, stdout, stderr = invoke(["--report", "--format", "json"], cache_root)
            payload = json.loads(stdout)
            encoded = json.dumps(payload)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertNotIn(secret, encoded)
        self.assertNotIn(str(home), encoded)
        self.assertIn("[REDACTED]", encoded)
        self.assertIn("~/work/demo", encoded)
        self.assertTrue(payload["recent"][0]["log_path"].startswith("~/.cache/base/cli/base_setup/logs/"))

    def test_invalid_options_report_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke(["--limit", "0"], Path(tmpdir))
            format_status, format_stdout, format_stderr = invoke(["--format", "yaml"], Path(tmpdir))
            report_status, report_stdout, report_stderr = invoke(["--report", "--format", "yaml"], Path(tmpdir))

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Option '--limit' must be greater than zero", stderr)
        self.assertEqual(format_status, 0)
        self.assertEqual(format_stderr, "")
        self.assertEqual(report_status, 0)
        self.assertEqual(report_stderr, "")
        self.assertIn("[]", format_stdout)
        self.assertIn("schema_version", report_stdout)

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
