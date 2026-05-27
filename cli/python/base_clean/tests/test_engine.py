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

    def test_clean_click_usage_errors_do_not_traceback(self) -> None:
        result = engine.main(["--unknown"])

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
