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


# pylint: disable=too-many-arguments
def render_records(
    records: Iterable[Mapping[str, Any]],
    *,
    requested_format: str | None,
    columns: Sequence[tuple[str, str]],
    stream: TextIO | None = None,
    footer: str | None = None,
    minimum_widths: Sequence[int] | None = None,
) -> str:
    """Render records according to the shared public output contract.

    The returned string is also written to *stream* when supplied (or stdout
    when omitted).  JSON and YAML retain the mapping shape supplied by the
    caller; delimited formats use the explicit ``columns`` order and never
    emit a header or footer. ``minimum_widths`` applies only to terminal table
    columns; values can still expand beyond those widths.
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

    _write_table(target, record_list, columns, footer, minimum_widths)
    return resolved


def render_document(
    document: Mapping[str, Any],
    *,
    requested_format: str | None,
    records_key: str | None = None,
    columns: Sequence[tuple[str, str]] | None = None,
    stream: TextIO | None = None,
) -> str:
    """Render a structured report or leave terminal text to its existing renderer.

    Structured formats preserve the complete document.  Delimited output uses
    the selected record list (or the document itself) and never emits report
    prose, headers, or footers.  A terminal ``text`` request returns ``text``
    without writing so the caller can keep its established human report.
    """

    target = stream if stream is not None else sys.stdout
    resolved = resolve_output_format(requested_format, stream=target)
    if resolved == "text":
        return resolved
    if resolved == "json":
        target.write(json.dumps(dict(document), indent=2))
        target.write("\n")
        return resolved
    if resolved == "yaml":
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError("PyYAML is required for YAML output.") from exc
        target.write(yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True))
        return resolved

    if records_key:
        candidate = document.get(records_key)
        if isinstance(candidate, list):
            records = [record for record in candidate if isinstance(record, Mapping)]
        else:
            records = [document]
    else:
        records = [document]
    selected_columns = columns or _document_columns(records)
    render_records(
        records,
        requested_format=resolved,
        columns=selected_columns,
        stream=target,
    )
    return resolved


def _document_columns(records: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    if not records:
        return []
    return [(str(key).upper(), str(key)) for key in records[0]]


def _cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def _write_table(
    stream: TextIO,
    records: Sequence[Mapping[str, Any]],
    columns: Sequence[tuple[str, str]],
    footer: str | None,
    minimum_widths: Sequence[int] | None,
) -> None:
    selected_minimums = minimum_widths or ()
    if len(selected_minimums) > len(columns):
        raise ValueError("minimum_widths cannot contain more entries than columns")

    if not records:
        if footer:
            stream.write(f"{footer}\n")
        return

    widths = [
        max(len(header), selected_minimums[index] if index < len(selected_minimums) else 0)
        for index, (header, _key) in enumerate(columns)
    ]
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
