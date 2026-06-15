from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from base_cli.ide_schema import PROJECT_AUTO_SETTING_KEYS
from base_cli.ide_schema import SUPPORTED_IDES
from base_cli.ide_schema import parse_ide_extensions
from base_cli.ide_schema import parse_ide_settings

try:
    import yaml
except ImportError as exc:
    yaml = None
    _yaml_import_error = exc
else:
    _yaml_import_error = None


CURRENT_MANIFEST_SCHEMA_VERSION = 1
ENVIRONMENT_VARIABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMMAND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HOMEBREW_PACKAGE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.+-]+$")
PORT_HEALTH_STATES = {"free", "listening"}
SUPPORTED_PYTHON_MANAGERS = {"uv"}
SUPPORTED_COMMAND_RUNNERS = {"uv"}


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactRequest:
    artifact_type: str
    name: str
    version: str
    bootstrap: bool = False


@dataclass(frozen=True)
class IdeConfig:
    install: bool
    extensions: tuple[str, ...]
    settings: dict[str, Any]


@dataclass(frozen=True)
class TestConfig:
    command: str | None = None
    mise: str | None = None
    runner: str | None = None


@dataclass(frozen=True)
class CommandConfig:
    command: str
    runner: str | None = None


@dataclass(frozen=True)
class DemoConfig:
    script: str
    description: str | None = None
    runner: str | None = None


@dataclass(frozen=True)
class ReleaseGithubConfig:
    repository: str
    release_title: str


@dataclass(frozen=True)
class ReleaseHomebrewConfig:
    required: bool
    tap_repository: str | None = None
    formula_path: str | None = None
    package: str | None = None


@dataclass(frozen=True)
class ReleaseConfig:
    version_file: str
    changelog: str
    tag_prefix: str
    github: ReleaseGithubConfig
    homebrew: ReleaseHomebrewConfig | None = None
    runner: str | None = None


@dataclass(frozen=True)
class BuildTargetConfig:
    command: str
    working_dir: str = "."
    description: str | None = None
    runner: str | None = None


@dataclass(frozen=True)
class BuildConfig:
    default: tuple[str, ...] = ()
    targets: dict[str, BuildTargetConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class PortHealthConfig:
    port: int
    state: str
    name: str | None = None
    host: str = "127.0.0.1"


@dataclass(frozen=True)
class HealthConfig:
    required_env: tuple[str, ...] = ()
    required_ports: tuple[PortHealthConfig, ...] = ()


@dataclass(frozen=True)
class ActivateConfig:
    source: tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonConfig:
    manager: str | None = None


@dataclass(frozen=True)
class BaseManifest:
    path: Path
    project_name: str
    brewfile: str | None
    artifacts: tuple[ArtifactRequest, ...]
    ide: dict[str, IdeConfig] = field(default_factory=dict)
    mise: str | None = None
    test: TestConfig | None = None
    schema_version: int = CURRENT_MANIFEST_SCHEMA_VERSION
    health: HealthConfig = field(default_factory=HealthConfig)
    commands: dict[str, CommandConfig] = field(default_factory=dict)
    activate: ActivateConfig = field(default_factory=ActivateConfig)
    python: PythonConfig = field(default_factory=PythonConfig)
    demo: DemoConfig | None = None
    build: BuildConfig | None = None
    release: ReleaseConfig | None = None


def read_manifest(path: Path) -> BaseManifest:
    if yaml is None:
        raise ManifestError(
            "PyYAML is required to read base_manifest.yaml. "
            "Run 'basectl setup' to install Base Python bootstrap dependencies."
        ) from _yaml_import_error

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping.")

    allowed_top_level = {
        "schema_version",
        "project",
        "brewfile",
        "mise",
        "ide",
        "artifacts",
        "test",
        "health",
        "commands",
        "activate",
        "python",
        "demo",
        "build",
        "release",
    }
    unknown_top_level = sorted(set(data) - allowed_top_level)
    if unknown_top_level:
        raise ManifestError(f"{path}: unsupported top-level keys: {', '.join(unknown_top_level)}.")

    schema_version = _read_schema_version(path, data.get("schema_version"))
    project_name = _read_project_name(path, data.get("project"))
    brewfile = _read_brewfile(path, data.get("brewfile"))
    mise = _read_mise(path, data.get("mise"))
    ide = _read_ide(path, data.get("ide"))
    test = _read_test(path, data.get("test"))
    health = _read_health(path, data.get("health"))
    commands = _read_commands(path, data.get("commands"))
    activate = _read_activate(path, data.get("activate"))
    python = _read_python(path, data.get("python"))
    demo = _read_demo(path, data.get("demo"))
    build = _read_build(path, data.get("build"))
    release = _read_release(path, data.get("release"))
    artifacts = _read_artifacts(path, data.get("artifacts", []))

    return BaseManifest(
        path=path,
        project_name=project_name,
        brewfile=brewfile,
        artifacts=tuple(artifacts),
        ide=ide,
        mise=mise,
        test=test,
        schema_version=schema_version,
        health=health,
        commands=commands,
        activate=activate,
        python=python,
        demo=demo,
        build=build,
        release=release,
    )


def _read_schema_version(path: Path, schema_version_data: Any) -> int:
    if schema_version_data is None:
        return CURRENT_MANIFEST_SCHEMA_VERSION
    if isinstance(schema_version_data, bool) or not isinstance(schema_version_data, int):
        raise ManifestError(f"{path}: schema_version must be an integer when provided.")
    if schema_version_data < 1:
        raise ManifestError(f"{path}: schema_version must be greater than or equal to 1.")
    if schema_version_data > CURRENT_MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            f"{path}: schema_version {schema_version_data} is newer than supported schema version "
            f"{CURRENT_MANIFEST_SCHEMA_VERSION}. Upgrade Base to read this manifest."
        )
    return schema_version_data


def _read_project_name(path: Path, project_data: Any) -> str:
    if not isinstance(project_data, dict):
        raise ManifestError(f"{path}: project must be a mapping.")

    allowed_project_keys = {"name"}
    unknown_project_keys = sorted(set(project_data) - allowed_project_keys)
    if unknown_project_keys:
        raise ManifestError(f"{path}: unsupported project keys: {', '.join(unknown_project_keys)}.")

    project_name = project_data.get("name")
    if not isinstance(project_name, str) or not project_name:
        raise ManifestError(f"{path}: project.name is required.")
    if not COMMAND_NAME_RE.fullmatch(project_name):
        raise ManifestError(
            f"{path}: project.name must be a valid name "
            "(alphanumeric with optional dots, dashes, underscores, or colons)."
        )
    return project_name


def _read_brewfile(path: Path, brewfile_data: Any) -> str | None:
    if brewfile_data is None:
        return None
    if not isinstance(brewfile_data, str) or not brewfile_data.strip():
        raise ManifestError(f"{path}: brewfile must be a non-empty string when provided.")
    return brewfile_data.strip()


def _read_mise(path: Path, mise_data: Any) -> str | None:
    if mise_data is None:
        return None
    if not isinstance(mise_data, str) or not mise_data.strip():
        raise ManifestError(f"{path}: mise must be a non-empty string when provided.")
    return mise_data.strip()


def _read_ide(path: Path, ide_data: Any) -> dict[str, IdeConfig]:
    if ide_data is None:
        return {}
    if not isinstance(ide_data, dict):
        raise ManifestError(f"{path}: ide must be a mapping when provided.")

    unknown_ide_names = sorted(set(ide_data) - SUPPORTED_IDES)
    if unknown_ide_names:
        raise ManifestError(f"{path}: unsupported IDE names: {', '.join(unknown_ide_names)}.")

    ide: dict[str, IdeConfig] = {}
    for ide_name, config_data in ide_data.items():
        ide[ide_name] = _read_ide_config(path, ide_name, config_data)
    return ide


def _read_test(path: Path, test_data: Any) -> TestConfig | None:
    if test_data is None:
        return None
    if not isinstance(test_data, dict):
        raise ManifestError(f"{path}: test must be a mapping when provided.")

    allowed_keys = {"command", "mise", "runner"}
    unknown_keys = sorted(set(test_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: test has unsupported keys: {', '.join(unknown_keys)}.")

    command = test_data.get("command")
    mise = test_data.get("mise")
    if command is not None and (not isinstance(command, str) or not command.strip()):
        raise ManifestError(f"{path}: test.command must be a non-empty string when provided.")
    if mise is not None and (not isinstance(mise, str) or not mise.strip()):
        raise ManifestError(f"{path}: test.mise must be a non-empty string when provided.")
    if command is not None and mise is not None:
        raise ManifestError(f"{path}: test must declare only one of command or mise.")
    if command is None and mise is None:
        raise ManifestError(f"{path}: test must declare command or mise.")

    return TestConfig(
        command=command.strip() if command is not None else None,
        mise=mise.strip() if mise is not None else None,
        runner=_read_optional_runner(path, "test.runner", test_data.get("runner")),
    )


def _read_demo(path: Path, demo_data: Any) -> DemoConfig | None:
    if demo_data is None:
        return None
    if not isinstance(demo_data, dict):
        raise ManifestError(f"{path}: demo must be a mapping when provided.")

    allowed_keys = {"script", "description", "runner"}
    unknown_keys = sorted(set(demo_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: demo has unsupported keys: {', '.join(unknown_keys)}.")

    script = demo_data.get("script")
    if not isinstance(script, str) or not script.strip():
        raise ManifestError(f"{path}: demo.script must be a non-empty string when demo is provided.")
    script = script.strip()
    if any(separator in script for separator in ("\0", "\n", "\r")):
        raise ManifestError(f"{path}: demo.script must not contain control line breaks.")

    description = demo_data.get("description")
    if description is not None:
        if not isinstance(description, str) or not description.strip():
            raise ManifestError(f"{path}: demo.description must be a non-empty string when provided.")
        description = description.strip()

    runner = _read_optional_runner(path, "demo.runner", demo_data.get("runner"))

    return DemoConfig(script=script, description=description, runner=runner)


def _read_build(path: Path, build_data: Any) -> BuildConfig | None:
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


def _read_release(path: Path, release_data: Any) -> ReleaseConfig | None:
    if release_data is None:
        return None
    if not isinstance(release_data, dict):
        raise ManifestError(f"{path}: release must be a mapping when provided.")

    allowed_keys = {"version_file", "changelog", "tag_prefix", "github", "homebrew", "runner"}
    unknown_keys = sorted(set(release_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: release has unsupported keys: {', '.join(unknown_keys)}.")

    version_file = _read_release_relative_path(
        path,
        "release.version_file",
        release_data.get("version_file", "VERSION"),
    )
    changelog = _read_release_relative_path(
        path,
        "release.changelog",
        release_data.get("changelog", "CHANGELOG.md"),
    )
    tag_prefix = _read_release_string(path, "release.tag_prefix", release_data.get("tag_prefix", "v"))
    github = _read_release_github(path, release_data.get("github"))
    homebrew = _read_release_homebrew(path, release_data.get("homebrew"))

    return ReleaseConfig(
        version_file=version_file,
        changelog=changelog,
        tag_prefix=tag_prefix,
        github=github,
        homebrew=homebrew,
        runner=_read_optional_runner(path, "release.runner", release_data.get("runner")),
    )


def _read_release_github(path: Path, github_data: Any) -> ReleaseGithubConfig:
    if not isinstance(github_data, dict):
        raise ManifestError(f"{path}: release.github must be a mapping.")

    allowed_keys = {"repository", "release_title"}
    unknown_keys = sorted(set(github_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: release.github has unsupported keys: {', '.join(unknown_keys)}.")

    repository = _read_release_repository(path, "release.github.repository", github_data.get("repository"))
    release_title = _read_release_string(
        path,
        "release.github.release_title",
        github_data.get("release_title", "{repository} v{version}"),
    )
    return ReleaseGithubConfig(repository=repository, release_title=release_title)


def _read_release_homebrew(path: Path, homebrew_data: Any) -> ReleaseHomebrewConfig | None:
    if homebrew_data is None:
        return None
    if not isinstance(homebrew_data, dict):
        raise ManifestError(f"{path}: release.homebrew must be a mapping when provided.")

    allowed_keys = {"required", "tap_repository", "formula_path", "package"}
    unknown_keys = sorted(set(homebrew_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: release.homebrew has unsupported keys: {', '.join(unknown_keys)}.")

    required = homebrew_data.get("required", True)
    if not isinstance(required, bool):
        raise ManifestError(f"{path}: release.homebrew.required must be a boolean when provided.")

    tap_repository = _read_optional_release_repository(
        path,
        "release.homebrew.tap_repository",
        homebrew_data.get("tap_repository"),
    )
    formula_path = _read_optional_release_relative_path(
        path,
        "release.homebrew.formula_path",
        homebrew_data.get("formula_path"),
    )
    package = _read_optional_homebrew_package(
        path,
        "release.homebrew.package",
        homebrew_data.get("package"),
    )

    if required:
        missing = [
            field_name
            for field_name, field_value in (
                ("tap_repository", tap_repository),
                ("formula_path", formula_path),
                ("package", package),
            )
            if field_value is None
        ]
        if missing:
            raise ManifestError(
                f"{path}: release.homebrew required fields are missing: {', '.join(missing)}."
            )

    return ReleaseHomebrewConfig(
        required=required,
        tap_repository=tap_repository,
        formula_path=formula_path,
        package=package,
    )


def _read_release_repository(path: Path, field_name: str, value: Any) -> str:
    repository = _read_release_string(path, field_name, value)
    if not GITHUB_REPOSITORY_RE.fullmatch(repository):
        raise ManifestError(f"{path}: {field_name} must use owner/name format.")
    return repository


def _read_optional_release_repository(path: Path, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _read_release_repository(path, field_name, value)


def _read_optional_homebrew_package(path: Path, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    package = _read_release_string(path, field_name, value)
    if not HOMEBREW_PACKAGE_RE.fullmatch(package):
        raise ManifestError(f"{path}: {field_name} must use owner/tap/formula format.")
    return package


def _read_release_relative_path(path: Path, field_name: str, value: Any) -> str:
    release_path = _read_release_string(path, field_name, value)
    parsed_path = Path(release_path)
    if parsed_path.is_absolute() or ".." in parsed_path.parts:
        raise ManifestError(f"{path}: {field_name} must be a relative path inside the project.")
    return release_path


def _read_optional_release_relative_path(path: Path, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _read_release_relative_path(path, field_name, value)


def _read_release_string(path: Path, field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{path}: {field_name} must be a non-empty string.")
    value = value.strip()
    if _has_control_line_break(value):
        raise ManifestError(f"{path}: {field_name} must not contain control line breaks.")
    return value


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
    if _has_control_line_break(command):
        raise ManifestError(f"{path}: build.targets.{target_name}.command must not contain control line breaks.")

    working_dir = target_data.get("working_dir", ".")
    if not isinstance(working_dir, str) or not working_dir.strip():
        raise ManifestError(f"{path}: build.targets.{target_name}.working_dir must be a non-empty string.")
    working_dir = working_dir.strip()
    if _has_control_line_break(working_dir):
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
        if _has_control_line_break(description):
            raise ManifestError(
                f"{path}: build.targets.{target_name}.description must not contain control line breaks."
            )

    runner = _read_optional_runner(path, f"build.targets.{target_name}.runner", target_data.get("runner"))

    return BuildTargetConfig(command=command, working_dir=working_dir, description=description, runner=runner)


def _read_health(path: Path, health_data: Any) -> HealthConfig:
    if health_data is None:
        return HealthConfig()
    if not isinstance(health_data, dict):
        raise ManifestError(f"{path}: health must be a mapping when provided.")

    allowed_keys = {"required_env", "required_ports"}
    unknown_keys = sorted(set(health_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: health has unsupported keys: {', '.join(unknown_keys)}.")

    return HealthConfig(
        required_env=_read_required_env(path, health_data.get("required_env", [])),
        required_ports=_read_required_ports(path, health_data.get("required_ports", [])),
    )


def _read_commands(path: Path, commands_data: Any) -> dict[str, CommandConfig]:
    if commands_data is None:
        return {}
    if not isinstance(commands_data, dict):
        raise ManifestError(f"{path}: commands must be a mapping when provided.")

    commands: dict[str, CommandConfig] = {}
    for command_name_data, command_data in commands_data.items():
        if not isinstance(command_name_data, str) or not command_name_data.strip():
            raise ManifestError(f"{path}: commands keys must be non-empty strings.")
        command_name = command_name_data.strip()
        if not COMMAND_NAME_RE.fullmatch(command_name):
            raise ManifestError(f"{path}: commands.{command_name} must be a valid command name.")
        if command_name == "test":
            raise ManifestError(f"{path}: commands.test is reserved; use top-level test.command or test.mise.")
        if command_name in commands:
            raise ManifestError(f"{path}: commands duplicates '{command_name}'.")
        commands[command_name] = _read_command_config(path, f"commands.{command_name}", command_data)
    return commands


def _read_command_config(path: Path, field_name: str, command_data: Any) -> CommandConfig:
    if isinstance(command_data, str):
        if not command_data.strip():
            raise ManifestError(f"{path}: {field_name} must be a non-empty string.")
        return CommandConfig(command=command_data.strip())

    if not isinstance(command_data, dict):
        raise ManifestError(f"{path}: {field_name} must be a non-empty string or command mapping.")

    allowed_keys = {"command", "runner"}
    unknown_keys = sorted(set(command_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: {field_name} has unsupported keys: {', '.join(unknown_keys)}.")

    command = command_data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ManifestError(f"{path}: {field_name}.command must be a non-empty string.")
    if _has_control_line_break(command):
        raise ManifestError(f"{path}: {field_name}.command must not contain control line breaks.")

    return CommandConfig(
        command=command.strip(),
        runner=_read_optional_runner(path, f"{field_name}.runner", command_data.get("runner")),
    )


def _read_activate(path: Path, activate_data: Any) -> ActivateConfig:
    if activate_data is None:
        return ActivateConfig()
    if not isinstance(activate_data, dict):
        raise ManifestError(f"{path}: activate must be a mapping when provided.")

    allowed_keys = {"source"}
    unknown_keys = sorted(set(activate_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: activate has unsupported keys: {', '.join(unknown_keys)}.")

    return ActivateConfig(source=_read_activate_sources(path, activate_data.get("source", [])))


def _read_python(path: Path, python_data: Any) -> PythonConfig:
    if python_data is None:
        return PythonConfig()
    if not isinstance(python_data, dict):
        raise ManifestError(f"{path}: python must be a mapping when provided.")

    allowed_keys = {"manager"}
    unknown_keys = sorted(set(python_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: python has unsupported keys: {', '.join(unknown_keys)}.")

    manager = python_data.get("manager")
    if manager is None:
        return PythonConfig()
    if not isinstance(manager, str) or not manager.strip():
        raise ManifestError(f"{path}: python.manager must be a non-empty string when provided.")
    manager = manager.strip()
    if manager not in SUPPORTED_PYTHON_MANAGERS:
        supported = ", ".join(sorted(SUPPORTED_PYTHON_MANAGERS))
        raise ManifestError(f"{path}: python.manager must be one of: {supported}.")
    return PythonConfig(manager=manager)


def _read_optional_runner(path: Path, field_name: str, runner_data: Any) -> str | None:
    if runner_data is None:
        return None
    if not isinstance(runner_data, str) or not runner_data.strip():
        raise ManifestError(f"{path}: {field_name} must be a non-empty string when provided.")
    runner = runner_data.strip()
    if runner not in SUPPORTED_COMMAND_RUNNERS:
        supported = ", ".join(sorted(SUPPORTED_COMMAND_RUNNERS))
        raise ManifestError(f"{path}: {field_name} must be one of: {supported}.")
    return runner


def _read_activate_sources(path: Path, source_data: Any) -> tuple[str, ...]:
    if source_data is None:
        return ()
    if not isinstance(source_data, list):
        raise ManifestError(f"{path}: activate.source must be a list when provided.")

    sources: list[str] = []
    seen: set[str] = set()
    for index, source_path_data in enumerate(source_data, start=1):
        if not isinstance(source_path_data, str) or not source_path_data.strip():
            raise ManifestError(f"{path}: activate.source[{index}] must be a non-empty string.")
        source_path = source_path_data.strip()
        if any(separator in source_path for separator in ("\0", "\n", "\r")):
            raise ManifestError(f"{path}: activate.source[{index}] must not contain control line breaks.")
        if source_path in seen:
            raise ManifestError(f"{path}: activate.source[{index}] duplicates '{source_path}'.")
        seen.add(source_path)
        sources.append(source_path)
    return tuple(sources)


def _read_required_env(path: Path, required_env_data: Any) -> tuple[str, ...]:
    if required_env_data is None:
        return ()
    if not isinstance(required_env_data, list):
        raise ManifestError(f"{path}: health.required_env must be a list when provided.")

    required_env: list[str] = []
    seen: set[str] = set()
    for index, env_name_data in enumerate(required_env_data, start=1):
        if not isinstance(env_name_data, str) or not env_name_data.strip():
            raise ManifestError(f"{path}: health.required_env[{index}] must be a non-empty string.")
        env_name = env_name_data.strip()
        if not ENVIRONMENT_VARIABLE_NAME_RE.fullmatch(env_name):
            raise ManifestError(
                f"{path}: health.required_env[{index}] must be a valid environment variable name."
            )
        if env_name in seen:
            raise ManifestError(f"{path}: health.required_env[{index}] duplicates '{env_name}'.")
        seen.add(env_name)
        required_env.append(env_name)
    return tuple(required_env)


def _read_required_ports(path: Path, required_ports_data: Any) -> tuple[PortHealthConfig, ...]:
    if required_ports_data is None:
        return ()
    if not isinstance(required_ports_data, list):
        raise ManifestError(f"{path}: health.required_ports must be a list when provided.")

    required_ports: list[PortHealthConfig] = []
    seen_endpoints: set[tuple[str, int]] = set()
    seen_names: set[str] = set()
    for index, port_data in enumerate(required_ports_data, start=1):
        required_ports.append(
            _read_required_port(path, index, port_data, seen_endpoints, seen_names)
        )

    return tuple(required_ports)


def _read_required_port(
    path: Path,
    index: int,
    port_data: Any,
    seen_endpoints: set[tuple[str, int]],
    seen_names: set[str],
) -> PortHealthConfig:
    if not isinstance(port_data, dict):
        raise ManifestError(f"{path}: health.required_ports[{index}] must be a mapping.")

    allowed_keys = {"name", "host", "port", "state"}
    unknown_keys = sorted(set(port_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(
            f"{path}: health.required_ports[{index}] has unsupported keys: "
            f"{', '.join(unknown_keys)}."
        )

    port = _read_required_port_number(path, index, port_data.get("port"))
    state = _read_required_port_state(path, index, port_data.get("state"))
    name = _read_required_port_name(path, index, port_data.get("name"), seen_names)
    host = _read_required_port_host(path, index, port_data.get("host", "127.0.0.1"))
    endpoint = (host, port)
    if endpoint in seen_endpoints:
        raise ManifestError(f"{path}: health.required_ports[{index}] duplicates '{host}:{port}'.")
    seen_endpoints.add(endpoint)
    return PortHealthConfig(port=port, state=state, name=name, host=host)


def _read_required_port_number(path: Path, index: int, port_data: Any) -> int:
    if isinstance(port_data, bool) or not isinstance(port_data, int):
        raise ManifestError(f"{path}: health.required_ports[{index}].port must be an integer.")
    if port_data < 1 or port_data > 65535:
        raise ManifestError(
            f"{path}: health.required_ports[{index}].port must be between 1 and 65535."
        )
    return port_data


def _read_required_port_state(path: Path, index: int, state_data: Any) -> str:
    if not isinstance(state_data, str) or not state_data.strip():
        raise ManifestError(
            f"{path}: health.required_ports[{index}].state must be a non-empty string."
        )
    state = state_data.strip()
    if state not in PORT_HEALTH_STATES:
        supported_states = ", ".join(sorted(PORT_HEALTH_STATES))
        raise ManifestError(
            f"{path}: health.required_ports[{index}].state must be one of: {supported_states}."
        )
    return state


def _read_required_port_name(
    path: Path,
    index: int,
    name_data: Any,
    seen_names: set[str],
) -> str | None:
    if name_data is None:
        return None
    if not isinstance(name_data, str) or not name_data.strip():
        raise ManifestError(
            f"{path}: health.required_ports[{index}].name must be a non-empty string."
        )
    name = name_data.strip()
    if _has_control_line_break(name):
        raise ManifestError(
            f"{path}: health.required_ports[{index}].name must not contain control line breaks."
        )
    if name in seen_names:
        raise ManifestError(f"{path}: health.required_ports[{index}].name duplicates '{name}'.")
    seen_names.add(name)
    return name


def _read_required_port_host(path: Path, index: int, host_data: Any) -> str:
    if not isinstance(host_data, str) or not host_data.strip():
        raise ManifestError(
            f"{path}: health.required_ports[{index}].host must be a non-empty string."
        )
    host = host_data.strip()
    if _has_control_line_break(host):
        raise ManifestError(
            f"{path}: health.required_ports[{index}].host must not contain control line breaks."
        )
    return host


def _has_control_line_break(value: str) -> bool:
    return any(separator in value for separator in ("\0", "\n", "\r"))


def _read_ide_config(path: Path, ide_name: str, config_data: Any) -> IdeConfig:
    if config_data is None:
        config_data = {}
    if not isinstance(config_data, dict):
        raise ManifestError(f"{path}: ide.{ide_name} must be a mapping.")

    allowed_keys = {"install", "extensions", "settings"}
    unknown_keys = sorted(set(config_data) - allowed_keys)
    if unknown_keys:
        raise ManifestError(f"{path}: ide.{ide_name} has unsupported keys: {', '.join(unknown_keys)}.")

    install = config_data.get("install", False)
    if not isinstance(install, bool):
        raise ManifestError(f"{path}: ide.{ide_name}.install must be a boolean when provided.")

    extensions = _read_ide_extensions(path, ide_name, config_data.get("extensions", []))
    settings = _read_ide_settings(path, ide_name, config_data.get("settings", {}))

    return IdeConfig(install=install, extensions=extensions, settings=settings)


def _read_ide_extensions(path: Path, ide_name: str, extensions_data: Any) -> tuple[str, ...]:
    try:
        return parse_ide_extensions(f"{path}: ide.{ide_name}.extensions", extensions_data)
    except ValueError as exc:
        raise ManifestError(str(exc)) from exc


def _read_ide_settings(path: Path, ide_name: str, settings_data: Any) -> dict[str, Any]:
    try:
        return parse_ide_settings(
            f"{path}: ide.{ide_name}.settings",
            settings_data,
            auto_setting_keys=PROJECT_AUTO_SETTING_KEYS,
        )
    except ValueError as exc:
        raise ManifestError(str(exc)) from exc


def _read_artifacts(path: Path, artifacts_data: Any) -> list[ArtifactRequest]:
    if artifacts_data is None:
        return []
    if not isinstance(artifacts_data, list):
        raise ManifestError(f"{path}: artifacts must be a list.")

    artifacts: list[ArtifactRequest] = []
    for index, artifact_data in enumerate(artifacts_data, start=1):
        artifacts.append(_read_artifact(path, artifact_data, index))
    return artifacts


def _read_artifact(path: Path, artifact_data: Any, index: int) -> ArtifactRequest:
    if not isinstance(artifact_data, dict):
        raise ManifestError(f"{path}: artifacts[{index}] must be a mapping.")

    required_artifact_keys = {"type", "name", "version"}
    allowed_artifact_keys = required_artifact_keys | {"bootstrap"}
    unknown_artifact_keys = sorted(set(artifact_data) - allowed_artifact_keys)
    if unknown_artifact_keys:
        raise ManifestError(
            f"{path}: artifacts[{index}] has unsupported keys: {', '.join(unknown_artifact_keys)}."
        )

    missing = sorted(key for key in required_artifact_keys if not artifact_data.get(key))
    if missing:
        raise ManifestError(f"{path}: artifacts[{index}] is missing required keys: {', '.join(missing)}.")

    artifact_type = artifact_data["type"]
    name = artifact_data["name"]
    version = artifact_data["version"]
    if not all(isinstance(value, str) for value in (artifact_type, name, version)):
        raise ManifestError(f"{path}: artifacts[{index}] type, name, and version must be strings.")
    bootstrap = artifact_data.get("bootstrap", False)
    if not isinstance(bootstrap, bool):
        raise ManifestError(f"{path}: artifacts[{index}] bootstrap must be a boolean when provided.")

    return ArtifactRequest(
        artifact_type=artifact_type,
        name=name,
        version=version,
        bootstrap=bootstrap,
    )
