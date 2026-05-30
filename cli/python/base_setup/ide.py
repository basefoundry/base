from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.config import UserConfig

from . import artifacts
from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest, IdeConfig


@dataclass(frozen=True)
class IdeDefinition:
    name: str
    label: str
    cli: str
    cask: str
    settings_app_dir: str


IDE_DEFINITIONS = {
    "vscode": IdeDefinition(
        name="vscode",
        label="VS Code",
        cli="code",
        cask="visual-studio-code",
        settings_app_dir="Code",
    ),
    "cursor": IdeDefinition(
        name="cursor",
        label="Cursor",
        cli="cursor",
        cask="cursor",
        settings_app_dir="Cursor",
    ),
}


def effective_ide_config(project_ide: dict[str, IdeConfig], user_config: UserConfig) -> dict[str, IdeConfig]:
    if user_config.ide.enabled is False:
        return {}

    effective: dict[str, IdeConfig] = {}
    ide_names = sorted(set(project_ide) | set(user_config.ide.preferences))
    for ide_name in ide_names:
        user_preference = user_config.ide.preferences.get(ide_name)
        if user_preference is not None and user_preference.enabled is False:
            continue

        project_config = project_ide.get(ide_name, IdeConfig(install=False, extensions=(), settings={}))
        install = project_config.install
        if user_preference is not None and user_preference.install is not None:
            install = user_preference.install

        extensions = list(project_config.extensions)
        if user_preference is not None:
            for extension in user_preference.extra_extensions:
                if extension not in extensions:
                    extensions.append(extension)

        settings = {}
        if user_preference is not None:
            settings.update(user_preference.settings)
        settings.update(project_config.settings)

        if install or extensions or settings:
            effective[ide_name] = IdeConfig(
                install=install,
                extensions=tuple(extensions),
                settings=settings,
            )
    return effective


def ide_preference_warning_checks(manifest: BaseManifest, user_config: UserConfig) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    if user_config.ide.enabled is False and manifest.ide:
        checks.append(
            ArtifactCheck(
                name="user IDE config",
                ok=False,
                message="User config disables all IDE setup and checks for this machine.",
                fix="Remove or change 'ide.enabled: false' in ~/.base.d/config.yaml to re-enable IDE work.",
                status="warn",
            )
        )

    for ide_name, project_config in manifest.ide.items():
        user_preference = user_config.ide.preferences.get(ide_name)
        if user_preference is None:
            continue
        if user_preference.enabled is False:
            checks.append(
                ArtifactCheck(
                    name=f"user IDE config: {ide_name}",
                    ok=False,
                    message=f"User config disables {ide_name} IDE setup and checks for this machine.",
                    fix=f"Remove or change 'ide.{ide_name}.enabled: false' in ~/.base.d/config.yaml to re-enable it.",
                    status="warn",
                )
            )
            continue
        conflicting_settings = sorted(set(project_config.settings) & set(user_preference.settings))
        for key in conflicting_settings:
            if project_config.settings[key] == user_preference.settings[key]:
                continue
            checks.append(
                ArtifactCheck(
                    name=f"user IDE setting: {ide_name}.{key}",
                    ok=False,
                    message=(
                        f"User config setting 'ide.{ide_name}.settings.{key}' is ignored because "
                        "the project manifest declares the same setting."
                    ),
                    fix=(
                        f"Remove 'ide.{ide_name}.settings.{key}' from ~/.base.d/config.yaml "
                        "or update the project manifest."
                    ),
                    status="warn",
                )
            )
    return checks


def log_ide_preference_warnings(ctx: base_cli.Context, checks: list[ArtifactCheck]) -> None:
    for check in checks:
        ctx.log.warning(check.message)
        if check.fix:
            ctx.log.warning("Fix: %s", check.fix)


def reconcile_ide_installs(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        definition = IDE_DEFINITIONS[ide_name]
        if not ide_config.install:
            ctx.log.debug("IDE '%s' does not request installation; skipping cask install.", ide_name)
            continue
        reconcile_ide_install(ctx, definition, dry_run=dry_run)


def reconcile_ide_install(ctx: base_cli.Context, definition: IdeDefinition, dry_run: bool) -> None:
    command = ["brew", "install", "--cask", definition.cask]
    if dry_run:
        process.dry_run_command(ctx, command)
        return

    if not process.command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install {definition.label}.")

    if process.run_check(["brew", "list", "--cask", definition.cask]):
        ctx.log.info("%s is already installed via Homebrew cask '%s'.", definition.label, definition.cask)
    else:
        ctx.log.info("Installing %s via Homebrew cask '%s'.", definition.label, definition.cask)
        process.run_command(ctx, command)

    if process.command_exists(definition.cli):
        ctx.log.info("%s CLI '%s' is available on PATH.", definition.label, definition.cli)
    else:
        ctx.log.warning(
            "%s is installed, but CLI '%s' is not on PATH. Enable the IDE shell command before extension setup.",
            definition.label,
            definition.cli,
        )


def check_ide_installs(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        definition = IDE_DEFINITIONS[ide_name]
        if ide_config.install:
            checks.append(check_ide_install(manifest.project_name, definition))
    return checks


def reconcile_ide_extensions(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.extensions:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        if dry_run:
            for extension in ide_config.extensions:
                process.dry_run_command(ctx, [definition.cli, "--install-extension", extension])
            continue
        if not process.command_exists(definition.cli):
            ctx.log.warning(
                "%s CLI '%s' is not on PATH; skipping extension setup.",
                definition.label,
                definition.cli,
            )
            continue
        installed_extensions = list_ide_extensions(definition)
        for extension in ide_config.extensions:
            if extension in installed_extensions:
                ctx.log.debug(
                    "%s extension '%s' is already installed.",
                    definition.label,
                    extension,
                )
                continue
            ctx.log.info("Installing %s extension '%s'.", definition.label, extension)
            process.run_command(ctx, [definition.cli, "--install-extension", extension])


def list_ide_extensions(definition: IdeDefinition) -> set[str]:
    completed = subprocess.run(
        [definition.cli, "--list-extensions"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        stderr = (completed.stderr or "").strip()
        message = f"Unable to list {definition.label} extensions with '{definition.cli} --list-extensions'."
        if stderr:
            message = f"{message}\n{stderr}"
        raise ArtifactError(message)
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def check_ide_extensions(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.extensions:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        checks.extend(
            check_ide_extension(manifest.project_name, definition, extension)
            for extension in ide_config.extensions
        )
    return checks


def check_ide_extension(project: str, definition: IdeDefinition, extension: str) -> ArtifactCheck:
    if not process.command_exists(definition.cli):
        return ArtifactCheck(
            name=extension,
            ok=False,
            message=(
                f"Cannot check {definition.label} extension '{extension}' "
                f"because CLI '{definition.cli}' is not on PATH."
            ),
            fix=(
                f"Enable the '{definition.cli}' shell command from {definition.label}, "
                f"then run 'basectl setup {project}'."
            ),
        )

    try:
        installed_extensions = list_ide_extensions(definition)
    except ArtifactError as exc:
        return ArtifactCheck(
            name=extension,
            ok=False,
            message=str(exc),
            fix=f"basectl setup {project}",
        )

    if extension in installed_extensions:
        return ArtifactCheck(
            name=extension,
            ok=True,
            message=f"{definition.label} extension '{extension}' is installed.",
            fix="",
        )
    return ArtifactCheck(
        name=extension,
        ok=False,
        message=f"{definition.label} extension '{extension}' is not installed.",
        fix=f"basectl setup {project}",
    )


def reconcile_ide_settings(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.settings:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        resolved_settings = resolve_ide_settings(manifest.project_name, ide_config.settings)
        merge_ide_settings(ctx, definition, resolved_settings, dry_run=dry_run)


def resolve_ide_settings(project: str, settings: dict[str, object]) -> dict[str, object]:
    resolved: dict[str, object] = {}
    for key, value in settings.items():
        if key == "python.defaultInterpreterPath" and value == "auto":
            resolved[key] = str(artifacts.project_venv_dir(project) / "bin" / "python")
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
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        json.dump(data, tmp_file, indent=2, sort_keys=True)
        tmp_file.write("\n")
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


def check_ide_settings(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.settings:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        resolved_settings = resolve_ide_settings(manifest.project_name, ide_config.settings)
        checks.extend(
            check_ide_setting(manifest.project_name, definition, key, value)
            for key, value in resolved_settings.items()
        )
    return checks


def check_ide_setting(
    project: str,
    definition: IdeDefinition,
    key: str,
    expected_value: object,
) -> ArtifactCheck:
    settings_file = ide_settings_file(definition)
    try:
        current_settings = read_ide_settings(definition)
    except ArtifactError as exc:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=False,
            message=str(exc),
            fix=f"Repair '{settings_file}' and run 'basectl setup {project}'.",
        )

    if key not in current_settings:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=False,
            message=f"{definition.label} setting '{key}' is absent from '{settings_file}'.",
            fix=f"basectl setup {project}",
        )
    if current_settings[key] == expected_value:
        return ArtifactCheck(
            name=f"{definition.label} setting: {key}",
            ok=True,
            message=f"{definition.label} setting '{key}' matches the Base manifest.",
            fix="",
        )
    return ArtifactCheck(
        name=f"{definition.label} setting: {key}",
        ok=False,
        message=(
            f"{definition.label} setting '{key}' is set to {json.dumps(current_settings[key], sort_keys=True)}; "
            f"expected {json.dumps(expected_value, sort_keys=True)}. Base will not overwrite user settings."
        ),
        fix=f"Update '{settings_file}' manually or remove the key and run 'basectl setup {project}'.",
    )


def check_ide_install(project: str, definition: IdeDefinition) -> ArtifactCheck:
    if not process.command_exists("brew"):
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=f"Homebrew is required to check {definition.label} installation.",
            fix="basectl setup",
        )

    cask_installed = process.run_check(["brew", "list", "--cask", definition.cask])
    cli_available = process.command_exists(definition.cli)

    if cask_installed and cli_available:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=True,
            message=f"{definition.label} is installed and CLI '{definition.cli}' is on PATH.",
            fix="",
        )
    if not cask_installed:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=f"{definition.label} is not installed via Homebrew cask '{definition.cask}'.",
            fix=f"basectl setup {project}",
        )
    return ArtifactCheck(
        name=f"{definition.label} CLI",
        ok=False,
        message=f"{definition.label} is installed, but CLI '{definition.cli}' is not on PATH.",
        fix=f"Enable the '{definition.cli}' shell command from {definition.label}.",
    )
