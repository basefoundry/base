from __future__ import annotations

import base_cli
from base_cli.config import UserConfig
from base_cli.ide_schema import IDE_DEFINITIONS  # pylint: disable=unused-import
from base_cli.ide_schema import IdeDefinition  # pylint: disable=unused-import

from .checks import ArtifactCheck
# pylint: disable=unused-import
from .ide_diagnostics import IdeDiagnosticSnapshot  # pylint: disable=unused-import
from .ide_extensions import check_ide_extension  # pylint: disable=unused-import
from .ide_extensions import check_ide_extensions
from .ide_extensions import list_ide_extensions  # pylint: disable=unused-import
from .ide_extensions import reconcile_ide_extensions
from .ide_installs import check_ide_install  # pylint: disable=unused-import
from .ide_installs import check_ide_installs
from .ide_installs import reconcile_ide_install  # pylint: disable=unused-import
from .ide_installs import reconcile_ide_installs
from .ide_settings import check_ide_setting  # pylint: disable=unused-import
from .ide_settings import check_ide_settings
from .ide_settings import ide_settings_file  # pylint: disable=unused-import
from .ide_settings import merge_ide_settings  # pylint: disable=unused-import
from .ide_settings import read_ide_settings  # pylint: disable=unused-import
from .ide_settings import reconcile_ide_settings
from .ide_settings import resolve_ide_settings  # pylint: disable=unused-import
from .ide_settings import write_json_atomic  # pylint: disable=unused-import
# pylint: enable=unused-import
from .manifest import BaseManifest, IdeConfig


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
                finding_id="BASE-P100",
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
                    finding_id="BASE-P101",
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
                    finding_id="BASE-P102",
                )
            )
    return checks


def log_ide_preference_warnings(ctx: base_cli.Context, checks: list[ArtifactCheck]) -> None:
    for check in checks:
        ctx.log.warning(check.message)
        if check.fix:
            ctx.log.warning("Fix: %s", check.fix)
