from __future__ import annotations

import json

from base_cli.inspection import inspection_envelope
from base_cli.inspection import render_inspection_json


def test_inspection_envelope_has_stable_v1_shape() -> None:
    payload = inspection_envelope(
        command="release check",
        status="ok",
        data={"project": 'demo "quoted"'},
    )

    assert payload == {
        "schema_version": 1,
        "command": "release check",
        "status": "ok",
        "data": {"project": 'demo "quoted"'},
        "error": None,
    }


def test_render_inspection_json_uses_stdlib_escaping() -> None:
    rendered = render_inspection_json(
        command="release check",
        status="error",
        data={},
        error={
            "type": "usage_error",
            "message": "bad value\nretry",
            "details": {},
        },
    )

    assert json.loads(rendered)["error"]["message"] == "bad value\nretry"
    assert rendered.endswith("\n")
