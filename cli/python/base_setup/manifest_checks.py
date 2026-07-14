from __future__ import annotations

import os

from base_cli.config import UserConfig, UserIdeConfig

from .artifacts import check_artifact
from .artifacts import resolve_artifact_definitions
from .build import check_build
from .checks import ArtifactCheck
from .command_lint import check_manifest_commands
from .demo import check_demo
from .delegates import check_brewfile
from .delegates import check_mise
from .git_remote import check_git_remote
from .health import check_required_env
from .health import check_required_ports
from .ide import ide_preference_warning_checks
from .ide_extensions import check_ide_extensions
from .ide_installs import check_ide_installs
from .ide_settings import check_ide_settings
from .manifest import BaseManifest
from .pyproject import check_pyproject
from .python_policy import python_requirement_checks
from .python_runtime import project_python_runtime_check
from .setup_reconcile import effective_manifest_with_user_config
from .setup_reconcile import project_runtime_argument
from .setup_reconcile import setup_artifacts
from .uv import check_uv

IDE_EXTENSION_PROFILE = "dev"


def pre_venv_manifest_checks(manifest: BaseManifest, remote_network: bool = False) -> tuple[ArtifactCheck, ...]:
    checks: list[ArtifactCheck] = []
    checks.extend(python_requirement_checks(manifest))
    checks.extend(check_git_remote(manifest, check_network=remote_network))
    return tuple(checks)


def manifest_checks(
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    remote_network: bool = False,
    *,
    user_config: UserConfig | None = None,
) -> tuple[ArtifactCheck, ...]:
    pre_venv_checks: list[ArtifactCheck] = []
    checks: list[ArtifactCheck] = []
    active_user_config = user_config if user_config is not None else empty_user_config()
    effective_manifest = effective_manifest_with_user_config(manifest, active_user_config)
    artifacts = setup_artifacts(default_manifest, effective_manifest)
    definitions = resolve_artifact_definitions(artifacts)

    pre_venv_checks.extend(pre_venv_manifest_checks(effective_manifest, remote_network=remote_network))
    checks.extend(ide_preference_warning_checks(manifest, active_user_config))

    if effective_manifest.brewfile is not None:
        checks.append(check_brewfile(effective_manifest))
    if effective_manifest.mise is not None:
        checks.append(check_mise(effective_manifest))

    checks.extend(check_required_env(effective_manifest))
    checks.extend(check_required_ports(effective_manifest))
    checks.extend(check_build(effective_manifest))
    checks.extend(check_demo(effective_manifest))
    checks.extend(check_manifest_commands(effective_manifest))
    checks.extend(check_ide_installs(effective_manifest))
    if setup_profile_enabled(IDE_EXTENSION_PROFILE):
        checks.extend(check_ide_extensions(effective_manifest))
    checks.extend(check_ide_settings(effective_manifest))
    checks.extend(check_uv(effective_manifest))
    checks.extend(check_pyproject(effective_manifest))
    checks.extend(project_python_runtime_check(effective_manifest))

    runtime_config = project_runtime_argument(effective_manifest)
    for artifact, definition in zip(artifacts, definitions, strict=True):
        checks.append(check_artifact(runtime_config, artifact, definition))

    if not pre_venv_checks and not checks:
        checks.append(
            ArtifactCheck(
                name="manifest",
                ok=True,
                message=f"Project '{effective_manifest.project_name}' declares no artifacts.",
                fix="",
                finding_id="BASE-P001",
            )
        )
    return tuple(pre_venv_checks + checks)


def setup_profile_enabled(profile: str) -> bool:
    return profile in os.environ.get("BASE_SETUP_PROFILES", "").split()


def empty_user_config() -> UserConfig:
    return UserConfig(raw={}, ide=UserIdeConfig(enabled=None, preferences={}))
