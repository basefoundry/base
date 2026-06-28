from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import base_cli
from base_setup.manifest import BaseManifest, BuildTargetConfig, ManifestError, read_manifest
from base_setup.project_routing import route_for_manifest


class ProjectLike(Protocol):
    name: str
    root: Path
    manifest_path: Path


class BuildTargetError(RuntimeError):
    pass


ProjectResolver = Callable[[base_cli.Context, str, str | None], ProjectLike]


def build_targets_project_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    resolve_project: ProjectResolver,
) -> int:
    if len(arguments) < 1:
        ctx.log.error("Command 'build-targets' requires at least 1 argument (project name); got %d.", len(arguments))
        return base_cli.ExitCode.USAGE_ERROR
    return build_targets_project_command(ctx, arguments[0], arguments[1:], workspace, resolve_project)


def list_build_targets_from_args(
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    workspace: str | None,
    resolve_project: ProjectResolver,
) -> int:
    if len(arguments) != 1:
        ctx.log.error("Command 'build-target-list' requires exactly 1 argument (project name); got %d.", len(arguments))
        return base_cli.ExitCode.USAGE_ERROR
    return list_build_targets_command(ctx, arguments[0], workspace, resolve_project)


def build_targets_project_command(
    ctx: base_cli.Context,
    project_name: str | None,
    target_names: tuple[str, ...],
    workspace: str | None,
    resolve_project: ProjectResolver,
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
        targets = selected_build_targets(project, manifest, target_names)
    except (RuntimeError, ManifestError, BuildTargetError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    for target_name, target_config, working_dir in targets:
        print_build_target(project, manifest, target_name, target_config, working_dir)
    return base_cli.ExitCode.SUCCESS


def list_build_targets_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    resolve_project: ProjectResolver,
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_project(ctx, project_name, workspace)
        manifest = read_manifest(project.manifest_path)
        targets = all_build_targets(project, manifest)
    except (RuntimeError, ManifestError, BuildTargetError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    for target_name, target_config, working_dir in targets:
        print_build_target(project, manifest, target_name, target_config, working_dir)
    return base_cli.ExitCode.SUCCESS


def print_build_target(
    project: ProjectLike,
    manifest: BaseManifest,
    target_name: str,
    target_config: BuildTargetConfig,
    working_dir: Path,
) -> None:
    fields = [
        project.name,
        str(project.root),
        str(project.manifest_path),
        target_name,
        str(working_dir),
        target_config.command,
        target_config.description or "",
    ]
    if target_config.runner is not None:
        fields.append(target_config.runner)
    fields.extend(route_metadata_fields(manifest))
    print("\t".join(fields))


def route_metadata_fields(manifest: BaseManifest) -> list[str]:
    route = route_for_manifest(manifest)
    uses_uv = "true" if route.uses_uv_manager else "false"
    return [
        f"__base_project_venv_dir={route.project_venv_dir}",
        f"__base_uses_uv_manager={uses_uv}",
    ]


def selected_build_targets(
    project: ProjectLike,
    manifest: BaseManifest,
    target_names: tuple[str, ...],
) -> tuple[tuple[str, BuildTargetConfig, Path], ...]:
    build = manifest.build
    if build is None or not build.targets:
        raise BuildTargetError(f"Project '{project.name}' does not declare build targets in '{manifest.path}'.")

    selected_names = target_names or build.default
    if not selected_names:
        raise BuildTargetError(
            f"Project '{project.name}' does not declare build.default in '{manifest.path}'. "
            "Pass one or more build targets explicitly."
        )

    targets: list[tuple[str, BuildTargetConfig, Path]] = []
    for target_name in selected_names:
        try:
            target_config = build.targets[target_name]
        except KeyError as exc:
            raise BuildTargetError(
                f"Project '{project.name}' does not declare build target '{target_name}' in '{manifest.path}'."
            ) from exc
        working_dir = resolve_build_target_working_dir(project, target_name, target_config)
        targets.append((target_name, target_config, working_dir))
    return tuple(targets)


def all_build_targets(
    project: ProjectLike,
    manifest: BaseManifest,
) -> tuple[tuple[str, BuildTargetConfig, Path], ...]:
    build = manifest.build
    if build is None or not build.targets:
        raise BuildTargetError(f"Project '{project.name}' does not declare build targets in '{manifest.path}'.")

    return tuple(
        (
            target_name,
            target_config,
            resolve_build_target_working_dir(project, target_name, target_config),
        )
        for target_name, target_config in build.targets.items()
    )


def resolve_build_target_working_dir(
    project: ProjectLike,
    target_name: str,
    target_config: BuildTargetConfig,
) -> Path:
    field = f"build.targets.{target_name}.working_dir"
    project_root = project.root.resolve()
    declared_path = Path(target_config.working_dir)
    if declared_path.is_absolute():
        raise BuildTargetError(f"{project.manifest_path}: {field} must be a relative path inside the project root.")

    candidate = (project_root / declared_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise BuildTargetError(
            f"{project.manifest_path}: {field} resolves outside the project root: {target_config.working_dir}."
        ) from exc

    if not candidate.exists():
        raise BuildTargetError(
            f"{project.manifest_path}: {field} directory '{target_config.working_dir}' does not exist."
        )
    if not candidate.is_dir():
        raise BuildTargetError(
            f"{project.manifest_path}: {field} path '{target_config.working_dir}' is not a directory."
        )
    return candidate
