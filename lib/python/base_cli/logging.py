from __future__ import annotations

import logging
import os
import platform
import sys
import time
from pathlib import Path
from typing import TextIO

from .context import get_current_context
from .paths import current_working_dir
from .redaction import redact_argv

_COLOR_RESET = "\033[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[0;36m",
    logging.INFO: "\033[0;32m",
    logging.WARNING: "\033[0;33m",
    logging.ERROR: "\033[0;31m",
    logging.CRITICAL: "\033[0;31m",
}


# pylint: disable=too-many-arguments
def configure_logger(
    cli_name: str,
    log_file: Path | None,
    debug: bool,
    *,
    quiet: bool = False,
    stream: TextIO | None = None,
    formatter: logging.Formatter | None = None,
) -> logging.Logger:
    logger = logging.getLogger(f"base_cli.{cli_name}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    user_stream = stream if stream is not None else sys.stderr
    user_handler = logging.StreamHandler(user_stream)
    user_handler.setLevel(_user_stream_level(debug, quiet))
    user_handler.setFormatter(_handler_formatter(formatter, use_color=_use_color(user_stream)))
    logger.addHandler(user_handler)

    if log_file is not None:
        file_handler = SecureLogFileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_handler_formatter(formatter, use_color=False))
        logger.addHandler(file_handler)
    return logger


def _user_stream_level(debug: bool, quiet: bool) -> int:
    if quiet:
        return logging.WARNING
    if debug:
        return logging.DEBUG
    return logging.INFO


def _handler_formatter(formatter: logging.Formatter | None, *, use_color: bool) -> logging.Formatter:
    if formatter is not None:
        return formatter
    return BaseCliFormatter(use_color=use_color)


def _use_color(stream: TextIO) -> bool:
    return (
        os.environ.get("BASE_CLI_COLOR") == "1"
        and "NO_COLOR" not in os.environ
        and hasattr(stream, "isatty")
        and stream.isatty()
    )


def secure_log_file_permissions(log_file: Path) -> None:
    log_file.chmod(0o600)


class SecureLogFileHandler(logging.FileHandler):
    def _open(self) -> TextIO:
        fd = os.open(self.baseFilename, _secure_log_file_open_flags(self.mode), 0o600)
        try:
            fchmod = getattr(os, "fchmod", None)
            if fchmod is not None:
                fchmod(fd, 0o600)
            return open(fd, self.mode, encoding=self.encoding, errors=self.errors, closefd=True)
        except BaseException:
            os.close(fd)
            raise


def _secure_log_file_open_flags(mode: str) -> int:
    flags = os.O_CREAT
    if "x" in mode:
        return flags | os.O_EXCL | os.O_WRONLY
    if "w" in mode:
        return flags | os.O_TRUNC | os.O_WRONLY
    return flags | os.O_APPEND | os.O_WRONLY


class BaseCliFormatter(logging.Formatter):
    def __init__(self, *, use_utc: bool | None = None, use_color: bool = False) -> None:
        self.use_utc = use_utc if use_utc is not None else os.environ.get("LOG_UTC") == "1"
        self.use_color = use_color
        datefmt = "%Y-%m-%d %H:%M:%S UTC" if self.use_utc else "%Y-%m-%d %H:%M:%S %z"
        super().__init__(datefmt=datefmt)
        self.converter = time.gmtime if self.use_utc else time.localtime

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        source = _source_path(record)
        level = _level_name(record)
        line = f"{timestamp} {level:<7} {source}:{record.lineno} {record.getMessage()}"
        if not self.use_color:
            return line
        color = _LEVEL_COLORS.get(record.levelno)
        return f"{color}{line}{_COLOR_RESET}" if color else line


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
    project_root = _active_project_root()
    if project_root is not None:
        candidates.append(project_root)
    candidates.append(current_working_dir())

    for root in candidates:
        try:
            return str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            continue
    return str(path.resolve())


def _active_project_root() -> Path | None:
    try:
        context = get_current_context()
    except RuntimeError:
        return None
    return context.project_root


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
