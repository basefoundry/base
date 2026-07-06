from __future__ import annotations

from pathlib import Path
from typing import Any

from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import BuildConfig
from base_setup.manifest_model import BuildTargetConfig
from base_setup.manifest_reader_common import read_optional_runner
from base_setup.manifest_schema import COMMAND_NAME_RE
from base_setup.manifest_schema import has_control_line_break


def read_build_config(path: Path, build_data: Any) -> BuildConfig | None:
    if build_data is None:
        return None
    if not isinstance(build_data, dict):
        raise ManifestError(f"{path}: build must be a mapping when provided.")

    allowed_keys = {"default", "targets"}
    unknown_keys = sorted(set(build_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: build has unsupported keys: {', '.join(unknown_keys)}.")

    targets = _read_build_targets(path, build_data.get("targets", {}))
    default = _read_build_default(path, build_data.get("default", []), targets)
    return BuildConfig(default=default, targets=targets)


def _read_build_default(
    path: Path,
    default_data: Any,
    targets: dict[str, BuildTargetConfig],
) -> tuple[str, ...]:
    if default_data is None:
        return ()
    if not isinstance(default_data, list):
        raise ManifestError(f"{path}: build.default must be a list when provided.")

    default: list[str] = []
    seen: set[str] = set()
    for index, target_data in enumerate(default_data, start=1):
        if not isinstance(target_data, str) or not target_data.strip():
            raise ManifestError(f"{path}: build.default[{index}] must be a non-empty string.")
        target_name = target_data.strip()
        if not COMMAND_NAME_RE.fullmatch(target_name):
            raise ManifestError(f"{path}: build.default[{index}] must be a valid target name.")
        if target_name in seen:
            raise ManifestError(f"{path}: build.default[{index}] duplicates '{target_name}'.")
        if target_name not in targets:
            raise ManifestError(f"{path}: build.default[{index}] references unknown target '{target_name}'.")
        seen.add(target_name)
        default.append(target_name)
    return tuple(default)


def _read_build_targets(path: Path, targets_data: Any) -> dict[str, BuildTargetConfig]:
    if targets_data is None:
        return {}
    if not isinstance(targets_data, dict):
        raise ManifestError(f"{path}: build.targets must be a mapping when provided.")

    targets: dict[str, BuildTargetConfig] = {}
    for target_name_data, target_data in targets_data.items():
        if not isinstance(target_name_data, str) or not target_name_data.strip():
            raise ManifestError(f"{path}: build.targets keys must be non-empty strings.")
        target_name = target_name_data.strip()
        if not COMMAND_NAME_RE.fullmatch(target_name):
            raise ManifestError(f"{path}: build.targets.{target_name} must be a valid target name.")
        if target_name in targets:
            raise ManifestError(f"{path}: build.targets duplicates '{target_name}'.")
        targets[target_name] = _read_build_target(path, target_name, target_data)
    return targets


def _read_build_target(path: Path, target_name: str, target_data: Any) -> BuildTargetConfig:
    if not isinstance(target_data, dict):
        raise ManifestError(f"{path}: build.targets.{target_name} must be a mapping.")

    allowed_keys = {"command", "working_dir", "description", "runner"}
    unknown_keys = sorted(set(target_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(
            f"{path}: build.targets.{target_name} has unsupported keys: {', '.join(unknown_keys)}."
        )

    command = target_data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ManifestError(f"{path}: build.targets.{target_name}.command must be a non-empty string.")
    command = command.strip()
    if has_control_line_break(command):
        raise ManifestError(f"{path}: build.targets.{target_name}.command must not contain control line breaks.")

    working_dir = target_data.get("working_dir", ".")
    if not isinstance(working_dir, str) or not working_dir.strip():
        raise ManifestError(f"{path}: build.targets.{target_name}.working_dir must be a non-empty string.")
    working_dir = working_dir.strip()
    if has_control_line_break(working_dir):
        raise ManifestError(
            f"{path}: build.targets.{target_name}.working_dir must not contain control line breaks."
        )

    description = target_data.get("description")
    if description is not None:
        if not isinstance(description, str) or not description.strip():
            raise ManifestError(
                f"{path}: build.targets.{target_name}.description must be a non-empty string when provided."
            )
        description = description.strip()
        if has_control_line_break(description):
            raise ManifestError(
                f"{path}: build.targets.{target_name}.description must not contain control line breaks."
            )

    runner = read_optional_runner(path, f"build.targets.{target_name}.runner", target_data.get("runner"))

    return BuildTargetConfig(command=command, working_dir=working_dir, description=description, runner=runner)
