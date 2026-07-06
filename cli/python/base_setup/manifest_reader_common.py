from __future__ import annotations

from pathlib import Path
from typing import Any

from base_setup.manifest_loader import ManifestError
from base_setup.manifest_schema import SUPPORTED_COMMAND_RUNNERS


def read_optional_runner(path: Path, field_name: str, runner_data: Any) -> str | None:
    if runner_data is None:
        return None
    if not isinstance(runner_data, str) or not runner_data.strip():
        raise ManifestError(f"{path}: {field_name} must be a non-empty string when provided.")
    runner = runner_data.strip()
    if runner not in SUPPORTED_COMMAND_RUNNERS:
        supported = ", ".join(sorted(SUPPORTED_COMMAND_RUNNERS))
        raise ManifestError(f"{path}: {field_name} must be one of: {supported}.")
    return runner
