from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import base_cli
from base_cli.command_protocol import dumps_records
from base_projects.project_commands import route_metadata_record
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import BaseManifest, BuildTargetConfig
from base_setup.project_routing import route_for_manifest


class ProjectLike(Protocol):
    name: str
    root: Path
    manifest_path: Path


class BuildTargetError(RuntimeError):
    pass


ProjectResolver = Callable[[base_cli.Context, str, str | None], ProjectLike]
InvocationProjectSelector = Callable[
    [base_cli.Context, str | None, tuple[str, ...], str | None],
    tuple[ProjectLike, tuple[str, ...]],
]


def build_targets_project_from_args(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    explicit_project: str | None,
    workspace: str | None,
    select_project: InvocationProjectSelector,
    output_format: str = "text",
) -> int:
    try:
        project, target_names = select_project(ctx, explicit_project, arguments, workspace)
    except (RuntimeError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE
    return build_targets_for_project(ctx, project, target_names, output_format)


def list_build_targets_from_args(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    ctx: base_cli.Context,
    arguments: tuple[str, ...],
    explicit_project: str | None,
    workspace: str | None,
    select_project: InvocationProjectSelector,
    output_format: str = "text",
) -> int:
    if explicit_project is not None and arguments:
        ctx.log.error("Command 'build-target-list' does not accept a positional project with --project.")
        return base_cli.ExitCode.USAGE_ERROR
    if len(arguments) > 1:
        ctx.log.error("Command 'build-target-list' accepts at most 1 positional project; got %d.", len(arguments))
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project, remaining = select_project(ctx, explicit_project, arguments, workspace)
    except (RuntimeError, ManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE
    if remaining:
        ctx.log.error("Project '%s' was not found in the configured workspace.", remaining[0])
        return base_cli.ExitCode.FAILURE
    return list_build_targets_for_project(ctx, project, output_format)


def build_targets_project_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    ctx: base_cli.Context,
    project_name: str | None,
    target_names: tuple[str, ...],
    workspace: str | None,
    resolve_project: ProjectResolver,
    output_format: str = "text",
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_project(ctx, project_name, workspace)
    except (RuntimeError, ManifestError, BuildTargetError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    return build_targets_for_project(ctx, project, target_names, output_format)


def build_targets_for_project(
    ctx: base_cli.Context,
    project: ProjectLike,
    target_names: tuple[str, ...],
    output_format: str = "text",
) -> int:
    if output_format != "command-protocol":
        try:
            base_cli.resolve_output_format(output_format)
        except base_cli.OutputFormatError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
    try:
        manifest = read_manifest(project.manifest_path)
        targets = selected_build_targets(project, manifest, target_names)
    except (RuntimeError, ManifestError, BuildTargetError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "command-protocol":
        records = [
            build_target_record(
                project,
                manifest,
                target_name,
                target_config,
                working_dir,
                manifest_command_trust_required=True,
            )
            for target_name, target_config, working_dir in targets
        ]
        print(dumps_records("build-target", records))
    elif output_format == "text":
        for target_name, target_config, working_dir in targets:
            print_build_target(
                project,
                manifest,
                target_name,
                target_config,
                working_dir,
                manifest_command_trust_required=True,
            )
    else:
        ctx.log.error("Unsupported build-targets output format '%s'.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


def list_build_targets_command(
    ctx: base_cli.Context,
    project_name: str | None,
    workspace: str | None,
    resolve_project: ProjectResolver,
    output_format: str = "text",
) -> int:
    if not project_name:
        ctx.log.error("Project name is required.")
        return base_cli.ExitCode.USAGE_ERROR

    try:
        project = resolve_project(ctx, project_name, workspace)
    except (RuntimeError, ManifestError, BuildTargetError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    return list_build_targets_for_project(ctx, project, output_format)


def list_build_targets_for_project(
    ctx: base_cli.Context,
    project: ProjectLike,
    output_format: str = "text",
) -> int:
    if output_format != "command-protocol":
        try:
            base_cli.resolve_output_format(output_format)
        except base_cli.OutputFormatError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
    try:
        manifest = read_manifest(project.manifest_path)
        targets = all_build_targets(project, manifest)
    except (RuntimeError, ManifestError, BuildTargetError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    records = [
        build_target_record(
            project,
            manifest,
            target_name,
            target_config,
            working_dir,
            manifest_command_trust_required=False,
        )
        for target_name, target_config, working_dir in targets
    ]
    if output_format == "command-protocol":
        print(dumps_records("build-target", records))
    elif output_format in {"json", "yaml"}:
        base_cli.render_document(
            {
                "schema_version": 1,
                "project": {
                    "name": project.name,
                    "root": str(project.root),
                    "manifest_path": str(project.manifest_path),
                },
                "targets": [
                    {
                        "name": target_name,
                        "working_dir": str(working_dir),
                        "command": target_config.command,
                        "description": target_config.description,
                        "runner": target_config.runner,
                    }
                    for target_name, target_config, working_dir in targets
                ],
            },
            requested_format=output_format,
        )
    elif output_format in {"csv", "tsv"} or not base_cli.is_terminal():
        base_cli.render_records(
            records,
            requested_format=output_format,
            columns=(
                ("PROJECT", "project_name"),
                ("TARGET", "target_name"),
                ("WORKING DIR", "working_dir"),
                ("COMMAND", "command"),
                ("DESCRIPTION", "description"),
                ("RUNNER", "runner"),
            ),
        )
    else:
        for target_name, target_config, working_dir in targets:
            print_build_target(
                project,
                manifest,
                target_name,
                target_config,
                working_dir,
                manifest_command_trust_required=False,
            )
    return base_cli.ExitCode.SUCCESS


def build_target_record(  # pylint: disable=too-many-arguments
    project: ProjectLike,
    manifest: BaseManifest,
    target_name: str,
    target_config: BuildTargetConfig,
    working_dir: Path,
    *,
    manifest_command_trust_required: bool,
) -> dict[str, str | bool | None]:
    return {
        "project_name": project.name,
        "project_root": str(project.root),
        "manifest_path": str(project.manifest_path),
        **route_metadata_record(
            manifest,
            manifest_command_trust_required=manifest_command_trust_required,
        ),
        "target_name": target_name,
        "working_dir": str(working_dir),
        "command": target_config.command,
        "description": target_config.description,
        "runner": target_config.runner,
    }


def print_build_target(  # pylint: disable=too-many-arguments
    project: ProjectLike,
    manifest: BaseManifest,
    target_name: str,
    target_config: BuildTargetConfig,
    working_dir: Path,
    *,
    manifest_command_trust_required: bool,
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
    fields.extend(
        route_metadata_fields(
            manifest,
            manifest_command_trust_required=manifest_command_trust_required,
        )
    )
    print("\t".join(fields))


def route_metadata_fields(manifest: BaseManifest, *, manifest_command_trust_required: bool = False) -> list[str]:
    route = route_for_manifest(manifest)
    uses_uv = "true" if route.uses_uv_manager else "false"
    trust_required = "true" if manifest_command_trust_required else "false"
    return [
        f"__base_project_venv_dir={route.project_venv_dir}",
        f"__base_uses_uv_manager={uses_uv}",
        f"__base_manifest_command_trust_required={trust_required}",
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
