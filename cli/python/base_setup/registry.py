from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactDefinition:
    name: str
    artifact_type: str
    manager: str
    package: str
    target: str


_ARTIFACTS = {
    ("python-package", "click"): ArtifactDefinition(
        name="click",
        artifact_type="python-package",
        manager="pip",
        package="click",
        target="project-venv",
    ),
    ("python-package", "PyYAML"): ArtifactDefinition(
        name="PyYAML",
        artifact_type="python-package",
        manager="pip",
        package="PyYAML",
        target="project-venv",
    ),
    ("python-package", "pylint"): ArtifactDefinition(
        name="pylint",
        artifact_type="python-package",
        manager="pip",
        package="pylint",
        target="project-venv",
    ),
    ("python-package", "pytest"): ArtifactDefinition(
        name="pytest",
        artifact_type="python-package",
        manager="pip",
        package="pytest",
        target="project-venv",
    ),
    ("tool", "terraform"): ArtifactDefinition(
        name="terraform",
        artifact_type="tool",
        manager="homebrew",
        package="terraform",
        target="system",
    ),
    ("tool", "kubectl"): ArtifactDefinition(
        name="kubectl",
        artifact_type="tool",
        manager="homebrew",
        package="kubernetes-cli",
        target="system",
    ),
    ("tool", "node"): ArtifactDefinition(
        name="node",
        artifact_type="tool",
        manager="homebrew",
        package="node",
        target="system",
    ),
    ("tool", "nodejs"): ArtifactDefinition(
        name="nodejs",
        artifact_type="tool",
        manager="homebrew",
        package="node",
        target="system",
    ),
    ("python-package", "requests"): ArtifactDefinition(
        name="requests",
        artifact_type="python-package",
        manager="pip",
        package="requests",
        target="project-venv",
    ),
}


def get_artifact_definition(artifact_type: str, name: str) -> ArtifactDefinition | None:
    return _ARTIFACTS.get((artifact_type, name))
