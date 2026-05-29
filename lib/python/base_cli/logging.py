from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path

from .context import get_current_context
from .redaction import redact_argv


def configure_logger(
    cli_name: str,
    log_file: Path | None,
    debug: bool,
) -> logging.Logger:
    logger = logging.getLogger(f"base_cli.{cli_name}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    user_handler = logging.StreamHandler()
    user_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    user_handler.setFormatter(BaseCliFormatter())
    logger.addHandler(user_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        secure_log_file_permissions(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(BaseCliFormatter())
        logger.addHandler(file_handler)
    return logger


def secure_log_file_permissions(log_file: Path) -> None:
    log_file.chmod(0o600)


class BaseCliFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        source = _source_path(record)
        level = _level_name(record)
        return f"{timestamp} {level:<7} {source}:{record.lineno} {record.getMessage()}"


def _level_name(record: logging.LogRecord) -> str:
    if record.levelno == logging.WARNING:
        return "WARN"
    if record.levelno == logging.CRITICAL:
        return "FATAL"
    return record.levelname


def _source_path(record: logging.LogRecord) -> str:
    path = Path(record.pathname)
    candidates = []
    base_home = os.environ.get("BASE_HOME")
    if base_home:
        candidates.append(Path(base_home))
    candidates.append(Path.cwd())

    for root in candidates:
        try:
            return str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            continue
    return str(path.resolve())


def log_invocation(logger: logging.Logger, argv: list[str], sensitive_options: set[str]) -> None:
    logger.debug("argv=%s", redact_argv(argv, sensitive_options))
    logger.debug("platform=%s %s", platform.system(), platform.machine())
    logger.debug("python=%s", sys.version.replace("\n", " "))


def log_debug(message: str, *args: object) -> None:
    get_current_context().log.debug(message, *args, stacklevel=2)


def log_info(message: str, *args: object) -> None:
    get_current_context().log.info(message, *args, stacklevel=2)


def log_warning(message: str, *args: object) -> None:
    get_current_context().log.warning(message, *args, stacklevel=2)


def log_error(message: str, *args: object) -> None:
    get_current_context().log.error(message, *args, stacklevel=2)


def log_critical(message: str, *args: object) -> None:
    get_current_context().log.critical(message, *args, stacklevel=2)
