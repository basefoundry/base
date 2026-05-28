from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from base_clean import engine


class BaseCleanTests(unittest.TestCase):
    def test_parse_age_accepts_supported_units(self) -> None:
        self.assertEqual(engine.parse_age("30d"), 30 * 24 * 60 * 60)
        self.assertEqual(engine.parse_age("12h"), 12 * 60 * 60)
        self.assertEqual(engine.parse_age("45m"), 45 * 60)
        self.assertEqual(engine.parse_age("60s"), 60)

    def test_parse_age_rejects_invalid_values(self) -> None:
        for value in ("", "d", "0d", "-1d", "30", "1w"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    engine.parse_age(value)

    def test_parse_keep_last_accepts_positive_integer(self) -> None:
        self.assertEqual(engine.parse_keep_last("20"), 20)

    def test_parse_keep_last_rejects_invalid_values(self) -> None:
        for value in ("", "0", "-1", "ten", "1.5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    engine.parse_keep_last(value)

    def test_find_clean_candidates_only_includes_old_runtime_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            old_log = cache_root / "cli" / "demo" / "logs" / "old.log"
            new_log = cache_root / "cli" / "demo" / "logs" / "new.log"
            old_temp = cache_root / "cli" / "demo" / "tmp" / "old-run"
            old_cache = cache_root / "cli" / "demo" / "cache" / "old-cache"
            durable_state = cache_root / "durable-state" / ".base.d" / "cli" / "demo" / "logs" / "durable.log"

            old_temp.mkdir(parents=True)
            old_cache.mkdir(parents=True)
            old_log.parent.mkdir(parents=True, exist_ok=True)
            durable_state.parent.mkdir(parents=True)
            for path in (old_log, new_log, durable_state):
                path.write_text("x", encoding="utf-8")

            old_time = time.time() - 40 * 24 * 60 * 60
            new_time = time.time()
            for path in (old_log, old_temp, old_cache, durable_state):
                os.utime(path, (old_time, old_time))
            os.utime(new_log, (new_time, new_time))

            candidates = engine.find_clean_candidates(cache_root, time.time() - 30 * 24 * 60 * 60)

        self.assertEqual(
            [(candidate.category, candidate.path.name) for candidate in candidates],
            [("cache", "old-cache"), ("log", "old.log"), ("temp", "old-run")],
        )

    def test_find_clean_candidates_logs_examined_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            (cache_root / "cli" / "demo" / "logs").mkdir(parents=True)
            logger = mock.Mock()

            engine.find_clean_candidates(cache_root, time.time(), logger)

        logger.debug.assert_any_call("Scanning Base CLI runtime root '%s'.", cache_root / "cli")
        logger.debug.assert_any_call(
            "Scanning %s runtime artifacts in '%s'.",
            "log",
            cache_root / "cli" / "demo" / "logs",
        )
        logger.debug.assert_any_call(
            "Scanning %s runtime artifacts in '%s'.",
            "temp",
            cache_root / "cli" / "demo" / "tmp",
        )
        logger.debug.assert_any_call(
            "Scanning %s runtime artifacts in '%s'.",
            "cache",
            cache_root / "cli" / "demo" / "cache",
        )

    def test_find_log_retention_candidates_keeps_newest_logs_per_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            demo_logs = cache_root / "cli" / "demo" / "logs"
            other_logs = cache_root / "cli" / "other" / "logs"
            demo_logs.mkdir(parents=True)
            other_logs.mkdir(parents=True)
            demo_old = demo_logs / "demo-1.log"
            demo_middle = demo_logs / "demo-2.log"
            demo_new = demo_logs / "demo-3.log"
            demo_notes = demo_logs / "notes.txt"
            other_old = other_logs / "other-1.log"
            other_new = other_logs / "other-2.log"
            for path in (demo_old, demo_middle, demo_new, demo_notes, other_old, other_new):
                path.write_text("x", encoding="utf-8")

            now = time.time()
            for offset, path in enumerate((demo_old, demo_middle, demo_new, other_old, other_new), start=1):
                timestamp = now - (10 - offset)
                os.utime(path, (timestamp, timestamp))

            candidates = engine.find_log_retention_candidates(cache_root, keep_count=1)

        self.assertEqual(
            [(candidate.category, candidate.path.name) for candidate in candidates],
            [("log", "demo-1.log"), ("log", "demo-2.log"), ("log", "other-1.log")],
        )

    def test_remove_path_removes_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            file_path = root / "file.log"
            dir_path = root / "run"
            file_path.write_text("x", encoding="utf-8")
            dir_path.mkdir()
            (dir_path / "temp.txt").write_text("x", encoding="utf-8")

            engine.remove_path(file_path)
            engine.remove_path(dir_path)

            self.assertFalse(file_path.exists())
            self.assertFalse(dir_path.exists())

    def test_clean_dry_run_reports_without_removing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            old_log = cache_root / "cli" / "demo" / "logs" / "old.log"
            old_log.parent.mkdir(parents=True)
            old_log.write_text("x", encoding="utf-8")
            old_time = time.time() - 40 * 24 * 60 * 60
            os.utime(old_log, (old_time, old_time))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--older-than", "30d", "--dry-run"])

            self.assertEqual(result, 0)
            self.assertTrue(old_log.exists())

    def test_clean_removes_old_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            old_log = cache_root / "cli" / "demo" / "logs" / "old.log"
            old_log.parent.mkdir(parents=True)
            old_log.write_text("x", encoding="utf-8")
            old_time = time.time() - 40 * 24 * 60 * 60
            os.utime(old_log, (old_time, old_time))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--older-than", "30d"])

            self.assertEqual(result, 0)
            self.assertFalse(old_log.exists())

    def test_clean_keep_last_removes_old_logs_but_keeps_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            logs_dir = cache_root / "cli" / "demo" / "logs"
            logs_dir.mkdir(parents=True)
            old_log = logs_dir / "old.log"
            new_log = logs_dir / "new.log"
            for path in (old_log, new_log):
                path.write_text("x", encoding="utf-8")
            now = time.time()
            os.utime(old_log, (now - 10, now - 10))
            os.utime(new_log, (now, now))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--keep-last", "1"])

            self.assertEqual(result, 0)
            self.assertFalse(old_log.exists())
            self.assertTrue(new_log.exists())

    def test_clean_deduplicates_age_and_retention_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            old_log = cache_root / "cli" / "demo" / "logs" / "old.log"
            old_log.parent.mkdir(parents=True)
            old_log.write_text("x", encoding="utf-8")
            old_time = time.time() - 40 * 24 * 60 * 60
            os.utime(old_log, (old_time, old_time))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--older-than", "30d", "--keep-last", "1"])

            self.assertEqual(result, 0)
            self.assertFalse(old_log.exists())

    def test_clean_invalid_older_than_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(Path(tmpdir) / "cache-root")}):
                result = engine.main(["--older-than", "forever"])

        self.assertEqual(result, 2)

    def test_clean_missing_older_than_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(Path(tmpdir) / "cache-root")}):
                result = engine.main([])

        self.assertEqual(result, 2)

    def test_clean_invalid_keep_last_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(Path(tmpdir) / "cache-root")}):
                result = engine.main(["--keep-last", "many"])

        self.assertEqual(result, 2)

    def test_clean_click_usage_errors_do_not_traceback(self) -> None:
        result = engine.main(["--unknown"])

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
