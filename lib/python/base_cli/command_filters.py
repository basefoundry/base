"""Shared command-name filter normalization for Base reports."""

from __future__ import annotations


def normalize_command_filter(value: str) -> str:
    """Normalize one public or internal command name for matching."""

    normalized = value.strip().lower().removeprefix("base_")
    return normalized.replace("_", "-")


def normalize_command_filters(value: str | None) -> tuple[str, ...]:
    """Normalize a comma-separated command filter and reject empty entries."""

    if value is None:
        return ()
    parts = value.split(",")
    if any(not part.strip() for part in parts):
        raise ValueError("Option '--command' expects comma-separated command names without empty entries.")
    normalized = tuple(dict.fromkeys(normalize_command_filter(part) for part in parts))
    if not normalized or any(not command for command in normalized):
        raise ValueError("Option '--command' expects at least one command name.")
    return normalized


def command_matches(value: str, command_filters: tuple[str, ...]) -> bool:
    """Return whether a command value matches one of the normalized filters."""

    return normalize_command_filter(value) in command_filters
