from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

import base_cli
from base_cli.testing import invoke


def write_log_file(path: Path, mtime: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old log\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))


class AppLogRetentionTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_prunes_oldest_default_logs(self) -> None:
        app = base_cli.App(name="retention-demo", max_log_files=2)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["log_file"] = ctx.log_file
            ctx.log.info("retention run")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_dir = home / ".cache" / "base" / "base" / "runs" / "seed" / "logs"
            oldest = log_dir / "20260620T120000_oldest.log"
            newest = log_dir / "20260621T120000_newest.log"
            write_log_file(oldest, 1)
            write_log_file(newest, 2)

            result = invoke(app, home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertFalse(oldest.exists())
            self.assertTrue(newest.exists())
            self.assertIsNotNone(seen["log_file"])
            self.assertTrue(seen["log_file"].exists())
            self.assertEqual(len(tuple((home / ".cache" / "base" / "base" / "runs").rglob("*.log"))), 2)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_prunes_by_filename_when_mtimes_disagree(self) -> None:
        app = base_cli.App(name="retention-filename", max_log_files=2)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["log_file"] = ctx.log_file
            ctx.log.info("filename retention")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_dir = home / ".cache" / "base" / "base" / "runs" / "seed" / "logs"
            older_by_name = log_dir / "20260620T120000_old.log"
            newer_by_name = log_dir / "20260621T120000_new.log"
            write_log_file(older_by_name, 2)
            write_log_file(newer_by_name, 1)

            result = invoke(app, home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertFalse(older_by_name.exists())
            self.assertTrue(newer_by_name.exists())
            self.assertIsNotNone(seen["log_file"])
            self.assertTrue(seen["log_file"].exists())
            self.assertEqual(len(tuple((home / ".cache" / "base" / "base" / "runs").rglob("*.log"))), 2)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_preserves_current_log_file(self) -> None:
        app = base_cli.App(name="retention-current", max_log_files=1)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["log_file"] = ctx.log_file
            ctx.log.info("keep current")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_dir = home / ".cache" / "base" / "base" / "runs" / "seed" / "logs"
            old_a = log_dir / "old-a.log"
            old_b = log_dir / "old-b.log"
            write_log_file(old_a, 1)
            write_log_file(old_b, 2)

            result = invoke(app, home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertFalse(old_a.exists())
            self.assertFalse(old_b.exists())
            self.assertIsNotNone(seen["log_file"])
            self.assertTrue(seen["log_file"].exists())
            self.assertEqual(tuple((home / ".cache" / "base" / "base" / "runs").rglob("*.log")), (seen["log_file"],))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_keeps_logs_when_count_is_within_limit(self) -> None:
        app = base_cli.App(name="retention-within-limit", max_log_files=3)
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["log_file"] = ctx.log_file
            ctx.log.info("within retention limit")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_dir = home / ".cache" / "base" / "base" / "runs" / "seed" / "logs"
            old_a = log_dir / "20260620T120000_a.log"
            old_b = log_dir / "20260621T120000_b.log"
            write_log_file(old_a, 1)
            write_log_file(old_b, 2)

            result = invoke(app, home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(old_a.exists())
            self.assertTrue(old_b.exists())
            self.assertIsNotNone(seen["log_file"])
            self.assertTrue(seen["log_file"].exists())
            self.assertEqual(len(tuple((home / ".cache" / "base" / "base" / "runs").rglob("*.log"))), 3)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_is_disabled_by_default(self) -> None:
        app = base_cli.App(name="retention-unset")
        seen = {}

        @app.command()
        def main(ctx: base_cli.Context) -> None:
            seen["log_file"] = ctx.log_file
            ctx.log.info("no retention")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            log_dir = home / ".cache" / "base" / "base" / "runs" / "seed" / "logs"
            old_a = log_dir / "old-a.log"
            old_b = log_dir / "old-b.log"
            write_log_file(old_a, 1)
            write_log_file(old_b, 2)

            result = invoke(app, home=home)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(old_a.exists())
            self.assertTrue(old_b.exists())
            self.assertIsNotNone(seen["log_file"])
            self.assertTrue(seen["log_file"].exists())
            self.assertEqual(len(tuple((home / ".cache" / "base" / "base" / "runs").rglob("*.log"))), 3)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_skips_no_durable_write_modes(self) -> None:
        dry_run_app = base_cli.App(name="retention-dry-run", max_log_files=1)
        dry_seen = {}

        @dry_run_app.command()
        @base_cli.option("--dry-run", is_flag=True)
        def dry_run_main(ctx: base_cli.Context, dry_run: bool) -> None:
            dry_seen["dry_run"] = dry_run
            dry_seen["log_file"] = ctx.log_file
            ctx.log.info("dry retention")

        no_file_app = base_cli.App(
            name="retention-no-file",
            log_to_file=False,
            max_log_files=1,
        )
        no_file_seen = {}

        @no_file_app.command()
        def no_file_main(ctx: base_cli.Context) -> None:
            no_file_seen["log_file"] = ctx.log_file
            ctx.log.info("no file retention")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            dry_log_dir = home / ".cache" / "base" / "base" / "runs" / "dry-seed" / "logs"
            no_file_log_dir = home / ".cache" / "base" / "base" / "runs" / "no-file-seed" / "logs"
            dry_old = dry_log_dir / "old.log"
            no_file_old = no_file_log_dir / "old.log"
            write_log_file(dry_old, 1)
            write_log_file(no_file_old, 1)

            dry_result = invoke(dry_run_app, ["--dry-run"], home=home)
            no_file_result = invoke(no_file_app, home=home)

            self.assertEqual(dry_result.exit_code, 0, dry_result.output)
            self.assertEqual(no_file_result.exit_code, 0, no_file_result.output)
            self.assertTrue(dry_seen["dry_run"])
            self.assertIsNone(dry_seen["log_file"])
            self.assertIsNone(no_file_seen["log_file"])
            self.assertTrue(dry_old.exists())
            self.assertTrue(no_file_old.exists())
            self.assertEqual(tuple(dry_log_dir.glob("*.log")), (dry_old,))
            self.assertEqual(tuple(no_file_log_dir.glob("*.log")), (no_file_old,))
