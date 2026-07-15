from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass


PROTOCOL_HEADER = "BASE_COMMAND_PROTOCOL_V1"
MAX_RECORD_COUNT = 1_000_000


class CommandProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class FieldSpec:
    value_type: str
    nullable: bool = False


STRING = FieldSpec("string")
NULLABLE_STRING = FieldSpec("string", nullable=True)
BOOLEAN = FieldSpec("boolean")

PROJECT_REFERENCE_FIELDS = {
    "project_name": STRING,
    "project_root": STRING,
    "manifest_path": STRING,
}
PROJECT_ROUTE_FIELDS = {
    **PROJECT_REFERENCE_FIELDS,
    "project_venv_dir": STRING,
    "uses_uv_manager": BOOLEAN,
    "manifest_command_trust_required": BOOLEAN,
}

RECORD_SCHEMAS: dict[str, dict[str, FieldSpec]] = {
    "project-list-entry": {
        "project_name": STRING,
        "project_root": STRING,
    },
    "project-reference": PROJECT_REFERENCE_FIELDS,
    "project-route": PROJECT_ROUTE_FIELDS,
    "project-command": {
        **PROJECT_ROUTE_FIELDS,
        "command": STRING,
        "runner": NULLABLE_STRING,
    },
    "named-command": {
        **PROJECT_REFERENCE_FIELDS,
        "command_name": STRING,
        "command": STRING,
        "runner": NULLABLE_STRING,
    },
    "build-target": {
        **PROJECT_ROUTE_FIELDS,
        "target_name": STRING,
        "working_dir": STRING,
        "command": STRING,
        "description": NULLABLE_STRING,
        "runner": NULLABLE_STRING,
    },
    "demo": {
        **PROJECT_ROUTE_FIELDS,
        "demo_script": STRING,
        "runner": NULLABLE_STRING,
    },
    "activation-source": {
        "source_path": STRING,
    },
}

RecordValue = str | bool | None
Record = Mapping[str, RecordValue]


def dumps_record(record_type: str, record: Record) -> str:
    return dumps_records(record_type, (record,))


def dumps_records(record_type: str, records: tuple[Record, ...] | list[Record]) -> str:
    schema = _schema(record_type)
    if len(records) > MAX_RECORD_COUNT:
        raise CommandProtocolError(f"record_count exceeds protocol maximum of {MAX_RECORD_COUNT}")
    lines = [
        PROTOCOL_HEADER,
        f"record_type={record_type}",
        f"record_count={len(records)}",
    ]
    for index, record in enumerate(records):
        _validate_record(schema, record_type, record)
        lines.append(f"record={index}")
        for field_name, spec in schema.items():
            wire_type, payload = _encode_value(field_name, spec, record[field_name])
            lines.append(f"field.{field_name}:{wire_type}={payload}")
        lines.append(f"end_record={index}")
    lines.append("end_protocol=")
    return "\n".join(lines)


def loads_records(
    payload: str,
    expected_record_type: str | None = None,
) -> tuple[str, tuple[dict[str, RecordValue], ...]]:
    # The wire framing is LF-delimited. `str.splitlines()` also accepts CR,
    # vertical tab, form feed, and Unicode separators, which would make the
    # Python decoder more permissive than the Bash and Zsh readers.
    # A CLI `print()` adds one terminal LF; accept that conventional text-file
    # terminator without accepting an extra blank line or other separators.
    framed_payload = payload.removesuffix("\n")
    lines = framed_payload.split("\n")
    cursor = 0

    def take(label: str) -> str:
        nonlocal cursor
        if cursor >= len(lines):
            raise CommandProtocolError(f"missing {label}")
        line = lines[cursor]
        cursor += 1
        return line

    if take("protocol header") != PROTOCOL_HEADER:
        raise CommandProtocolError(f"unsupported protocol header; expected {PROTOCOL_HEADER}")

    record_type = _metadata_value(take("record_type"), "record_type")
    schema = _schema(record_type)
    if expected_record_type is not None and record_type != expected_record_type:
        raise CommandProtocolError(f"expected record_type '{expected_record_type}', got '{record_type}'")

    record_count_text = _metadata_value(take("record_count"), "record_count")
    record_count = _parse_record_count(record_count_text)

    records: list[dict[str, RecordValue]] = []
    for index in range(record_count):
        if take(f"record {index}") != f"record={index}":
            raise CommandProtocolError(f"expected record={index}")

        record: dict[str, RecordValue] = {}
        for _field_index in range(len(schema)):
            field_name, wire_type, encoded_value = _parse_field_line(take(f"field in record {index}"))
            if field_name in record:
                raise CommandProtocolError(f"record {index} duplicates field '{field_name}'")
            try:
                spec = schema[field_name]
            except KeyError as exc:
                raise CommandProtocolError(
                    f"record {index} has unknown field '{field_name}' for '{record_type}'"
                ) from exc
            record[field_name] = _decode_value(field_name, spec, wire_type, encoded_value)

        missing = sorted(set(schema) - set(record))
        if missing:
            raise CommandProtocolError(f"record {index} is missing fields: {', '.join(missing)}")
        if take(f"end_record {index}") != f"end_record={index}":
            raise CommandProtocolError(f"expected end_record={index}")
        records.append(record)

    if take("end_protocol") != "end_protocol=":
        raise CommandProtocolError("expected end_protocol marker")
    if cursor != len(lines):
        raise CommandProtocolError("unexpected data after end_protocol marker")
    return record_type, tuple(records)


def _schema(record_type: str) -> dict[str, FieldSpec]:
    try:
        return RECORD_SCHEMAS[record_type]
    except KeyError as exc:
        supported = ", ".join(sorted(RECORD_SCHEMAS))
        raise CommandProtocolError(f"unsupported record_type '{record_type}'; expected one of: {supported}") from exc


def _validate_record(schema: Mapping[str, FieldSpec], record_type: str, record: Record) -> None:
    missing = sorted(set(schema) - set(record))
    unknown = sorted(set(record) - set(schema))
    if missing:
        raise CommandProtocolError(f"record for '{record_type}' is missing fields: {', '.join(missing)}")
    if unknown:
        raise CommandProtocolError(f"record for '{record_type}' has unknown fields: {', '.join(unknown)}")


def _encode_value(field_name: str, spec: FieldSpec, value: RecordValue) -> tuple[str, str]:
    if value is None:
        if not spec.nullable:
            raise CommandProtocolError(f"field '{field_name}' cannot be null")
        return "null", ""
    if spec.value_type == "boolean":
        if not isinstance(value, bool):
            raise CommandProtocolError(f"field '{field_name}' must be a boolean")
        return "boolean", "true" if value else "false"
    if not isinstance(value, str):
        raise CommandProtocolError(f"field '{field_name}' must be a string")
    if "\0" in value:
        raise CommandProtocolError(f"field '{field_name}' cannot contain NUL")
    return "string", value.encode("utf-8").hex()


def _decode_value(field_name: str, spec: FieldSpec, wire_type: str, payload: str) -> RecordValue:
    if wire_type == "null":
        if not spec.nullable:
            raise CommandProtocolError(f"field '{field_name}' cannot be null")
        if payload:
            raise CommandProtocolError(f"null field '{field_name}' must have an empty payload")
        return None
    if spec.value_type == "boolean":
        if wire_type != "boolean" or payload not in ("true", "false"):
            raise CommandProtocolError(f"field '{field_name}' must use boolean:true or boolean:false")
        return payload == "true"
    if wire_type != "string":
        expected = "string or null" if spec.nullable else "string"
        raise CommandProtocolError(f"field '{field_name}' must use {expected} encoding")
    if len(payload) % 2 != 0 or re.fullmatch(r"[0-9a-f]*", payload) is None:
        raise CommandProtocolError(f"field '{field_name}' has invalid lowercase hexadecimal data")
    try:
        value = bytes.fromhex(payload).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CommandProtocolError(f"field '{field_name}' has invalid UTF-8 data") from exc
    if "\0" in value:
        raise CommandProtocolError(f"field '{field_name}' cannot contain NUL")
    return value


def _metadata_value(line: str, name: str) -> str:
    prefix = f"{name}="
    if not line.startswith(prefix):
        raise CommandProtocolError(f"expected {name} metadata")
    return line[len(prefix) :]


def _parse_record_count(record_count_text: str) -> int:
    if re.fullmatch(r"0|[1-9][0-9]*", record_count_text) is None:
        raise CommandProtocolError("record_count must be a canonical non-negative integer")
    if len(record_count_text) > len(str(MAX_RECORD_COUNT)):
        raise CommandProtocolError(f"record_count exceeds protocol maximum of {MAX_RECORD_COUNT}")
    record_count = int(record_count_text)
    if record_count > MAX_RECORD_COUNT:
        raise CommandProtocolError(f"record_count exceeds protocol maximum of {MAX_RECORD_COUNT}")
    return record_count


def _parse_field_line(line: str) -> tuple[str, str, str]:
    key, separator, payload = line.partition("=")
    if not separator or not key.startswith("field."):
        raise CommandProtocolError("expected field.<name>:<type>=<payload>")
    descriptor = key.removeprefix("field.")
    field_name, separator, wire_type = descriptor.partition(":")
    if not separator or not field_name or not wire_type:
        raise CommandProtocolError("expected field.<name>:<type>=<payload>")
    return field_name, wire_type, payload
