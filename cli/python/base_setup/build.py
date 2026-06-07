from __future__ import annotations

from pathlib import Path

from .checks import ArtifactCheck
from .manifest import BaseManifest, BuildTargetConfig


def check_build(manifest: BaseManifest) -> list[ArtifactCheck]:
    if manifest.build is None:
        return []

    checks: list[ArtifactCheck] = []
    for target_name, target_config in manifest.build.targets.items():
        checks.append(check_build_target_working_dir(manifest, target_name, target_config))
    return checks


def check_build_target_working_dir(
    manifest: BaseManifest,
    target_name: str,
    target_config: BuildTargetConfig,
) -> ArtifactCheck:
    field = f"build.targets.{target_name}.working_dir"
    working_dir = Path(target_config.working_dir)
    project_root = manifest.path.parent.resolve()

    if working_dir.is_absolute():
        return build_target_error(
            manifest,
            target_name,
            f"{manifest.path}: {field} must be relative to the project root.",
        )

    resolved_working_dir = (project_root / working_dir).resolve()
    try:
        resolved_working_dir.relative_to(project_root)
    except ValueError:
        return build_target_error(
            manifest,
            target_name,
            f"{manifest.path}: {field} resolves outside the project root: {target_config.working_dir}.",
        )

    if not resolved_working_dir.exists():
        return build_target_error(
            manifest,
            target_name,
            f"Build target '{target_name}' working directory '{target_config.working_dir}' does not exist.",
        )
    if not resolved_working_dir.is_dir():
        return build_target_error(
            manifest,
            target_name,
            f"Build target '{target_name}' working directory '{target_config.working_dir}' is not a directory.",
        )

    return ArtifactCheck(
        name=f"build.targets.{target_name}",
        ok=True,
        message=f"Build target '{target_name}' working directory '{target_config.working_dir}' exists.",
        fix="",
        finding_id="BASE-P070",
    )


def build_target_error(manifest: BaseManifest, target_name: str, message: str) -> ArtifactCheck:
    return ArtifactCheck(
        name=f"build.targets.{target_name}",
        ok=False,
        message=message,
        fix=f"Create the directory or update build.targets.{target_name}.working_dir in '{manifest.path}'.",
        finding_id="BASE-P070",
    )
