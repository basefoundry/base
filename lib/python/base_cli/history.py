from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - fcntl is unavailable on Windows.
    _fcntl = None  # type: ignore[assignment]

from .config import load_yaml_file
from .context import Context
from .paths import base_cache_root
from .redaction import REDACTED, is_secret_key, option_name_to_parameter, redact_argv, redact_text_value


__all__ = [
    "HISTORY_PATH",
    "HISTORY_SCOPE_INTERNAL",
    "HISTORY_SCOPE_PRIMARY",
    "SCHEMA_VERSION",
    "base_setup_action",
    "base_version",
    "build_finished_record",
    "compact_home_text",
    "compact_optional_path",
    "compact_path",
    "display_command",
    "duration_ms",
    "format_timestamp",
    "optional_int",
    "optional_string",
    "parse_finished_history_record_line",
    "parse_positive_int",
    "project_name",
    "redact_history_argv",
    "redact_history_text",
    "runtime_bundle_path",
    "utc_now",
    "write_finished_record",
    "write_history_record",
    "write_primary_record",
]


SCHEMA_VERSION = 1
HISTORY_PATH = Path("base") / "history" / "runs.jsonl"
HISTORY_SCOPE_PRIMARY = "primary"
HISTORY_SCOPE_INTERNAL = "internal"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def write_finished_record(
    context: Context,
    argv: list[str],
    sensitive_options: set[str],
    started_at: datetime,
    exit_code: int,
) -> None:
    # Base-dispatched child commands share the parent's run bundle and
    # diagnostic stream.  Their completion is an implementation detail, so
    # keep history at the public-invocation level as well.
    if context.dry_run or context.log_file is None or context.history_scope == HISTORY_SCOPE_INTERNAL:
        return
    try:
        record = build_finished_record(context, argv, sensitive_options, started_at, exit_code)
        write_history_record(record)
        if context.run_root is not None:
            update_run_metadata(context.run_root, record)
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
        "owner": context.runtime_owner,
        "bundle_path": compact_path(context.run_root or context.state_dir),
        "os": normalized_os(),
    }
    optional_fields = {
        "project": project_name(context),
        "project_root": compact_optional_path(context.project_root),
        "manifest": compact_optional_path(context.manifest_path),
        "workspace_root": compact_optional_path(context.workspace_root),
        "base_version": base_version(context.base_home),
        "shell": os.environ.get("SHELL"),
        "scope": context.history_scope,
        "parent_run_id": context.history_parent_run_id,
    }
    record.update({key: value for key, value in optional_fields.items() if value})
    return record


# pylint: disable=too-many-arguments,too-many-positional-arguments
def write_primary_record(
    command: str,
    argv: list[str],
    started_at: datetime,
    exit_code: int,
    run_id: str,
    scope: str = HISTORY_SCOPE_PRIMARY,
    project: str | None = None,
    project_root: str | None = None,
    manifest: str | None = None,
    log_path: str | None = None,
    owner: str = "base",
    bundle_path: str | None = None,
) -> None:
    """Write the user-facing record for a Bash-dispatched command."""
    ended_at = utc_now()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "event": "finished",
        "command": command,
        "raw_command": "basectl",
        "argv": redact_history_argv(argv, sensitive_options=set()),
        "started_at": format_timestamp(started_at),
        "ended_at": format_timestamp(ended_at),
        "duration_ms": duration_ms(started_at, ended_at),
        "exit_code": exit_code,
        "status": "ok" if exit_code == 0 else "error",
        "os": normalized_os(),
        "scope": scope,
    }
    resolved_bundle = Path(bundle_path).expanduser() if bundle_path else runtime_bundle_path()
    resolved_log = Path(log_path).expanduser() if log_path else (
        resolved_bundle / "logs" / "primary.log" if resolved_bundle is not None else None
    )
    optional_fields = {
        "project": project,
        "project_root": compact_optional_path(Path(project_root)) if project_root else None,
        "manifest": compact_optional_path(Path(manifest)) if manifest else None,
        "log_path": compact_optional_path(resolved_log),
        "owner": owner,
        "bundle_path": compact_optional_path(resolved_bundle),
    }
    record.update({key: value for key, value in optional_fields.items() if value})
    write_history_record(record)
    if resolved_bundle is not None:
        update_run_metadata(resolved_bundle, record)


def write_history_record(record: dict[str, Any]) -> None:
    path = base_cache_root() / HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    append_history_line(path, f"{json.dumps(record, sort_keys=True)}\n")
    path.chmod(0o600)


def runtime_bundle_path() -> Path | None:
    value = os.environ.get("BASE_CLI_RUN_ROOT")
    if not value:
        return None
    return Path(value).expanduser().resolve(strict=False)


def update_run_metadata(run_root: Path, record: dict[str, Any]) -> None:
    metadata_path = run_root / "run.json"
    metadata: dict[str, Any] = {}
    try:
        if metadata_path.is_file():
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                metadata = loaded
        metadata.update(
            {
                "run_id": record.get("run_id"),
                "owner": record.get("owner", metadata.get("owner", "base")),
                "status": record.get("status"),
                "exit_code": record.get("exit_code"),
                "ended_at": record.get("ended_at"),
                "command": record.get("command"),
            }
        )
        for key in (
            "argv",
            "manifest",
            "parent_run_id",
            "project",
            "project_root",
            "raw_command",
            "scope",
            "workspace_root",
        ):
            if key in record and record[key] is not None:
                metadata[key] = record[key]
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
        metadata_path.chmod(0o600)
    except (OSError, TypeError, ValueError):
        pass


def append_history_line(path: Path, line: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        lock_history_file(fd)
        try:
            write_all(fd, line.encode("utf-8"))
        finally:
            unlock_history_file(fd)
    finally:
        os.close(fd)


def lock_history_file(fd: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(fd, _fcntl.LOCK_EX)


def unlock_history_file(fd: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(fd, _fcntl.LOCK_UN)


def write_all(fd: int, data: bytes) -> None:
    remaining = data
    while remaining:
        written = os.write(fd, remaining)
        if written == 0:
            raise OSError("history append wrote zero bytes")
        remaining = remaining[written:]


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


def parse_positive_int(option: str, value: str) -> int:
    if not value.isdigit():
        raise ValueError(f"Option '{option}' must be a positive integer.")
    amount = int(value)
    if amount <= 0:
        raise ValueError(f"Option '{option}' must be greater than zero.")
    return amount


def parse_finished_history_record_line(line: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        return None
    if payload.get("event") != "finished":
        return None
    return payload


def optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def base_setup_action(argv: list[str]) -> str | None:
    for index, arg in enumerate(argv):
        if arg == "--action" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--action="):
            return arg.partition("=")[2]
    return None


def project_name(context: Context) -> str | None:
    if context.project_name:
        return context.project_name
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
    return compact_home_text(redact_text_value(value))


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
