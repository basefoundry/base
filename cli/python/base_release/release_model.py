from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from base_setup.manifest_model import BaseManifest, ReleaseConfig


class ReleaseError(RuntimeError):
    def __init__(self, message: str, *, guidance: str = "") -> None:
        super().__init__(message)
        self.guidance = guidance


@dataclass(frozen=True)
class ReleaseContext:
    manifest_path: Path
    manifest: BaseManifest
    release: ReleaseConfig
    version: str
    tag_name: str
    version_file: Path
    changelog: Path


@dataclass(frozen=True)
class ReleaseFinding:
    status: str
    name: str
    message: str
