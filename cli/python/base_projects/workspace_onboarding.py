from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from base_projects.project_commands import test_command as manifest_test_command
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_statuses import WorkspaceProjectStatus
from base_projects.workspace_statuses import workspace_manifest_project_statuses
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError


@dataclass(frozen=True)
class WorkspaceOnboardingRepository:
    repository: str
    path: Path
    required: bool
    status: str
    discovery_status: str
    manifest: str
    venv: str
    next_action: str
    manifest_path: Path | None = None
    url: str | None = None
    default_branch: str | None = None
    setup_command: str | None = None
    validation_command: str | None = None
    test_command: str | None = None
    clone_command: str | None = None


@dataclass(frozen=True)
class WorkspaceOnboardingSummary:
    workspace_root: Path
    workspace_manifest: WorkspaceManifest
    repositories: tuple[WorkspaceOnboardingRepository, ...]


def workspace_onboarding_summary(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
) -> WorkspaceOnboardingSummary:
    statuses = workspace_manifest_project_statuses(workspace_root, workspace_manifest)
    repositories = tuple(
        onboarding_repository_from_status(status)
        for status in statuses
        if status.expected
    )
    return WorkspaceOnboardingSummary(
        workspace_root=workspace_root,
        workspace_manifest=workspace_manifest,
        repositories=repositories,
    )


def onboarding_repository_from_status(status: WorkspaceProjectStatus) -> WorkspaceOnboardingRepository:
    repository = status.repository or status.root.name
    status_name = onboarding_status(status)
    setup_command = setup_command_for_status(status)
    validation_command = validation_command_for_status(status)
    clone_command = clone_command_for_status(status)
    test_command = test_command_for_status(status)

    return WorkspaceOnboardingRepository(
        repository=repository,
        path=status.root,
        required=status.required,
        status=status_name,
        discovery_status="missing" if status.repo == "missing" else "present",
        manifest=status.manifest,
        venv=status.venv,
        next_action=next_action_for_status(status, status_name),
        manifest_path=status.manifest_path,
        url=status.url,
        default_branch=status.default_branch,
        setup_command=setup_command,
        validation_command=validation_command,
        test_command=test_command,
        clone_command=clone_command,
    )


def onboarding_status(status: WorkspaceProjectStatus) -> str:
    if status.repo == "missing":
        return "missing_required" if status.required else "missing_optional"
    if status.manifest == "missing":
        return "present_without_manifest"
    if status.manifest == "invalid":
        return "invalid_manifest"
    if status.venv in ("ready", "not_applicable"):
        return "ready"
    return "needs_setup"


def setup_command_for_status(status: WorkspaceProjectStatus) -> str | None:
    if status.manifest != "valid":
        return None
    return f"cd {shlex.quote(str(status.root))} && basectl setup"


def validation_command_for_status(status: WorkspaceProjectStatus) -> str | None:
    if status.manifest != "valid":
        return None
    return f"cd {shlex.quote(str(status.root))} && basectl check"


def clone_command_for_status(status: WorkspaceProjectStatus) -> str | None:
    if status.repo != "missing" or status.url is None:
        return None
    return shlex.join(["git", "clone", status.url, str(status.root)])


def test_command_for_status(status: WorkspaceProjectStatus) -> str | None:
    if status.manifest != "valid" or status.manifest_path is None:
        return None
    try:
        manifest = read_manifest(status.manifest_path)
    except ManifestError:
        return None
    if manifest.test is None:
        return None
    return manifest_test_command(manifest.test).command


def next_action_for_status(status: WorkspaceProjectStatus, status_name: str) -> str:
    if status_name == "missing_required":
        return missing_required_next_action(status)
    if status_name == "missing_optional":
        return "optional repository is missing; clone it only if this role needs it."
    if status_name == "present_without_manifest":
        return f"Add or verify {(status.root / 'base_manifest.yaml').resolve()} before Base setup."
    if status_name == "invalid_manifest":
        return f"Fix {status.manifest_path} before Base setup."
    if status_name == "ready":
        return "Run validation command."
    return "Run setup command, then validation command."


def missing_required_next_action(status: WorkspaceProjectStatus) -> str:
    if status.url is not None:
        return f"Clone {status.url} into {status.root}, then run setup."
    repository = status.repository or status.root.name
    return f"Create or clone repository '{repository}' into {status.root}, then run setup."
