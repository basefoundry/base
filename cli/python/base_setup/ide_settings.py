from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import base_cli
from .ide_schema import IDE_DEFINITIONS
from .ide_schema import IdeDefinition

from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest
from .project_routing import route_for_manifest
from .python_artifacts import project_venv_dir

if TYPE_CHECKING:
    from .ide_diagnostics import IdeDiagnosticSnapshot


def reconcile_ide_settings(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.settings:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        resolved_settings = resolve_ide_settings(manifest, ide_config.settings)
        merge_ide_settings(ctx, definition, resolved_settings, dry_run=dry_run)


def resolve_ide_settings(project: str | BaseManifest, settings: dict[str, object]) -> dict[str, object]:
    resolved: dict[str, object] = {}
    for key, value in settings.items():
        if key == "python.defaultInterpreterPath" and value == "auto":
            if isinstance(project, BaseManifest):
                venv_dir = route_for_manifest(project).project_venv_dir
            else:
                venv_dir = project_venv_dir(project)
            resolved[key] = str(venv_dir / "bin" / "python")
        else:
            resolved[key] = value
    return resolved


def ide_settings_file(definition: IdeDefinition) -> Path:
    home = Path(os.environ.get("HOME") or Path.home()).expanduser()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / definition.settings_app_dir / "User" / "settings.json"
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config").expanduser()
    return config_home / definition.settings_app_dir / "User" / "settings.json"


def read_ide_settings(definition: IdeDefinition) -> dict[str, object]:
    _, data = _read_ide_settings_document(definition)
    return data


class _JsoncDocument(NamedTuple):
    source: str
    data: dict[str, object]


def _read_ide_settings_document(definition: IdeDefinition) -> _JsoncDocument:
    settings_file = ide_settings_file(definition)
    if not settings_file.exists():
        return _JsoncDocument("", {})
    try:
        source = settings_file.read_text(encoding="utf-8")
        data = _parse_jsonc(source)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ArtifactError(f"{settings_file}: invalid JSONC: {exc}") from exc
    if not isinstance(data, dict):
        raise ArtifactError(f"{settings_file}: expected a JSON object.")
    return _JsoncDocument(source, data)


def _parse_jsonc(source: str) -> object:
    masked = _mask_jsonc_comments(source)
    return json.loads(_remove_jsonc_trailing_commas(masked))


def _mask_jsonc_comments(source: str) -> str:
    chars = list(source)
    index = 0
    in_string = False
    escaped = False
    while index < len(source):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "/" and index + 1 < len(source) and source[index + 1] == "/":
            chars[index] = " "
            chars[index + 1] = " "
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                chars[index] = " "
                index += 1
            continue
        if char == "/" and index + 1 < len(source) and source[index + 1] == "*":
            start = index
            chars[index] = " "
            chars[index + 1] = " "
            index += 2
            while index + 1 < len(source) and source[index : index + 2] != "*/":
                if source[index] not in "\r\n":
                    chars[index] = " "
                index += 1
            if index + 1 >= len(source):
                raise ValueError(f"unterminated comment at line {source.count(chr(10), 0, start) + 1}")
            chars[index] = " "
            chars[index + 1] = " "
            index += 2
            continue
        index += 1
    return "".join(chars)


def _remove_jsonc_trailing_commas(source: str) -> str:
    chars = list(source)
    index = 0
    in_string = False
    escaped = False
    while index < len(source):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == ",":
            next_index = index + 1
            while next_index < len(source) and source[next_index].isspace():
                next_index += 1
            if next_index < len(source) and source[next_index] in "}]":
                chars[index] = " "
        index += 1
    return "".join(chars)


def _jsonc_object_with_added_properties(source: str, added: dict[str, object]) -> str:
    if not source:
        lines = ["{"]
        lines.extend(f"  {json.dumps(key)}: {json.dumps(value, sort_keys=True)}," for key, value in added.items())
        lines[-1] = lines[-1].rstrip(",")
        lines.append("}")
        return "\n".join(lines) + "\n"

    opening, closing, last_significant = _jsonc_root_positions(source)
    newline = "\r\n" if "\r\n" in source else "\n"
    close_line_start = source.rfind("\n", 0, closing) + 1
    closing_indent = source[close_line_start:closing]
    multiline_close = "\n" in source[opening:closing] and all(char in " \t\r" for char in closing_indent)
    existing_content = last_significant is not None and last_significant > opening
    property_indent = f"{closing_indent}  " if multiline_close else ""
    property_lines = [
        f"{property_indent}{json.dumps(key)}: {json.dumps(value, sort_keys=True)},"
        for key, value in added.items()
    ]
    if property_lines:
        property_lines[-1] = property_lines[-1].rstrip(",")

    if not existing_content:
        if multiline_close:
            return source[:close_line_start] + newline.join(property_lines) + newline + source[close_line_start:]
        return source[:closing] + ", ".join(line.strip().rstrip(",") for line in property_lines) + source[closing:]

    has_trailing_comma = source[last_significant] == "," if last_significant is not None else False
    comma = "" if has_trailing_comma else ","
    if multiline_close:
        prefix = source[: last_significant + 1] + comma
        suffix = source[last_significant + 1 : close_line_start]
        return prefix + suffix + newline.join(property_lines) + newline + source[close_line_start:]
    return source[: last_significant + 1] + comma + " " + ", ".join(
        line.strip().rstrip(",") for line in property_lines
    ) + source[last_significant + 1 :]


# pylint: disable=too-many-branches,too-many-statements
def _jsonc_root_positions(source: str) -> tuple[int, int, int | None]:
    opening = next((index for index, char in enumerate(source) if not char.isspace()), None)
    if opening is None or source[opening] != "{":
        raise ValueError("expected a JSON object")
    depth = 0
    index = opening
    in_string = False
    escaped = False
    last_significant: int | None = None
    while index < len(source):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
                last_significant = index
            index += 1
            continue
        if char == '"':
            in_string = True
            last_significant = index
            index += 1
            continue
        if char == "/" and index + 1 < len(source) and source[index + 1] == "/":
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and index + 1 < len(source) and source[index + 1] == "*":
            index += 2
            while index + 1 < len(source) and source[index : index + 2] != "*/":
                index += 1
            if index + 1 >= len(source):
                raise ValueError("unterminated comment")
            index += 2
            continue
        if char.isspace():
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return opening, index, last_significant
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        last_significant = index
        index += 1
    raise ValueError("unterminated JSON object")


def _verified_jsonc_update(
    settings_file: Path,
    source: str,
    current_settings: dict[str, object],
    added: dict[str, object],
) -> str:
    updated_source = _jsonc_object_with_added_properties(source, added)
    expected_settings = {**current_settings, **added}
    try:
        verified_settings = _parse_jsonc(updated_source)
    except ValueError as exc:
        raise ArtifactError(f"{settings_file}: could not safely add settings: {exc}") from exc
    if verified_settings != expected_settings:
        raise ArtifactError(f"{settings_file}: refusing to write an unexpected settings result.")
    return updated_source


def merge_ide_settings(
    ctx: base_cli.Context,
    definition: IdeDefinition,
    desired_settings: dict[str, object],
    dry_run: bool,
) -> None:
    settings_file = ide_settings_file(definition)
    document = _read_ide_settings_document(definition)
    current_settings = document.data
    added: dict[str, object] = {}

    for key, value in desired_settings.items():
        if key not in current_settings:
            added[key] = value
        elif current_settings[key] != value:
            ctx.log.info(
                "%s setting '%s' already set by user; leaving intact.",
                definition.label,
                key,
            )

    if not added:
        ctx.log.debug("%s user settings already contain all Base-managed keys.", definition.label)
        return

    if dry_run:
        for key, value in added.items():
            ctx.log.info(
                "[DRY-RUN] Would set %s user setting '%s' to %s.",
                definition.label,
                key,
                json.dumps(value, sort_keys=True),
            )
        return

    settings_file.parent.mkdir(parents=True, exist_ok=True)
    updated_source = _verified_jsonc_update(settings_file, document.source, current_settings, added)
    write_text_atomic(settings_file, updated_source)
    ctx.log.info("Updated %s user settings at '%s'.", definition.label, settings_file)


def write_json_atomic(path: Path, data: dict[str, object]) -> None:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            json.dump(data, tmp_file, indent=2, sort_keys=True)
            tmp_file.write("\n")
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def write_text_atomic(path: Path, text: str) -> None:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(text)
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def check_ide_settings(manifest: BaseManifest) -> list[ArtifactCheck]:
    from .ide_diagnostics import IdeDiagnosticSnapshot

    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.settings:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        snapshot = IdeDiagnosticSnapshot(definition)
        resolved_settings = resolve_ide_settings(manifest, ide_config.settings)
        checks.extend(
            check_ide_setting(manifest.project_name, definition, key, value, snapshot=snapshot)
            for key, value in resolved_settings.items()
        )
    return checks


def check_ide_setting(
    project: str,
    definition: IdeDefinition,
    key: str,
    expected_value: object,
    snapshot: IdeDiagnosticSnapshot | None = None,
) -> ArtifactCheck:
    from .ide_diagnostics import IdeDiagnosticSnapshot

    snapshot = snapshot or IdeDiagnosticSnapshot(definition)
    settings_file = snapshot.settings_file()
    try:
        current_settings = snapshot.current_settings()
    except ArtifactError as exc:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=False,
            message=str(exc),
            fix=f"Repair '{settings_file}' and run 'basectl setup {project}'.",
            finding_id="BASE-P120",
        )

    if key not in current_settings:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=False,
            message=f"{definition.label} setting '{key}' is absent from '{settings_file}'.",
            fix=f"basectl setup {project}",
            finding_id="BASE-P121",
        )
    if current_settings[key] == expected_value:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=True,
            message=f"{definition.label} setting '{key}' matches the Base manifest.",
            fix="",
            finding_id="BASE-P122",
        )
    return ArtifactCheck(
        name=f"{definition.label} setting: {key}",
        ok=False,
        message=(
            f"{definition.label} setting '{key}' is set to {json.dumps(current_settings[key], sort_keys=True)}; "
            f"expected {json.dumps(expected_value, sort_keys=True)}. Base will not overwrite user settings."
        ),
        fix=f"Update '{settings_file}' manually or remove the key and run 'basectl setup {project}'.",
        finding_id="BASE-P123",
    )
