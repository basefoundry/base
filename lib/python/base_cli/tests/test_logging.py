from __future__ import annotations

import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import base_cli
from base_cli.logging import BaseCliFormatter


class ConfigureLoggerTests(unittest.TestCase):
    def test_configure_logger_accepts_custom_stream(self) -> None:
        stream = io.StringIO()
        logger = base_cli.configure_logger("custom-stream", None, debug=False, stream=stream)

        logger.info("hello stream")

        self.assertIn("INFO", stream.getvalue())
        self.assertIn("hello stream", stream.getvalue())

    def test_configure_logger_accepts_custom_formatter(self) -> None:
        stream = io.StringIO()
        formatter = logging.Formatter("%(levelname)s:%(message)s")
        logger = base_cli.configure_logger("custom-formatter", None, debug=False, stream=stream, formatter=formatter)

        logger.info("hello formatter")

        self.assertEqual(stream.getvalue().strip(), "INFO:hello formatter")

    def test_configure_logger_defaults_to_stderr_and_base_formatter(self) -> None:
        stream = io.StringIO()

        with mock.patch.object(sys, "stderr", stream):
            logger = base_cli.configure_logger("default-stream", None, debug=False)
            logger.info("hello default")

        handler = logger.handlers[0]
        self.assertIsInstance(handler.formatter, BaseCliFormatter)
        self.assertIn("INFO", stream.getvalue())
        self.assertIn("hello default", stream.getvalue())

    def test_configure_logger_uses_custom_formatter_for_file_handler(self) -> None:
        formatter = logging.Formatter("%(levelname)s:%(message)s")
        user_stream = io.StringIO()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = base_cli.configure_logger(
                "custom-file-formatter",
                log_file,
                debug=False,
                stream=user_stream,
                formatter=formatter,
            )
            logger.info("hello file")
            for handler in logger.handlers:
                handler.flush()

            log_text = log_file.read_text(encoding="utf-8")

        self.assertEqual(user_stream.getvalue().strip(), "INFO:hello file")
        self.assertEqual(log_text.strip(), "INFO:hello file")
