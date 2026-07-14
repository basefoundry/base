from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from base_setup.github_manifest import GithubConfig
from base_setup.manifest_schema import CURRENT_MANIFEST_SCHEMA_VERSION


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
    requires_python: str | None = None
    venv_location: str = "project"


@dataclass(frozen=True)
class BaseManifest:
    path: Path
    project_name: str
    brewfile: str | None
    artifacts: tuple[ArtifactRequest, ...]
    project_languages: tuple[str, ...] = ()
    ide: dict[str, IdeConfig] = field(default_factory=dict)
    mise: str | None = None
    test: TestConfig | None = None
    schema_version: int = CURRENT_MANIFEST_SCHEMA_VERSION
    health: HealthConfig = field(default_factory=HealthConfig)
    commands: dict[str, CommandConfig] = field(default_factory=dict)
    activate: ActivateConfig = field(default_factory=ActivateConfig)
    python: PythonConfig = field(default_factory=PythonConfig)
    github: GithubConfig = field(default_factory=GithubConfig)
    demo: DemoConfig | None = None
    build: BuildConfig | None = None
    release: ReleaseConfig | None = None
