from __future__ import annotations

import json
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_yaml_file
from .context import Context
from .paths import base_cache_root
from .redaction import REDACTED, option_name_to_parameter, redact_argv


SCHEMA_VERSION = 1
HISTORY_PATH = Path("history") / "runs.jsonl"
SECRET_KEY_RE = re.compile(r"(token|password|secret|api[-_]?key|authorization)", re.IGNORECASE)
URL_CREDENTIALS_RE = re.compile(r"://[^/@\s]+@")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def write_finished_record(
    context: Context,
    argv: list[str],
    sensitive_options: set[str],
    started_at: datetime,
    exit_code: int,
) -> None:
    if context.dry_run or context.log_file is None:
        return
    try:
        record = build_finished_record(context, argv, sensitive_options, started_at, exit_code)
        write_history_record(record)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        context.log.debug("Unable to write command history record: %s", exc)


def build_finished_record(
    context: Context,
    argv: list[str],
    sensitive_options: set[str],
    started_at: datetime,
    exit_code: int,
) -> dict[str, Any]:
    ended_at = utc_now()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": context.run_id,
        "event": "finished",
        "command": display_command(context.cli_name, argv),
        "raw_command": context.cli_name,
        "argv": redact_history_argv(argv, sensitive_options),
        "started_at": format_timestamp(started_at),
        "ended_at": format_timestamp(ended_at),
        "duration_ms": duration_ms(started_at, ended_at),
        "exit_code": exit_code,
        "status": "ok" if exit_code == 0 else "error",
        "log_path": compact_path(context.log_file),
        "os": normalized_os(),
    }
    optional_fields = {
        "project": project_name(context),
        "project_root": compact_optional_path(context.project_root),
        "manifest": compact_optional_path(context.manifest_path),
        "workspace_root": compact_optional_path(context.workspace_root),
        "base_version": base_version(context.base_home),
        "shell": os.environ.get("SHELL"),
    }
    record.update({key: value for key, value in optional_fields.items() if value})
    return record


def write_history_record(record: dict[str, Any]) -> None:
    path = base_cache_root() / HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")
    path.chmod(0o600)


def format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def duration_ms(started_at: datetime, ended_at: datetime) -> int:
    return max(0, round((ended_at - started_at).total_seconds() * 1000))


def display_command(cli_name: str, argv: list[str]) -> str:
    if cli_name == "base_setup":
        return base_setup_action(argv) or "setup"
    if cli_name.startswith("base_"):
        return cli_name.removeprefix("base_").replace("_", "-")
    return cli_name.replace("_", "-")


def base_setup_action(argv: list[str]) -> str | None:
    for index, arg in enumerate(argv):
        if arg == "--action" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--action="):
            return arg.partition("=")[2]
    return None


def project_name(context: Context) -> str | None:
    if context.manifest_path is None:
        return None
    try:
        data = load_yaml_file(context.manifest_path)
    except (OSError, RuntimeError, ValueError):
        return None
    project_data = data.get("project")
    if not isinstance(project_data, dict):
        return None
    value = project_data.get("name")
    return value if isinstance(value, str) and value else None


def base_version(base_home: Path | None) -> str | None:
    if base_home is None:
        return None
    try:
        version = (base_home / "VERSION").read_text(encoding="utf-8").splitlines()[0].strip()
    except (IndexError, OSError):
        return None
    return version or None


def normalized_os() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system or platform.platform()


def redact_history_argv(argv: list[str], sensitive_options: set[str]) -> list[str]:
    redacted = redact_argv(argv, sensitive_options)
    result: list[str] = []
    redact_next = False
    for arg in redacted:
        if redact_next:
            result.append(REDACTED)
            redact_next = False
            continue

        option, separator, _value = arg.partition("=")
        normalized = option_name_to_parameter(option) if option.startswith("--") else option
        if option.startswith("--") and is_secret_key(normalized):
            if separator:
                result.append(f"{option}={REDACTED}")
            else:
                result.append(option)
                redact_next = True
            continue
        result.append(redact_history_text(arg))
    return result


def redact_history_text(value: str) -> str:
    key, separator, _value = value.partition("=")
    if separator and is_secret_key(key):
        return f"{key}={REDACTED}"
    redacted = URL_CREDENTIALS_RE.sub(f"://{REDACTED}@", value)
    return compact_home_text(redacted)


def is_secret_key(value: str) -> bool:
    return SECRET_KEY_RE.search(value) is not None


def compact_optional_path(path: Path | None) -> str | None:
    if path is None:
        return None
    return compact_path(path)


def compact_path(path: Path) -> str:
    return compact_home_text(str(path.expanduser().resolve(strict=False)))


def compact_home_text(value: str) -> str:
    home = str(Path.home().expanduser().resolve(strict=False))
    if value == home:
        return "~"
    if value.startswith(f"{home}/"):
        return f"~/{value[len(home) + 1:]}"
    return value
