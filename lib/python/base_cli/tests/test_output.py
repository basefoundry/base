from __future__ import annotations

import io
import json
import unittest

from base_cli.output import OutputFormatError
from base_cli.output import render_records
from base_cli.output import resolve_output_format


class _Stream(io.StringIO):
    def __init__(self, *, terminal: bool) -> None:
        super().__init__()
        self.terminal = terminal

    def isatty(self) -> bool:
        return self.terminal


RECORDS = (
    {"name": "base", "path": "/work/base"},
    {"name": "demo,one", "path": "/work/demo\tone"},
)
COLUMNS = (("PROJECT", "name"), ("PATH", "path"))


class OutputTest(unittest.TestCase):
    def test_text_is_pretty_on_terminal(self) -> None:
        stream = _Stream(terminal=True)

        render_records(RECORDS, requested_format="text", columns=COLUMNS, stream=stream, footer="2 projects.")

        self.assertEqual(
            stream.getvalue(),
            "PROJECT   PATH\nbase      /work/base\ndemo,one  /work/demo\tone\n\n2 projects.\n",
        )

    def test_terminal_table_honors_minimum_widths(self) -> None:
        stream = _Stream(terminal=True)

        render_records(
            ({"name": "base", "path": "/work/base"},),
            requested_format="text",
            columns=COLUMNS,
            stream=stream,
            minimum_widths=(12,),
        )

        lines = stream.getvalue().splitlines()
        path_column = lines[0].index("PATH")
        self.assertEqual(path_column, 14)
        self.assertEqual(lines[1].index("/work/base"), path_column)

    def test_terminal_table_expands_beyond_minimum_widths(self) -> None:
        stream = _Stream(terminal=True)

        render_records(
            (
                {"name": "base", "path": "/work/base"},
                {"name": "base-bash-libs", "path": "/work/base-bash-libs"},
            ),
            requested_format="text",
            columns=COLUMNS,
            stream=stream,
            minimum_widths=(12,),
        )

        lines = stream.getvalue().splitlines()
        path_column = lines[0].index("PATH")
        self.assertEqual(path_column, len("base-bash-libs") + 2)
        self.assertEqual(lines[1].index("/work/base"), path_column)
        self.assertEqual(lines[2].index("/work/base-bash-libs"), path_column)

    def test_terminal_table_rejects_excess_minimum_widths(self) -> None:
        stream = _Stream(terminal=True)

        with self.assertRaisesRegex(ValueError, "more entries than columns"):
            render_records(
                RECORDS,
                requested_format="text",
                columns=COLUMNS,
                stream=stream,
                minimum_widths=(1, 2, 3),
            )

    def test_text_is_tsv_when_redirected(self) -> None:
        stream = _Stream(terminal=False)

        render_records(RECORDS, requested_format="text", columns=COLUMNS, stream=stream, footer="ignored")

        self.assertEqual(stream.getvalue(), "base\t/work/base\ndemo,one\t\"/work/demo\tone\"\n")

    def test_csv_quotes_cells_and_has_no_header(self) -> None:
        stream = _Stream(terminal=True)

        render_records(RECORDS, requested_format="csv", columns=COLUMNS, stream=stream, footer="ignored")

        self.assertEqual(stream.getvalue(), "base,/work/base\n\"demo,one\",/work/demo\tone\n")

    def test_json_preserves_record_shape(self) -> None:
        stream = _Stream(terminal=True)

        render_records(RECORDS, requested_format="json", columns=COLUMNS, stream=stream)

        self.assertEqual(json.loads(stream.getvalue()), list(RECORDS))

    def test_yaml_preserves_record_shape(self) -> None:
        import yaml

        stream = _Stream(terminal=True)

        render_records(RECORDS, requested_format="yaml", columns=COLUMNS, stream=stream)

        self.assertEqual(yaml.safe_load(stream.getvalue()), list(RECORDS))

    def test_resolve_rejects_unknown_format(self) -> None:
        with self.assertRaisesRegex(OutputFormatError, "Expected one of: text, csv, tsv, yaml, json"):
            resolve_output_format("xml")

    def test_empty_tty_result_keeps_footer(self) -> None:
        stream = _Stream(terminal=True)

        render_records((), requested_format="text", columns=COLUMNS, stream=stream, footer="0 projects.")

        self.assertEqual(stream.getvalue(), "0 projects.\n")
