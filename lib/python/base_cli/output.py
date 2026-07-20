"""Shared output-format resolution and rendering for Base CLIs."""

from __future__ import annotations

import csv
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TextIO


PUBLIC_OUTPUT_FORMATS = ("text", "csv", "tsv", "yaml", "json")


class OutputFormatError(ValueError):
    """Raised when a public output format is not supported."""


def output_format_choices() -> str:
    """Return the public choices in help/error-message order."""

    return "|".join(PUBLIC_OUTPUT_FORMATS)


def is_terminal(stream: TextIO | None = None) -> bool:
    """Return whether *stream* is an interactive terminal."""

    candidate = stream if stream is not None else sys.stdout
    try:
        return bool(candidate.isatty())
    except (AttributeError, OSError):
        return False


def resolve_output_format(
    requested: str | None,
    *,
    stream: TextIO | None = None,
) -> str:
    """Resolve a requested format, making text TTY-aware.

    ``text`` is intentionally a presentation mode rather than a wire format:
    it renders a table for terminals and tab-delimited rows for redirected or
    piped output.  Omitting the format follows the same policy.
    """

    normalized = (requested or "text").lower()
    if normalized not in PUBLIC_OUTPUT_FORMATS:
        raise OutputFormatError(
            f"Unsupported output format '{requested}'. Expected one of: {', '.join(PUBLIC_OUTPUT_FORMATS)}."
        )
    if normalized == "text" and not is_terminal(stream):
        return "tsv"
    return normalized


def render_records(
    records: Iterable[Mapping[str, Any]],
    *,
    requested_format: str | None,
    columns: Sequence[tuple[str, str]],
    stream: TextIO | None = None,
    footer: str | None = None,
) -> str:
    """Render records according to the shared public output contract.

    The returned string is also written to *stream* when supplied (or stdout
    when omitted).  JSON and YAML retain the mapping shape supplied by the
    caller; delimited formats use the explicit ``columns`` order and never
    emit a header or footer.
    """

    target = stream if stream is not None else sys.stdout
    record_list = [dict(record) for record in records]
    resolved = resolve_output_format(requested_format, stream=target)

    if resolved in ("csv", "tsv"):
        delimiter = "," if resolved == "csv" else "\t"
        writer = csv.writer(target, delimiter=delimiter, lineterminator="\n")
        for record in record_list:
            writer.writerow([_cell_value(record.get(key)) for _header, key in columns])
        return resolved

    if resolved == "json":
        target.write(json.dumps(record_list, separators=(",", ":")))
        target.write("\n")
        return resolved

    if resolved == "yaml":
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError("PyYAML is required for YAML output.") from exc
        target.write(yaml.safe_dump(record_list, sort_keys=False, allow_unicode=True))
        return resolved

    _write_table(target, record_list, columns, footer)
    return resolved


def _cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _write_table(
    stream: TextIO,
    records: Sequence[Mapping[str, Any]],
    columns: Sequence[tuple[str, str]],
    footer: str | None,
) -> None:
    if not records:
        if footer:
            stream.write(f"{footer}\n")
        return

    widths = [len(header) for header, _key in columns]
    rows: list[list[str]] = []
    for record in records:
        row = [_cell_value(record.get(key)) for _header, key in columns]
        rows.append(row)
        widths = [max(width, len(value)) for width, value in zip(widths, row)]

    stream.write("  ".join(header.ljust(width) for (header, _key), width in zip(columns, widths)).rstrip())
    stream.write("\n")
    for row in rows:
        stream.write("  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())
        stream.write("\n")
    if footer:
        stream.write(f"\n{footer}\n")
