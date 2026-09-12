"""Compatibility checks for the extracted Base CLI provider."""

from __future__ import annotations

import os
import sys
from dataclasses import fields
from importlib import import_module
from types import ModuleType


REQUIRED_COMMAND_PROTOCOL_SYMBOLS = (
    "BOOLEAN",
    "CommandProtocolError",
    "FieldSpec",
    "NULLABLE_STRING",
    "STRING",
    "dumps_record",
    "dumps_records",
    "loads_records",
    "register_record_schema",
    "RECORD_SCHEMAS",
)


class BaseCliCompatibilityError(ImportError):
    """Raised when the installed base-cli provider cannot serve Base."""


# Base owns this boundary, including the one private provider runtime seam.
REQUIRED_PROVIDER_CAPABILITIES = {
    "base_cli": ("App", "CliProfile", "ProjectInfo", "RuntimeBinding", "ExitCode", "ConfigurationError"),
    "base_cli.command_protocol": REQUIRED_COMMAND_PROTOCOL_SYMBOLS,
    "base_cli._runtime": ("refresh_run_bundle_index",),
    "base_cli.context": ("Context",),
    "base_cli.runtime": ("RuntimeLayout",),
    "base_cli.config": ("load_yaml_file",),
    "base_cli.paths": ("make_run_id", "runtime_run_directory_name", "runtime_slug"),
    "base_cli.command_filters": (
        "CommandFilterNormalizer", "command_matches", "normalize_command_filter", "normalize_command_filters",
    ),
    "base_cli.history": (
        "HISTORY_SCOPE_INTERNAL", "HISTORY_SCOPE_PRIMARY", "SCHEMA_VERSION", "compact_home_text",
        "compact_optional_path", "compact_path", "display_command", "duration_ms", "format_timestamp",
        "optional_int", "optional_string", "parse_finished_history_record_line", "parse_positive_int",
        "redact_history_argv", "redact_history_text", "update_run_metadata", "utc_now", "write_history_record",
    ),
}


PROVIDER_VALUE_SYMBOLS = {
    "BOOLEAN", "NULLABLE_STRING", "STRING", "RECORD_SCHEMAS",
    "HISTORY_SCOPE_INTERNAL", "HISTORY_SCOPE_PRIMARY", "SCHEMA_VERSION",
}


def provider_description() -> str:
    """Identify the selected source without assuming its version guarantees compatibility."""
    provider = sys.modules.get("base_cli")
    location = getattr(provider, "__file__", None)
    source_root = os.environ.get("BASE_CLI_RUNTIME_SOURCE_ROOT")
    kind = os.environ.get("BASE_CLI_SOURCE", "Python import path")
    selected = source_root or location or f"Python environment {sys.executable}"
    return f"{kind} provider at {selected}"


def compatibility_error(problem: str) -> BaseCliCompatibilityError:
    return BaseCliCompatibilityError(
        f"Base's selected base-cli {provider_description()} is incompatible: {problem}. "
        "Install or upgrade base-cli to the release-pinned v0.4.3 provider, or set "
        "BASE_CLI_SOURCE_DIR to a compatible source checkout. Source overrides take "
        "precedence over the installed package; repair or remove an incompatible override."
    )


def load_capabilities(module_name: str) -> ModuleType:
    """Load a provider module and validate Base's required symbols."""
    try:
        module = import_module(module_name)
    except ImportError as exc:
        raise compatibility_error(f"cannot import {module_name}: {exc}") from exc
    missing = [name for name in REQUIRED_PROVIDER_CAPABILITIES[module_name] if not hasattr(module, name)]
    if missing:
        raise compatibility_error(f"{module_name} is missing {', '.join(missing)}")
    for name in REQUIRED_PROVIDER_CAPABILITIES[module_name]:
        if name not in PROVIDER_VALUE_SYMBOLS and not callable(getattr(module, name)):
            raise compatibility_error(f"{module_name}.{name} must be callable")
    return module


def load_command_protocol() -> ModuleType:
    """Load the provider protocol or explain how to repair an incompatible one."""
    return load_capabilities("base_cli.command_protocol")


def load_run_index_runtime() -> ModuleType:
    """Keep the private refresh dependency inside the provider compatibility boundary."""
    return load_capabilities("base_cli._runtime")


def validate_provider() -> None:
    """Check all Base adapter dependencies before dispatching an owned command."""
    for module_name in REQUIRED_PROVIDER_CAPABILITIES:
        load_capabilities(module_name)


def public_context_field_names(context_type: type) -> set[str]:
    """Public Context fields exclude underscore-prefixed state and cleanup hooks."""
    return {
        field.name for field in fields(context_type)
        if not field.name.startswith("_") and field.name != "cleanup_hooks"
    }


__all__ = [
    "BaseCliCompatibilityError", "REQUIRED_COMMAND_PROTOCOL_SYMBOLS", "REQUIRED_PROVIDER_CAPABILITIES",
    "load_command_protocol", "load_run_index_runtime", "public_context_field_names", "validate_provider",
]
