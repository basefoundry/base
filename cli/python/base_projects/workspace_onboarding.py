from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from base_trust.guidance import allow_command_text
from base_trust.trust_store import ManifestCommandTrustStore
from base_trust.trust_store import compute_trust_identity
from base_trust.trust_store import manifest_command_surfaces_from_manifest
from base_projects.project_commands import test_command as manifest_test_command
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_repository_url import redact_repository_url
from base_projects.workspace_statuses import WorkspaceProjectStatus
from base_projects.workspace_statuses import workspace_manifest_project_statuses
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.runtime_inspection import runtime_verification_command


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
    trust_command: str | None = None


@dataclass(frozen=True)
class WorkspaceOnboardingSummary:
    workspace_root: Path
    workspace_manifest: WorkspaceManifest
    repositories: tuple[WorkspaceOnboardingRepository, ...]


@dataclass(frozen=True)
class WorkspaceNextAction:
    order: int
    description: str
    commands: tuple[str, ...]


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


def workspace_onboarding_next_actions(
    summary: WorkspaceOnboardingSummary,
) -> tuple[WorkspaceNextAction, ...]:
    """Build a deterministic, executable remediation sequence for a workspace."""
    actions: list[WorkspaceNextAction] = []

    missing_required = tuple(
        repository
        for repository in summary.repositories
        if repository.required and repository.status == "missing_required"
    )
    if missing_required:
        clone_commands = tuple(
            repository.clone_command
            for repository in missing_required
            if repository.clone_command is not None
        )
        if not clone_commands:
            clone_commands = (workspace_clone_command(summary),)
        actions.append(
            WorkspaceNextAction(
                order=len(actions) + 1,
                description="Clone missing repos",
                commands=clone_commands,
            )
        )

    setup_commands = tuple(
        repository.setup_command
        for repository in summary.repositories
        if repository.setup_command is not None and repository.status == "needs_setup"
    )
    if setup_commands:
        actions.append(
            WorkspaceNextAction(
                order=len(actions) + 1,
                description="Set up unconfigured projects",
                commands=setup_commands,
            )
        )

    trust_commands = tuple(
        repository.trust_command
        for repository in summary.repositories
        if repository.trust_command is not None
    )
    if trust_commands:
        actions.append(
            WorkspaceNextAction(
                order=len(actions) + 1,
                description="Trust new manifests",
                commands=trust_commands,
            )
        )

    if actions or any(repository.status == "needs_verification" for repository in summary.repositories):
        actions.append(
            WorkspaceNextAction(
                order=len(actions) + 1,
                description="Review runtimes and verify workspace health",
                commands=(workspace_check_command(summary),),
            )
        )

    return tuple(actions)


def workspace_clone_command(summary: WorkspaceOnboardingSummary) -> str:
    return shlex.join(
        [
            "basectl",
            "workspace",
            "clone",
            "--workspace",
            str(summary.workspace_root),
            "--manifest",
            str(summary.workspace_manifest.path),
        ]
    )


def workspace_check_command(summary: WorkspaceOnboardingSummary) -> str:
    return shlex.join(
        [
            "basectl",
            "workspace",
            "check",
            "--workspace",
            str(summary.workspace_root),
            "--manifest",
            str(summary.workspace_manifest.path),
            "--verify-project-runtime",
        ]
    )


def onboarding_repository_from_status(status: WorkspaceProjectStatus) -> WorkspaceOnboardingRepository:
    repository = status.repository or status.root.name
    status_name = onboarding_status(status)
    setup_command = setup_command_for_status(status)
    validation_command = validation_command_for_status(status)
    clone_command = clone_command_for_status(status)
    test_command = test_command_for_status(status)
    trust_command = trust_command_for_status(status)

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
        url=redact_repository_url(status.url) if status.url is not None else None,
        default_branch=status.default_branch,
        setup_command=setup_command,
        validation_command=validation_command,
        test_command=test_command,
        clone_command=clone_command,
        trust_command=trust_command,
    )


def onboarding_status(status: WorkspaceProjectStatus) -> str:
    if status.repo == "missing":
        return "missing_required" if status.required else "missing_optional"
    if status.manifest == "missing":
        return "present_without_manifest"
    if status.manifest == "invalid":
        return "invalid_manifest"
    if status.venv == "present_unverified":
        return "needs_verification"
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
    if status.venv == "present_unverified" and status.manifest_path is not None:
        return runtime_verification_command(status.manifest_path)
    return f"cd {shlex.quote(str(status.root))} && basectl check"


def clone_command_for_status(status: WorkspaceProjectStatus) -> str | None:
    if status.repo != "missing" or status.url is None:
        return None
    return shlex.join(["git", "clone", redact_repository_url(status.url), str(status.root)])


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


def trust_command_for_status(status: WorkspaceProjectStatus) -> str | None:
    if status.manifest != "valid" or status.manifest_path is None:
        return None
    try:
        manifest = read_manifest(status.manifest_path)
        if not manifest_command_surfaces_from_manifest(manifest):
            return None
        identity = compute_trust_identity(manifest)
    except (ManifestError, OSError):
        return None
    if ManifestCommandTrustStore().status(identity).is_allowed:
        return None
    return allow_command_text(identity)


def next_action_for_status(status: WorkspaceProjectStatus, status_name: str) -> str:
    if status_name == "missing_required":
        return missing_required_next_action(status)
    if status_name == "missing_optional":
        return "optional repository is missing; clone it only if this role needs it."
    if status_name == "present_without_manifest":
        return f"Add or verify {(status.root / 'base_manifest.yaml').resolve()} before Base setup."
    if status_name == "invalid_manifest":
        return f"Fix {status.manifest_path} before Base setup."
    if status_name in {"needs_verification", "ready"}:
        return (
            "Review the project runtime and configuration, then run the validation command."
            if status_name == "needs_verification" else "Run validation command."
        )
    return "Run setup command, then validation command."


def missing_required_next_action(status: WorkspaceProjectStatus) -> str:
    if status.url is not None:
        return f"Clone {redact_repository_url(status.url)} into {status.root}, then run setup."
    repository = status.repository or status.root.name
    return f"Create or clone repository '{repository}' into {status.root}, then run setup."
