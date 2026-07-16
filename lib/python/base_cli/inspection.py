from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from typing import Literal

InspectionStatus = Literal["ok", "warn", "error"]


def inspection_envelope(
    *,
    command: str,
    status: InspectionStatus,
    data: Mapping[str, Any],
    error: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable v1 envelope for read-only inspection commands."""
    if status not in ("ok", "warn", "error"):
        raise ValueError(f"Unsupported inspection status: {status}")
    return {
        "schema_version": 1,
        "command": command,
        "status": status,
        "data": dict(data),
        "error": None if error is None else dict(error),
    }


def render_inspection_json(
    *,
    command: str,
    status: InspectionStatus,
    data: Mapping[str, Any],
    error: Mapping[str, Any] | None = None,
) -> str:
    """Serialize the stable inspection envelope with Python's JSON encoder."""
    return (
        json.dumps(
            inspection_envelope(command=command, status=status, data=data, error=error),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
