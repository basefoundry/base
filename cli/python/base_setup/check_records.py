"""Checkout and manifest identity for optional saved check evidence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


CHECK_RECORD_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class CheckRecordContext:
    project_root: Path
    manifest_path: Path

    def identity(self) -> dict[str, str]:
        manifest = self.manifest_path.resolve()
        return {
            "project_root": str(self.project_root.resolve()),
            "manifest_path": str(manifest),
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        }
