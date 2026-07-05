from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from base_cli.ide_schema import IdeDefinition

from . import process
from .errors import ArtifactError


@dataclass
class IdeDiagnosticSnapshot:
    definition: IdeDefinition
    _cli_available: bool | None = None
    _installed_extensions: set[str] | None = None
    _extension_error: ArtifactError | None = None
    _settings_file: Path | None = None
    _current_settings: dict[str, object] | None = None
    _settings_error: ArtifactError | None = None

    def cli_available(self) -> bool:
        if self._cli_available is None:
            self._cli_available = process.command_exists(self.definition.cli)
        return self._cli_available

    def installed_extensions(self) -> set[str]:
        if self._installed_extensions is None and self._extension_error is None:
            from .ide_extensions import list_ide_extensions

            try:
                self._installed_extensions = list_ide_extensions(self.definition)
            except ArtifactError as exc:
                self._extension_error = exc
        if self._extension_error is not None:
            raise self._extension_error
        if self._installed_extensions is None:
            raise RuntimeError(f"{self.definition.label} installed extensions snapshot is unavailable.")
        return self._installed_extensions

    def settings_file(self) -> Path:
        if self._settings_file is None:
            from .ide_settings import ide_settings_file

            self._settings_file = ide_settings_file(self.definition)
        return self._settings_file

    def current_settings(self) -> dict[str, object]:
        if self._current_settings is None and self._settings_error is None:
            from .ide_settings import read_ide_settings

            try:
                self._current_settings = read_ide_settings(self.definition)
            except ArtifactError as exc:
                self._settings_error = exc
        if self._settings_error is not None:
            raise self._settings_error
        if self._current_settings is None:
            raise RuntimeError(f"{self.definition.label} settings snapshot is unavailable.")
        return self._current_settings
