"""Versioned base-demo dependency inputs; pins are not compatibility evidence."""

from __future__ import annotations

import re
from typing import Any


COMPONENTS = {"base", "base-cli", "base-bash-libs"}
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
CHECKSUM = re.compile(r"[0-9a-f]{64}\Z")


def validate_inputs(document: Any) -> dict[str, dict[str, str]]:
    """Validate the complete v1 input contract and return its components."""
    if not isinstance(document, dict) or set(document) != {"schema_version", "components"}:
        raise ValueError("dependency inputs require exactly schema_version and components")
    schema = document["schema_version"]
    if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
        raise ValueError("dependency inputs schema_version must be integer 1")
    components = document["components"]
    if not isinstance(components, dict) or set(components) != COMPONENTS:
        raise ValueError("dependency inputs require exactly base, base-cli, and base-bash-libs")
    for name, row in components.items():
        keys = {"version", "commit"} | ({"installer_sha256"} if name == "base" else set())
        if not isinstance(row, dict) or set(row) != keys:
            raise ValueError(f"{name} requires exactly {', '.join(sorted(keys))}")
        for key, pattern in (("version", VERSION), ("commit", SHA)):
            if not isinstance(row[key], str) or not pattern.fullmatch(row[key]):
                raise ValueError(f"{name}.{key} must be a stable version or full lowercase commit")
        if name == "base" and (
            not isinstance(row["installer_sha256"], str)
            or not CHECKSUM.fullmatch(row["installer_sha256"])
        ):
            raise ValueError("base.installer_sha256 must be a lowercase SHA-256")
    return components
