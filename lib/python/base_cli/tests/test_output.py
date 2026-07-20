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
