from __future__ import annotations

from dataclasses import replace

import base_cli
from base_cli.config import UserConfig

from .artifacts import merge_artifacts
from .artifacts import ProjectRuntimeConfig
from .artifacts import reconcile_artifacts
from .artifacts import resolve_artifact_definitions
from .delegates import reconcile_brewfile
from .delegates import reconcile_mise
from .ide import effective_ide_config
from .ide import ide_preference_warning_checks
from .ide import log_ide_preference_warnings
from .ide_extensions import reconcile_ide_extensions
from .ide_installs import reconcile_ide_installs
from .ide_settings import reconcile_ide_settings
from .manifest import BaseManifest
from .project_routing import manifest_requires_project_python
from .project_routing import route_for_manifest
from .uv import manifest_uses_uv_project_manager
from .uv import reconcile_uv_project


def reconcile_manifest(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    dry_run: bool,
) -> None:
    ctx.log.info("Reading Base manifest at '%s'.", manifest.path)
    ctx.log.info("Setting up project '%s'.", manifest.project_name)
    user_config = ctx.user_config
    log_ide_preference_warnings(ctx, ide_preference_warning_checks(manifest, user_config))
    effective_manifest = effective_manifest_with_user_config(manifest, user_config)

    artifacts = setup_artifacts(default_manifest, effective_manifest)
    definitions = resolve_artifact_definitions(artifacts)
    if not effective_manifest.artifacts:
        if artifacts:
            ctx.log.info(
                "Project '%s' declares no artifacts; installing Base default artifacts only.",
                effective_manifest.project_name,
            )
        else:
            ctx.log.info("Project '%s' has no artifacts to install.", effective_manifest.project_name)

    reconcile_brewfile(ctx, effective_manifest, dry_run=dry_run)
    reconcile_mise(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_installs(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_extensions(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_settings(ctx, effective_manifest, dry_run=dry_run)
    reconcile_uv_project(ctx, effective_manifest, dry_run=dry_run)

    if artifacts:
        reconcile_artifacts(
            ctx,
            artifacts,
            definitions,
            project_runtime_argument(effective_manifest),
            dry_run=dry_run,
        )

    ctx.log.info("Project '%s' setup is complete.", effective_manifest.project_name)


def reconcile_bootstrap_artifacts(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    dry_run: bool,
) -> None:
    if not manifest_requires_project_python(manifest):
        ctx.log.info(
            "Project '%s' does not declare a Python runtime; skipping project bootstrap.",
            manifest.project_name,
        )
        return

    ctx.log.info("Bootstrapping project '%s' Python runtime.", manifest.project_name)

    artifacts = tuple(artifact for artifact in default_manifest.artifacts if artifact.bootstrap)
    definitions = resolve_artifact_definitions(artifacts)
    if not artifacts:
        ctx.log.info("Base default manifest declares no bootstrap artifacts.")
        return

    reconcile_artifacts(
        ctx,
        artifacts,
        definitions,
        project_runtime_argument(manifest),
        dry_run=dry_run,
    )


def project_runtime_argument(manifest: BaseManifest) -> ProjectRuntimeConfig:
    return ProjectRuntimeConfig(
        name=manifest.project_name,
        python_requirement=manifest.python.requires_python,
        venv_dir=route_for_manifest(manifest).project_venv_dir,
    )


def effective_manifest_with_user_config(manifest: BaseManifest, user_config: UserConfig) -> BaseManifest:
    return replace(manifest, ide=effective_ide_config(manifest.ide, user_config))


def setup_artifacts(default_manifest: BaseManifest, manifest: BaseManifest) -> tuple:
    default_artifacts = default_manifest.artifacts
    if not manifest_requires_project_python(manifest):
        default_artifacts = tuple(
            artifact for artifact in default_artifacts if artifact.artifact_type != "python-package"
        )
    artifacts = merge_artifacts(default_artifacts, manifest.artifacts)
    if not manifest_uses_uv_project_manager(manifest):
        return artifacts
    return tuple(artifact for artifact in artifacts if artifact.artifact_type != "python-package")
