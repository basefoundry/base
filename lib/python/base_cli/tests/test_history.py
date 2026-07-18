from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import base_cli
from base_cli import history as history_helpers


def read_history_records(cache_root: Path) -> list[dict]:
    history_path = cache_root / "history" / "runs.jsonl"
    return [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]


class BaseCliHistoryTests(unittest.TestCase):
    def test_shared_history_helpers_parse_records_and_display_paths(self) -> None:
        payload = {
            "schema_version": 1,
            "event": "finished",
            "run_id": "run-1",
            "command": "check",
            "status": "ok",
            "exit_code": 0,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            inside_home = home / "logs" / "run.log"
            outside_home = Path(tmpdir) / "outside" / "run.log"
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                self.assertEqual(
                    history_helpers.parse_finished_history_record_line(json.dumps(payload)),
                    payload,
                )
                self.assertIsNone(history_helpers.parse_finished_history_record_line("{not json"))
                self.assertIsNone(
                    history_helpers.parse_finished_history_record_line(
                        json.dumps({**payload, "event": "started"})
                    )
                )
                self.assertEqual(history_helpers.display_command("base_setup", ["--action", "check"]), "check")
                self.assertEqual(history_helpers.compact_path(inside_home), "~/logs/run.log")
                self.assertEqual(
                    history_helpers.compact_path(outside_home),
                    str(outside_home.expanduser().resolve(strict=False)),
                )

    def test_write_history_record_uses_locked_append_payload(self) -> None:
        record = {
            "schema_version": 1,
            "event": "finished",
            "run_id": "run-1",
            "command": "check",
            "status": "ok",
            "exit_code": 0,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache"
            real_os_write = os.write
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                with mock.patch("base_cli.history._fcntl") as fcntl_module:
                    fcntl_module.LOCK_EX = 1
                    fcntl_module.LOCK_UN = 8
                    with mock.patch("base_cli.history.os.write", wraps=real_os_write) as os_write:
                        history_helpers.write_history_record(record)

            history_path = cache_root / "history" / "runs.jsonl"
            payloads = [call.args[1] for call in os_write.call_args_list]
            history_mode = history_path.stat().st_mode & 0o777

        fcntl_module.flock.assert_has_calls(
            [
                mock.call(mock.ANY, fcntl_module.LOCK_EX),
                mock.call(mock.ANY, fcntl_module.LOCK_UN),
            ]
        )
        self.assertEqual(len(payloads), 1)
        self.assertTrue(payloads[0].endswith(b"\n"))
        self.assertEqual(json.loads(payloads[0]), record)
        self.assertEqual(history_mode, 0o600)

    def test_write_history_record_appends_without_fcntl(self) -> None:
        record = {
            "schema_version": 1,
            "event": "finished",
            "run_id": "run-1",
            "command": "check",
            "status": "ok",
            "exit_code": 0,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache"
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                with mock.patch("base_cli.history._fcntl", None):
                    history_helpers.write_history_record(record)

            history_mode = (cache_root / "history" / "runs.jsonl").stat().st_mode & 0o777
            records = read_history_records(cache_root)

        self.assertEqual(records, [record])
        self.assertEqual(history_mode, 0o600)

    def test_write_primary_record_preserves_user_command_and_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache"
            project_root = Path(tmpdir) / "work" / "demo"
            manifest = project_root / "base_manifest.yaml"
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                history_helpers.write_primary_record(
                    command="test",
                    argv=["basectl", "test", "demo"],
                    started_at=history_helpers.utc_now(),
                    exit_code=1,
                    run_id="parent-1",
                    project="demo",
                    project_root=str(project_root),
                    manifest=str(manifest),
                )
            record = read_history_records(cache_root)[0]

        self.assertEqual(record["command"], "test")
        self.assertEqual(record["raw_command"], "basectl")
        self.assertEqual(record["scope"], "primary")
        self.assertEqual(record["run_id"], "parent-1")
        self.assertEqual(record["project"], "demo")
        self.assertEqual(record["project_root"], str(project_root.resolve()))
        self.assertEqual(record["manifest"], str(manifest.resolve()))
        self.assertEqual(record["status"], "error")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_records_successful_command_history_with_redacted_metadata(self) -> None:
        app = base_cli.App(name="history-demo", version="0.1.0")
        seen = {}

        @app.command()
        @base_cli.option("--endpoint", required=True)
        @base_cli.option("--token", sensitive=True, required=True)
        def main(ctx: base_cli.Context, endpoint: str, token: str) -> None:
            seen["endpoint"] = endpoint
            seen["token"] = token
            seen["run_id"] = ctx.run_id
            ctx.log.info("processed request")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            project = home / "work" / "demo"
            home.mkdir()
            project.mkdir(parents=True)

            from base_cli.testing import invoke

            with mock.patch.object(
                os.sys,
                "argv",
                [
                    "history-demo",
                    "--endpoint",
                    "https://user:super-secret@example.invalid/path",
                    "--token",
                    "super-secret",
                ],
            ):
                result = invoke(
                    app,
                    [
                        "--endpoint",
                        "https://user:super-secret@example.invalid/path",
                        "--token",
                        "super-secret",
                    ],
                    home=home,
                    cwd=project,
                    manifest={"project": {"name": "demo"}},
                )

            records = read_history_records(home / ".cache" / "base")

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["event"], "finished")
        self.assertEqual(record["run_id"], seen["run_id"])
        self.assertEqual(record["command"], "history-demo")
        self.assertEqual(record["raw_command"], "history-demo")
        self.assertEqual(record["project"], "demo")
        self.assertEqual(record["project_root"], "~/work/demo")
        self.assertEqual(record["manifest"], "~/work/demo/base_manifest.yaml")
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["status"], "ok")
        self.assertTrue(record["duration_ms"] >= 0)
        self.assertTrue(record["log_path"].startswith("~/.cache/base/cli/history-demo/logs/"))
        self.assertIn("[REDACTED]", record["argv"])
        self.assertIn("https://[REDACTED]@example.invalid/path", record["argv"])
        self.assertNotIn("super-secret", json.dumps(record))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_records_internal_scope_and_parent_run_id(self) -> None:
        app = base_cli.App(name="history-internal")

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            self.assertEqual(ctx.history_scope, "internal")
            self.assertEqual(ctx.history_parent_run_id, "parent-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "BASE_CACHE_DIR": str(home / ".cache" / "base"),
                    "BASE_CLI_HISTORY_SCOPE": "internal",
                    "BASE_CLI_HISTORY_PARENT_RUN_ID": "parent-1",
                },
            ):
                status = base_cli.run_app(app, [])
            records = read_history_records(home / ".cache" / "base")

        self.assertEqual(status, 0)
        self.assertEqual(records[0]["scope"], "internal")
        self.assertEqual(records[0]["parent_run_id"], "parent-1")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_run_app_uses_explicit_argv_for_history_and_log_metadata(self) -> None:
        app = base_cli.App(name="history-explicit", version="0.1.0")
        seen = {}
        current_endpoint = "https://current.example/path"
        stale_endpoint = "https://stale.invalid/path"

        @app.command()
        @base_cli.option("--endpoint", required=True)
        @base_cli.option("--token", sensitive=True, required=True)
        def main(ctx: base_cli.Context, endpoint: str, token: str) -> None:
            seen["endpoint"] = endpoint
            seen["token"] = token
            seen["log_file"] = ctx.log_file
            ctx.log.info("processed request")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            stderr = io.StringIO()
            with mock.patch.dict(
                os.environ,
                {"HOME": str(home), "BASE_CACHE_DIR": str(home / ".cache" / "base")},
            ):
                with mock.patch.object(
                    os.sys,
                    "argv",
                    ["stale-wrapper", "--debug", "--endpoint", stale_endpoint, "--token", "stale-secret"],
                ):
                    with redirect_stderr(stderr):
                        status = base_cli.run_app(
                            app,
                            ["--debug", "--endpoint", current_endpoint, "--token", "super-secret"],
                        )
            records = read_history_records(home / ".cache" / "base")
            log_text = seen["log_file"].read_text(encoding="utf-8")

        self.assertEqual(status, 0, stderr.getvalue())
        self.assertEqual(seen["endpoint"], current_endpoint)
        self.assertEqual(seen["token"], "super-secret")
        self.assertEqual(len(records), 1)
        record_text = json.dumps(records[0])
        self.assertIn(current_endpoint, record_text)
        self.assertNotIn(stale_endpoint, record_text)
        self.assertNotIn("super-secret", record_text)
        self.assertNotIn("stale-secret", record_text)
        self.assertIn(current_endpoint, log_text)
        self.assertNotIn(stale_endpoint, log_text)
        self.assertNotIn("super-secret", log_text)
        self.assertNotIn("stale-secret", log_text)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_records_failed_command_history(self) -> None:
        app = base_cli.App(name="failing-history")

        @app.command()
        def main(ctx: base_cli.Context) -> int:
            ctx.log.error("planned failure")
            return 7

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            stderr = io.StringIO()
            with mock.patch.dict(
                os.environ,
                {"HOME": str(home), "BASE_CACHE_DIR": str(home / ".cache" / "base")},
            ):
                with redirect_stderr(stderr):
                    status = base_cli.run_app(app, [])
            records = read_history_records(home / ".cache" / "base")

        self.assertEqual(status, 7, stderr.getvalue())
        self.assertEqual(records[0]["command"], "failing-history")
        self.assertEqual(records[0]["exit_code"], 7)
        self.assertEqual(records[0]["status"], "error")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_app_history_write_failures_do_not_fail_command(self) -> None:
        app = base_cli.App(name="history-best-effort")

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            ctx.log.info("still succeeds")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            from base_cli.testing import invoke

            with mock.patch("base_cli.history.write_history_record", side_effect=OSError("permission denied")):
                result = invoke(app, [], home=home)

        self.assertEqual(result.exit_code, 0, result.output)


if __name__ == "__main__":
    unittest.main()
