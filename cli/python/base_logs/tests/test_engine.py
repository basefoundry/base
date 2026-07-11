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


def history_record(  # pylint: disable=too-many-arguments
    run_id: str,
    *,
    command: str = "check",
    raw_command: str = "base_setup",
    status: str = "error",
    exit_code: int = 1,
    ended_at: str = "2026-06-01T01:00:00Z",
    project: str | None = "demo",
    log_path: str | None = "~/logs/run.log",
    argv: list[str] | None = None,
) -> dict:
    payload: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "event": "finished",
        "command": command,
        "raw_command": raw_command,
        "ended_at": ended_at,
        "exit_code": exit_code,
        "status": status,
        "argv": argv if argv is not None else [command],
    }
    if project is not None:
        payload["project"] = project
    if log_path is not None:
        payload["log_path"] = log_path
    return payload


def invoke(args: list[str], cache_root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.dict(
        os.environ,
        {"BASE_CACHE_DIR": str(cache_root), "BASE_CLI_DISPLAY_COMMAND": ""},
    ):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class BaseLogsTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    def test_delegated_unknown_option_usage_uses_basectl_logs(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ,
                {
                    "BASE_CACHE_DIR": str(Path(tmpdir)),
                    "BASE_CLI_DISPLAY_COMMAND": "basectl logs",
                },
            ), redirect_stderr(stderr):
                status = engine.main(["--bad-option"])

        self.assertEqual(status, 2)
        self.assertIn("Usage: basectl logs", stderr.getvalue())
        self.assertIn("No such option '--bad-option'.", stderr.getvalue())
        self.assertNotIn("python -m base_logs", stderr.getvalue())
        self.assertNotIn("base_logs", stderr.getvalue())

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

    def test_history_command_overrides_base_setup_log_action_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            run_id = "20260601T010000_aaaaaaaa"
            log_path = write_log(
                cache_root,
                "base_setup",
                run_id,
                "2026-06-01 01:00:00 DEBUG argv=['base_setup']\n",
            )
            write_history_line(
                cache_root,
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "event": "finished",
                    "command": "check",
                    "raw_command": "base_setup",
                    "ended_at": "2026-06-01T01:00:02Z",
                    "exit_code": 0,
                    "status": "ok",
                    "log_path": str(log_path),
                },
            )

            entries = engine.recent_logs(cache_root)
            filtered = engine.recent_logs(cache_root, command_filter="check")

        self.assertEqual(entries[0].command, "check")
        self.assertEqual([entry.path for entry in filtered], [log_path])

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

    def test_last_prints_latest_failed_history_record_with_redacted_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            older_log = write_log(cache_root, "base_setup", "20260601T010000_aaaaaaaa", "old failure\n")
            newer_log = write_log(
                cache_root,
                "base_setup",
                "20260601T010200_bbbbbbbb",
                "\n".join(
                    [
                        "line 1",
                        "line 2",
                        "token=secret-token",
                        "fetch https://user:pass@example.com/repo.git",
                    ]
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010000_aaaaaaaa",
                    ended_at="2026-06-01T01:00:00Z",
                    log_path=str(older_log),
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010100_okokokok",
                    status="ok",
                    exit_code=0,
                    ended_at="2026-06-01T01:01:00Z",
                    log_path=str(cache_root / "cli" / "base_setup" / "logs" / "ok.log"),
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010200_bbbbbbbb",
                    ended_at="2026-06-01T01:02:00Z",
                    log_path=str(newer_log),
                    argv=["check", "--github-token", "token-secret", "url=https://user:pass@example.com/repo.git"],
                ),
            )

            status, stdout, stderr = invoke(["last", "--lines", "2"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Latest failed Base command", stdout)
        self.assertIn("Command: check", stdout)
        self.assertIn("Project: demo", stdout)
        self.assertIn("Exit: 1", stdout)
        self.assertIn("Log tail (last 2 lines (truncated)):", stdout)
        self.assertNotIn("line 1", stdout)
        self.assertNotIn("secret-token", stdout)
        self.assertNotIn("token-secret", stdout)
        self.assertNotIn("user:pass", stdout)
        self.assertIn("token=[REDACTED]", stdout)
        self.assertIn("https://[REDACTED]@example.com/repo.git", stdout)
        self.assertIn("--github-token [REDACTED]", stdout)

    def test_last_reports_no_failure_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010000_aaaaaaaa",
                    status="ok",
                    exit_code=0,
                    log_path=str(cache_root / "cli" / "base_setup" / "logs" / "ok.log"),
                ),
            )

            status, stdout, stderr = invoke(["last"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("No failed Base command history found", stdout)

    def test_last_reports_missing_log_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            missing_log = cache_root / "cli" / "base_setup" / "logs" / "missing.log"
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010000_aaaaaaaa",
                    log_path=str(missing_log),
                    argv=["check", "API_KEY=plain-secret"],
                ),
            )

            status, stdout, stderr = invoke(["last"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Log:", stdout)
        self.assertIn("(missing)", stdout)
        self.assertIn("recorded log file is missing or was cleaned", stdout)
        self.assertNotIn("plain-secret", stdout)
        self.assertIn("API_KEY=[REDACTED]", stdout)

    def test_last_json_output_has_stable_shape_and_redacted_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            log_path = write_log(
                cache_root,
                "base_setup",
                "20260601T010000_aaaaaaaa",
                "ok\npassword=db-secret\n",
            )
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010000_aaaaaaaa",
                    log_path=str(log_path),
                    argv=["check", "--token=token-secret"],
                ),
            )

            status, stdout, stderr = invoke(["last", "--format", "json", "--lines", "1"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["run"]["command"], "check")
        self.assertEqual(payload["run"]["project"], "demo")
        self.assertTrue(payload["run"]["log_exists"])
        self.assertEqual(payload["run"]["argv"], ["check", "--token=[REDACTED]"])
        self.assertEqual(payload["tail"]["requested_lines"], 1)
        self.assertTrue(payload["tail"]["truncated"])
        self.assertEqual(payload["tail"]["lines"], ["password=[REDACTED]"])
        self.assertNotIn("db-secret", stdout)
        self.assertNotIn("token-secret", stdout)

    def test_last_json_reports_no_failure_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = invoke(["last", "--format", "json"], Path(tmpdir))

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertFalse(payload["found"])
        self.assertIn("history_path", payload)

    def test_last_can_filter_failures_by_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            check_log = write_log(cache_root, "base_setup", "20260601T010000_aaaaaaaa", "check failed\n")
            release_log = write_log(cache_root, "base_release", "20260601T010100_bbbbbbbb", "release failed\n")
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010000_aaaaaaaa",
                    command="check",
                    raw_command="base_setup",
                    ended_at="2026-06-01T01:00:00Z",
                    log_path=str(check_log),
                ),
            )
            write_history_line(
                cache_root,
                history_record(
                    "20260601T010100_bbbbbbbb",
                    command="release",
                    raw_command="base_release",
                    ended_at="2026-06-01T01:01:00Z",
                    log_path=str(release_log),
                ),
            )

            status, stdout, stderr = invoke(["last", "--command", "check"], cache_root)

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Command: check", stdout)
        self.assertIn("check failed", stdout)
        self.assertNotIn("release failed", stdout)

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

    def test_last_rejects_file_actions_and_unknown_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            status, stdout, stderr = invoke(["last", "--path"], cache_root)
            format_status, format_stdout, format_stderr = invoke(["last", "--format", "xml"], cache_root)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("does not accept --path", stderr)
        self.assertEqual(format_status, 2)
        self.assertEqual(format_stdout, "")
        self.assertIn("Unsupported output format 'xml'", format_stderr)

    def test_json_format_is_only_supported_for_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            write_log(cache_root, "base_clean", "20260601T010000_aaaaaaaa", "INFO clean\n")

            status, stdout, stderr = invoke(["--format", "json"], cache_root)

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("only supported with `basectl logs last`", stderr)

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
