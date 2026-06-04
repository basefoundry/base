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
    ("tool", "bats-core"): ArtifactDefinition(
        name="bats-core",
        artifact_type="tool",
        manager="homebrew",
        package="bats-core",
        target="system",
    ),
    ("tool", "gh"): ArtifactDefinition(
        name="gh",
        artifact_type="tool",
        manager="homebrew",
        package="gh",
        target="system",
    ),
    ("tool", "shellcheck"): ArtifactDefinition(
        name="shellcheck",
        artifact_type="tool",
        manager="homebrew",
        package="shellcheck",
        target="system",
    ),
    ("tool", "docker"): ArtifactDefinition(
        name="docker",
        artifact_type="tool",
        manager="homebrew",
        package="docker",
        target="system",
    ),
    ("tool", "colima"): ArtifactDefinition(
        name="colima",
        artifact_type="tool",
        manager="homebrew",
        package="colima",
        target="system",
    ),
    ("tool", "kubectl"): ArtifactDefinition(
        name="kubectl",
        artifact_type="tool",
        manager="homebrew",
        package="kubernetes-cli",
        target="system",
    ),
    ("tool", "helm"): ArtifactDefinition(
        name="helm",
        artifact_type="tool",
        manager="homebrew",
        package="helm",
        target="system",
    ),
    ("tool", "k9s"): ArtifactDefinition(
        name="k9s",
        artifact_type="tool",
        manager="homebrew",
        package="k9s",
        target="system",
    ),
    ("tool", "httpie"): ArtifactDefinition(
        name="httpie",
        artifact_type="tool",
        manager="homebrew",
        package="httpie",
        target="system",
    ),
    ("tool", "grpcurl"): ArtifactDefinition(
        name="grpcurl",
        artifact_type="tool",
        manager="homebrew",
        package="grpcurl",
        target="system",
    ),
    ("tool", "jq"): ArtifactDefinition(
        name="jq",
        artifact_type="tool",
        manager="homebrew",
        package="jq",
        target="system",
    ),
    ("tool", "yq"): ArtifactDefinition(
        name="yq",
        artifact_type="tool",
        manager="homebrew",
        package="yq",
        target="system",
    ),
    ("tool", "nmap"): ArtifactDefinition(
        name="nmap",
        artifact_type="tool",
        manager="homebrew",
        package="nmap",
        target="system",
    ),
    ("tool", "mtr"): ArtifactDefinition(
        name="mtr",
        artifact_type="tool",
        manager="homebrew",
        package="mtr",
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
    definition = _ARTIFACTS.get((artifact_type, name))
    if definition is not None:
        return definition

    if artifact_type == "python-package":
        return ArtifactDefinition(
            name=name,
            artifact_type=artifact_type,
            manager="pip",
            package=name,
            target="project-venv",
        )

    return None
