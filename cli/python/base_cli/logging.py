from __future__ import annotations

import logging
import platform
import sys
from pathlib import Path

from .context import get_current_context
from .redaction import redact_argv


def configure_logger(
    cli_name: str,
    log_file: Path,
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
    user_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(user_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    return logger


def log_invocation(logger: logging.Logger, argv: list[str], sensitive_options: set[str]) -> None:
    logger.debug("argv=%s", redact_argv(argv, sensitive_options))
    logger.debug("platform=%s %s", platform.system(), platform.machine())
    logger.debug("python=%s", sys.version.replace("\n", " "))


def log_debug(message: str, *args: object) -> None:
    get_current_context().log.debug(message, *args)


def log_info(message: str, *args: object) -> None:
    get_current_context().log.info(message, *args)


def log_warning(message: str, *args: object) -> None:
    get_current_context().log.warning(message, *args)


def log_error(message: str, *args: object) -> None:
    get_current_context().log.error(message, *args)


def log_critical(message: str, *args: object) -> None:
    get_current_context().log.critical(message, *args)

