from __future__ import annotations

import os

from base_cli_adapters.config import UserConfig, UserIdeConfig

from .artifacts import check_artifact
from .artifacts import artifact_details
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
from .python_policy import python_requirement_policy_check
from .python_runtime import project_python_runtime_check
from .project_routing import manifest_requires_project_python, route_for_manifest
from .runtime_inspection import project_environment_check, unverified_runtime_check
from .setup_reconcile import effective_manifest_with_user_config
from .setup_reconcile import project_runtime_argument
from .setup_reconcile import setup_artifacts
from .test_requirements import check_test_requirements
from .uv import check_uv

IDE_EXTENSION_PROFILE = "dev"


def pre_venv_manifest_checks(
    manifest: BaseManifest, remote_network: bool = False, *, verify_project_runtime: bool = False,
) -> tuple[ArtifactCheck, ...]:
    checks: list[ArtifactCheck] = []
    if verify_project_runtime:
        checks.extend(python_requirement_checks(manifest))
    else:
        policy = python_requirement_policy_check(manifest)
        if policy is not None:
            checks.append(policy)
            if policy.ok:
                checks.append(unverified_runtime_check(manifest, "python.interpreter", "BASE-P171"))
    checks.extend(check_git_remote(manifest, check_network=remote_network))
    return tuple(checks)


def manifest_checks(
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    remote_network: bool = False,
    *,
    user_config: UserConfig | None = None,
    verify_project_runtime: bool = False,
) -> tuple[ArtifactCheck, ...]:
    pre_venv_checks: list[ArtifactCheck] = []
    checks: list[ArtifactCheck] = []
    active_user_config = user_config if user_config is not None else empty_user_config()
    effective_manifest = effective_manifest_with_user_config(manifest, active_user_config)
    artifacts = setup_artifacts(default_manifest, effective_manifest)
    definitions = resolve_artifact_definitions(artifacts)

    pre_venv_checks.extend(pre_venv_manifest_checks(
        effective_manifest, remote_network=remote_network, verify_project_runtime=verify_project_runtime,
    ))
    checks.extend(ide_preference_warning_checks(manifest, active_user_config))

    runtime_verified = verify_project_runtime
    if manifest_requires_project_python(effective_manifest):
        environment = project_environment_check(
            effective_manifest, route_for_manifest(effective_manifest).project_venv_dir,
            verify_project_runtime=verify_project_runtime,
        )
        checks.append(environment)
        runtime_verified = verify_project_runtime and environment.ok

    if effective_manifest.brewfile is not None:
        checks.append(check_brewfile(effective_manifest, verify_project_runtime=verify_project_runtime))
    if effective_manifest.mise is not None:
        checks.append(check_mise(effective_manifest, verify_project_runtime=verify_project_runtime))

    checks.extend(check_required_env(effective_manifest))
    checks.extend(check_required_ports(effective_manifest))
    checks.extend(check_build(effective_manifest))
    checks.extend(check_demo(effective_manifest))
    checks.extend(check_manifest_commands(effective_manifest))
    checks.extend(check_ide_installs(effective_manifest))
    if setup_profile_enabled(IDE_EXTENSION_PROFILE):
        checks.extend(check_ide_extensions(effective_manifest))
    checks.extend(check_ide_settings(effective_manifest))
    checks.extend(
        check for check in check_uv(effective_manifest, verify_project_runtime=verify_project_runtime)
        if check.finding_id != "BASE-P154"  # Runtime presence/verification is reported above.
    )
    checks.extend(check_pyproject(effective_manifest))
    if runtime_verified:
        checks.extend(project_python_runtime_check(effective_manifest))
    test_requirements_check = check_test_requirements(effective_manifest, verify_project_runtime=runtime_verified)
    if test_requirements_check is not None:
        checks.append(test_requirements_check)

    runtime_config = project_runtime_argument(effective_manifest)
    for artifact, definition in zip(artifacts, definitions, strict=True):
        if definition.manager == "pip" and not runtime_verified:
            checks.append(unverified_runtime_check(
                effective_manifest, artifact.name, "BASE-P040", details=artifact_details(definition),
            ))
        else:
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
