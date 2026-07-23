from __future__ import annotations

from . import command_filters, command_protocol, history, testing
from .app import App, argument, command, delegated_display_command, option, run_app
from .command_filters import command_matches, normalize_command_filter, normalize_command_filters
from .command_protocol import CommandProtocolError, dumps_record, dumps_records, loads_records
from .config import UserConfig, UserGithubConfig, UserIdeConfig, UserIdePreference, UserWorkspaceConfig
from .context import Context, get_current_context
from .exit_codes import ExitCode
from .inspection import inspection_envelope, render_inspection_json
from .logging import configure_logger, log_critical, log_debug, log_error, log_info, log_warning
from .output import (
    OutputFormatError,
    PUBLIC_OUTPUT_FORMATS,
    is_terminal,
    output_format_choices,
    render_document,
    render_records,
    resolve_output_format,
)

__all__ = [
    "App",
    "CommandProtocolError",
    "Context",
    "ExitCode",
    "UserConfig",
    "UserGithubConfig",
    "UserIdeConfig",
    "UserIdePreference",
    "UserWorkspaceConfig",
    "command_filters",
    "command_matches",
    "command_protocol",
    "dumps_record",
    "dumps_records",
    "history",
    "inspection_envelope",
    "render_inspection_json",
    "testing",
    "argument",
    "command",
    "configure_logger",
    "delegated_display_command",
    "get_current_context",
    "log_critical",
    "log_debug",
    "log_error",
    "log_info",
    "log_warning",
    "loads_records",
    "normalize_command_filter",
    "normalize_command_filters",
    "OutputFormatError",
    "PUBLIC_OUTPUT_FORMATS",
    "is_terminal",
    "output_format_choices",
    "option",
    "render_document",
    "render_records",
    "resolve_output_format",
    "run_app",
]
