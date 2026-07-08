from __future__ import annotations

import shlex
from pathlib import Path

from base_projects.project_discovery import Project
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.manifest_model import BaseManifest
from base_setup.manifest_model import CommandConfig
from base_setup.manifest_model import TestConfig
from base_setup.project_routing import route_for_manifest


def test_command(test_config: TestConfig) -> CommandConfig:
    if test_config.command is not None:
        return CommandConfig(command=test_config.command, runner=test_config.runner)
    if test_config.mise is not None:
        return CommandConfig(command=shlex.join(["mise", "run", test_config.mise]), runner=test_config.runner)
    raise ValueError("TestConfig must have command or mise set.")


class ProjectCommandError(RuntimeError):
    pass


def project_commands(manifest: BaseManifest) -> dict[str, CommandConfig]:
    commands: dict[str, CommandConfig] = {}
    if manifest.test is not None:
        commands["test"] = test_command(manifest.test)
    commands.update(manifest.commands)
    return commands


def project_command(manifest: BaseManifest, command_name: str) -> CommandConfig:
    commands = project_commands(manifest)
    try:
        return commands[command_name]
    except KeyError as exc:
        if command_name == "test":
            raise ProjectCommandError(
                f"Project '{manifest.project_name}' does not declare test.command or test.mise in '{manifest.path}'."
            ) from exc
        raise ProjectCommandError(
            f"Project '{manifest.project_name}' does not declare command '{command_name}' in '{manifest.path}'."
        ) from exc


def route_metadata_fields(manifest: BaseManifest, *, manifest_command_trust_required: bool = False) -> list[str]:
    route = route_for_manifest(manifest)
    uses_uv = "true" if route.uses_uv_manager else "false"
    trust_required = "true" if manifest_command_trust_required else "false"
    return [
        f"__base_project_venv_dir={route.project_venv_dir}",
        f"__base_uses_uv_manager={uses_uv}",
        f"__base_manifest_command_trust_required={trust_required}",
    ]


def project_output(project_name: str, project_root: Path, manifest_path: Path, manifest: BaseManifest) -> str:
    return "\t".join(
        [
            project_name,
            str(project_root),
            str(manifest_path),
            *route_metadata_fields(
                manifest,
                manifest_command_trust_required=bool(manifest.activate.source),
            ),
        ]
    )


def command_output(
    project_name: str,
    project_root: Path,
    manifest_path: Path,
    command: CommandConfig,
    manifest: BaseManifest,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), command.command]
    if command.runner is not None:
        fields.append(command.runner)
    fields.extend(route_metadata_fields(manifest, manifest_command_trust_required=True))
    return "\t".join(fields)


def named_command_output(
    project_name: str,
    project_root: Path,
    manifest_path: Path,
    command_name: str,
    command: CommandConfig,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), command_name, command.command]
    if command.runner is not None:
        fields.append(command.runner)
    return "\t".join(fields)


def demo_output(
    project_name: str,
    project_root: Path,
    manifest_path: Path,
    demo_script: Path,
    manifest: BaseManifest,
) -> str:
    fields = [project_name, str(project_root), str(manifest_path), str(demo_script)]
    if manifest.demo.runner is not None:
        fields.append(manifest.demo.runner)
    fields.extend(route_metadata_fields(manifest, manifest_command_trust_required=True))
    return "\t".join(fields)


def activation_source_paths(project: Project, source_paths: tuple[str, ...]) -> tuple[Path, ...]:
    return tuple(
        resolve_activation_source_path(project, source_path, index)
        for index, source_path in enumerate(source_paths, start=1)
    )


def resolve_activation_source_path(project: Project, source_path: str, index: int) -> Path:
    field = f"activate.source[{index}]"
    project_root = project.root.resolve()
    declared_path = Path(source_path)
    if declared_path.is_absolute():
        raise ProjectDiscoveryError(
            f"{project.manifest_path}: {field} must be a relative path inside the project root."
        )

    candidate = (project_root / declared_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ProjectDiscoveryError(
            f"{project.manifest_path}: {field} resolves outside the project root: {source_path}."
        ) from exc

    if not candidate.exists():
        raise ProjectDiscoveryError(f"{project.manifest_path}: {field} script '{source_path}' does not exist.")
    if not candidate.is_file():
        raise ProjectDiscoveryError(f"{project.manifest_path}: {field} script '{source_path}' is not a file.")
    return candidate
