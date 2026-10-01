from __future__ import annotations

from collections.abc import Mapping

from .provider import load_command_protocol


_command_protocol = load_command_protocol()
BOOLEAN = _command_protocol.BOOLEAN
CommandProtocolError = _command_protocol.CommandProtocolError
FieldSpec = _command_protocol.FieldSpec
NULLABLE_STRING = _command_protocol.NULLABLE_STRING
STRING = _command_protocol.STRING
_dumps_record = _command_protocol.dumps_record
_dumps_records = _command_protocol.dumps_records
_loads_records = _command_protocol.loads_records
register_record_schema = _command_protocol.register_record_schema
_registered_schemas = _command_protocol.RECORD_SCHEMAS


BASE_PROTOCOL_HEADER = "BASE_COMMAND_PROTOCOL_V1"
RecordValue = str | bool | None
Record = Mapping[str, RecordValue]

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
PROJECT_SETUP_ROUTE_FIELDS = {
    **PROJECT_ROUTE_FIELDS,
    "requires_project_python": BOOLEAN,
}

BASE_RECORD_SCHEMAS: dict[str, dict[str, FieldSpec]] = {
    "project-list-entry": {
        "project_name": STRING,
        "project_root": STRING,
    },
    "project-reference": PROJECT_REFERENCE_FIELDS,
    "project-route": PROJECT_ROUTE_FIELDS,
    "project-setup-route": PROJECT_SETUP_ROUTE_FIELDS,
    "project-command": {
        **PROJECT_ROUTE_FIELDS,
        "command": STRING,
        "runner": NULLABLE_STRING,
        "uv_extras": STRING,
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


def register_base_record_schemas() -> None:
    """Register Base's record schemas with the generic protocol runtime."""

    for record_type, fields in BASE_RECORD_SCHEMAS.items():
        if record_type not in _registered_schemas:
            register_record_schema(record_type, fields)


def dumps_record(record_type: str, record: Record) -> str:
    register_base_record_schemas()
    return _dumps_record(record_type, record, protocol_header=BASE_PROTOCOL_HEADER)


def dumps_records(record_type: str, records: tuple[Record, ...] | list[Record]) -> str:
    register_base_record_schemas()
    return _dumps_records(record_type, records, protocol_header=BASE_PROTOCOL_HEADER)


def loads_records(
    payload: str,
    expected_record_type: str | None = None,
) -> tuple[str, tuple[dict[str, RecordValue], ...]]:
    register_base_record_schemas()
    return _loads_records(
        payload,
        expected_record_type=expected_record_type,
        protocol_header=BASE_PROTOCOL_HEADER,
    )


__all__ = [
    "BASE_PROTOCOL_HEADER",
    "BASE_RECORD_SCHEMAS",
    "CommandProtocolError",
    "dumps_record",
    "dumps_records",
    "loads_records",
    "register_base_record_schemas",
]


register_base_record_schemas()
