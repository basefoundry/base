from __future__ import annotations

import re


CURRENT_MANIFEST_SCHEMA_VERSION = 1
ENVIRONMENT_VARIABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMMAND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HOMEBREW_PACKAGE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.+-]+$")
PORT_HEALTH_STATES = {"free", "listening"}
SUPPORTED_PYTHON_MANAGERS = {"uv"}
SUPPORTED_PYTHON_VENV_LOCATIONS = {"external", "project"}
SUPPORTED_COMMAND_RUNNERS = {"uv"}
PROJECT_LANGUAGE_ALIASES = {
    "c": "c",
    "c++": "cpp",
    "cpp": "cpp",
    "go": "go",
    "golang": "go",
    "java": "java",
    "javascript": "javascript",
    "js": "javascript",
    "python": "python",
    "typescript": "typescript",
    "ts": "typescript",
}
SUPPORTED_PROJECT_LANGUAGES = frozenset(PROJECT_LANGUAGE_ALIASES.values())


def normalize_project_language(value: str) -> str | None:
    """Return the canonical project language identifier for a user value."""

    return PROJECT_LANGUAGE_ALIASES.get(value.strip().lower())


def has_control_line_break(value: str) -> bool:
    return any(separator in value for separator in ("\0", "\n", "\r"))
