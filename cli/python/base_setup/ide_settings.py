from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import base_cli
from base_cli.ide_schema import IDE_DEFINITIONS
from base_cli.ide_schema import IdeDefinition

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
    settings_file = ide_settings_file(definition)
    if not settings_file.exists():
        return {}
    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"{settings_file}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ArtifactError(f"{settings_file}: expected a JSON object.")
    return data


def merge_ide_settings(
    ctx: base_cli.Context,
    definition: IdeDefinition,
    desired_settings: dict[str, object],
    dry_run: bool,
) -> None:
    settings_file = ide_settings_file(definition)
    current_settings = read_ide_settings(definition)
    merged_settings = dict(current_settings)
    added: dict[str, object] = {}

    for key, value in desired_settings.items():
        if key not in current_settings:
            merged_settings[key] = value
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
    write_json_atomic(settings_file, merged_settings)
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
