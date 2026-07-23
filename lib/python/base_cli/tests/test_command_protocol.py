from __future__ import annotations

import unittest
from unittest.mock import patch

from base_cli.command_protocol import CommandProtocolError
from base_cli.command_protocol import dumps_record
from base_cli.command_protocol import dumps_records
from base_cli.command_protocol import loads_records
from base_cli.command_protocol import RECORD_SCHEMAS


def project_command_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "project_name": "demo",
        "project_root": "/tmp/work space/demo",
        "manifest_path": "/tmp/work space/demo/base_manifest.yaml",
        "project_venv_dir": "/tmp/work space/demo/.venv",
        "uses_uv_manager": False,
        "manifest_command_trust_required": True,
        "command": "printf 'tab=\t unicode=λ newline=\n control=\x01'",
        "runner": None,
    }
    record.update(overrides)
    return record


class CommandProtocolTests(unittest.TestCase):
    def test_project_python_requirement_is_scoped_to_project_setup_route_records(self) -> None:
        self.assertIn("requires_project_python", RECORD_SCHEMAS["project-setup-route"])
        for record_type in ("project-route", "project-command", "build-target", "demo"):
            with self.subTest(record_type=record_type):
                self.assertNotIn("requires_project_python", RECORD_SCHEMAS[record_type])

    def test_round_trip_preserves_manifest_strings_and_empty_optional_fields(self) -> None:
        records = (
            project_command_record(),
            project_command_record(command="line one\nline two\t雪", runner=""),
        )

        payload = dumps_records("project-command", records)
        record_type, decoded = loads_records(payload, expected_record_type="project-command")

        self.assertEqual(record_type, "project-command")
        self.assertEqual(decoded, records)
        self.assertIsNone(decoded[0]["runner"])
        self.assertEqual(decoded[1]["runner"], "")

    def test_protocol_has_stable_version_type_and_explicit_field_names(self) -> None:
        payload = dumps_record("project-command", project_command_record())

        self.assertTrue(payload.startswith("BASE_COMMAND_PROTOCOL_V1\n"))
        self.assertIn("record_type=project-command\n", payload)
        self.assertIn("record_count=1\n", payload)
        self.assertIn("field.project_name:string=", payload)
        self.assertIn("field.runner:null=\n", payload)

        _, decoded = loads_records(f"{payload}\n", expected_record_type="project-command")
        self.assertEqual(decoded, (project_command_record(),))

    def test_rejects_missing_and_unknown_fields_before_serializing(self) -> None:
        missing = project_command_record()
        del missing["command"]
        unknown = project_command_record(extra="value")

        with self.assertRaisesRegex(CommandProtocolError, "missing fields: command"):
            dumps_record("project-command", missing)
        with self.assertRaisesRegex(CommandProtocolError, "unknown fields: extra"):
            dumps_record("project-command", unknown)

    def test_rejects_oversized_record_sets_before_serializing(self) -> None:
        with patch("base_cli.command_protocol.MAX_RECORD_COUNT", 0):
            with self.assertRaisesRegex(CommandProtocolError, "protocol maximum"):
                dumps_record("project-command", project_command_record())

    def test_rejects_wrong_field_types_and_nul(self) -> None:
        with self.assertRaisesRegex(CommandProtocolError, "uses_uv_manager.*boolean"):
            dumps_record("project-command", project_command_record(uses_uv_manager="false"))
        with self.assertRaisesRegex(CommandProtocolError, "runner.*string"):
            dumps_record("project-command", project_command_record(runner=7))
        with self.assertRaisesRegex(CommandProtocolError, "command.*NUL"):
            dumps_record("project-command", project_command_record(command="bad\0command"))

    def test_rejects_wrong_protocol_version_and_record_type(self) -> None:
        payload = dumps_record("project-command", project_command_record())

        with self.assertRaisesRegex(CommandProtocolError, "unsupported protocol header"):
            loads_records(payload.replace("_V1", "_V2", 1))
        with self.assertRaisesRegex(CommandProtocolError, "expected record_type 'demo'"):
            loads_records(payload, expected_record_type="demo")

    def test_rejects_malformed_record_metadata_and_trailing_data(self) -> None:
        payload = dumps_record("project-command", project_command_record())

        with self.assertRaisesRegex(CommandProtocolError, "record_count"):
            loads_records(payload.replace("record_count=1", "record_count=one", 1))
        with self.assertRaisesRegex(CommandProtocolError, "canonical"):
            loads_records(payload.replace("record_count=1", "record_count=01", 1))
        with self.assertRaisesRegex(CommandProtocolError, "protocol maximum"):
            loads_records(payload.replace("record_count=1", "record_count=1000001", 1))
        with self.assertRaisesRegex(CommandProtocolError, "protocol maximum"):
            loads_records(payload.replace("record_count=1", f"record_count={'9' * 5000}", 1))
        with self.assertRaisesRegex(CommandProtocolError, "expected record=0"):
            loads_records(payload.replace("record=0", "record=1", 1))
        with self.assertRaisesRegex(CommandProtocolError, "unexpected data"):
            loads_records(f"{payload}\nextra=true")
        with self.assertRaisesRegex(CommandProtocolError, "unexpected data"):
            loads_records(f"{payload}\n\n")
        with self.assertRaisesRegex(CommandProtocolError, "protocol header"):
            loads_records(payload.replace("\n", "\r\n"))
        with self.assertRaisesRegex(CommandProtocolError, "protocol header"):
            loads_records(payload.replace("\n", "\v"))

    def test_rejects_duplicate_unknown_missing_and_invalidly_encoded_fields(self) -> None:
        payload = dumps_record("project-command", project_command_record())
        duplicate = payload.replace(
            "field.project_root:string=",
            "field.project_name:string=",
            1,
        )
        unknown = payload.replace(
            "field.project_root:string=",
            "field.unknown:string=",
            1,
        )
        wrong_type = payload.replace(
            "field.uses_uv_manager:boolean=false",
            "field.uses_uv_manager:string=false",
            1,
        )
        malformed_hex = payload.replace(
            "field.project_name:string=64656d6f",
            "field.project_name:string=xyz",
            1,
        )

        with self.assertRaisesRegex(CommandProtocolError, "duplicates field 'project_name'"):
            loads_records(duplicate)
        with self.assertRaisesRegex(CommandProtocolError, "unknown field 'unknown'"):
            loads_records(unknown)
        with self.assertRaisesRegex(CommandProtocolError, "uses_uv_manager.*boolean"):
            loads_records(wrong_type)
        with self.assertRaisesRegex(CommandProtocolError, "invalid lowercase hexadecimal"):
            loads_records(malformed_hex)

if __name__ == "__main__":
    unittest.main()
