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


def read_history_records(cache_root: Path) -> list[dict]:
    history_path = cache_root / "history" / "runs.jsonl"
    return [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]


class BaseCliHistoryTests(unittest.TestCase):
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
