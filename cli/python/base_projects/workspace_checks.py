from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path

import base_cli
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_report_common import missing_repo_fix
from base_projects.workspace_report_common import missing_repo_message
from base_projects.workspace_report_common import project_venv_dir
from base_projects.workspace_report_common import project_venv_ready
from base_projects.workspace_report_common import workspace_repo_check_details
from base_projects.workspace_scanner import ManifestEntry
from base_projects.workspace_scanner import workspace_manifest_entries
from base_setup.checks import ArtifactCheck
from base_setup.checks import checks_status
from base_setup.checks import doctor_status
from base_setup.engine import manifest_checks
from base_setup.engine import pre_venv_manifest_checks
from base_setup.engine import read_default_manifest
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import BaseManifest
from base_setup.uv import manifest_uses_uv_project_manager


@dataclass(frozen=True)
class WorkspaceProjectCheckResult:
    name: str
    root: Path
    manifest_path: Path | None
    manifest: str
    status: str
    checks: tuple[ArtifactCheck, ...]
    expected: bool = False
    required: bool = False
    repo: str = "present"
    repository: str | None = None
    url: str | None = None
    default_branch: str | None = None


def workspace_project_check_results(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest | None = None,
) -> tuple[WorkspaceProjectCheckResult, ...]:
    default_manifest = read_default_manifest(ctx)
    if workspace_manifest is None:
        return tuple(
            workspace_project_check_result(entry, default_manifest)
            for entry in workspace_manifest_entries(workspace_root)
        )
    return workspace_manifest_project_check_results(workspace_root, workspace_manifest, default_manifest)


def workspace_manifest_project_check_results(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    default_manifest: BaseManifest,
) -> tuple[WorkspaceProjectCheckResult, ...]:
    entries_by_repo = {
        entry.path.parent.resolve().name: entry
        for entry in workspace_manifest_entries(workspace_root)
    }
    results: list[WorkspaceProjectCheckResult] = []

    for repo in workspace_manifest.repos:
        entry = entries_by_repo.pop(repo.name, None)
        results.append(workspace_expected_repo_check_result(workspace_root, repo, entry, default_manifest))

    for repo_name in sorted(entries_by_repo):
        results.append(workspace_extra_project_check_result(entries_by_repo[repo_name], default_manifest))

    return tuple(results)


def workspace_expected_repo_check_result(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
    entry: ManifestEntry | None,
    default_manifest: BaseManifest,
) -> WorkspaceProjectCheckResult:
    root = (workspace_root / repo.name).resolve()
    if entry is not None:
        result = workspace_project_check_result(entry, default_manifest)
        checks = (workspace_repo_presence_check(repo, root, present=True),) + result.checks
        return attach_check_result_repo_metadata(
            result,
            repo,
            checks=checks,
            status=checks_status(checks),
        )
    if root.exists():
        checks = (workspace_non_base_repo_check(repo, root),)
        return WorkspaceProjectCheckResult(
            name=repo.name,
            root=root,
            manifest_path=None,
            manifest="missing",
            status=checks_status(checks),
            checks=checks,
            expected=True,
            required=repo.required,
            repo="present",
            repository=repo.name,
            url=repo.url,
            default_branch=repo.default_branch,
        )

    checks = (workspace_repo_presence_check(repo, root, present=False),)
    return WorkspaceProjectCheckResult(
        name=repo.name,
        root=root,
        manifest_path=None,
        manifest="unknown",
        status=checks_status(checks),
        checks=checks,
        expected=True,
        required=repo.required,
        repo="missing",
        repository=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
    )


def attach_check_result_repo_metadata(
    result: WorkspaceProjectCheckResult,
    repo: WorkspaceManifestRepo,
    checks: tuple[ArtifactCheck, ...],
    status: str,
) -> WorkspaceProjectCheckResult:
    return replace(
        result,
        status=status,
        checks=checks,
        expected=True,
        required=repo.required,
        repo="present",
        repository=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
    )


def workspace_extra_project_check_result(
    entry: ManifestEntry,
    default_manifest: BaseManifest,
) -> WorkspaceProjectCheckResult:
    result = workspace_project_check_result(entry, default_manifest)
    checks = (workspace_extra_project_check(result),) + result.checks
    return replace(
        result,
        status=checks_status(checks),
        checks=checks,
        expected=False,
        required=False,
        repo="present",
        repository=entry.path.parent.resolve().name,
    )


def workspace_project_check_result(
    entry: ManifestEntry,
    default_manifest: BaseManifest,
) -> WorkspaceProjectCheckResult:
    root = entry.path.parent.resolve()
    manifest_path = entry.path.resolve()
    try:
        manifest = read_manifest(entry.path)
    except ManifestError as exc:
        checks = (invalid_manifest_check(str(exc)),)
        return WorkspaceProjectCheckResult(
            name=root.name,
            root=root,
            manifest_path=manifest_path,
            manifest="invalid",
            status="error",
            checks=checks,
        )

    if manifest_uses_uv_project_manager(manifest):
        checks = manifest_checks(default_manifest, manifest)
    else:
        venv_check = project_venv_check(manifest)
        if venv_check.ok:
            checks = (venv_check,) + manifest_checks(default_manifest, manifest)
        else:
            checks = pre_venv_manifest_checks(manifest) + (venv_check,)

    return WorkspaceProjectCheckResult(
        name=manifest.project_name,
        root=root,
        manifest_path=manifest_path,
        manifest="valid",
        status=checks_status(checks),
        checks=checks,
    )


def invalid_manifest_check(message: str) -> ArtifactCheck:
    return ArtifactCheck(
        name="project_manifest",
        ok=False,
        message=message,
        fix="Fix base_manifest.yaml syntax and schema.",
        status="error",
        finding_id="BASE-P002",
    )


def workspace_repo_presence_check(repo: WorkspaceManifestRepo, root: Path, present: bool) -> ArtifactCheck:
    if present:
        return ArtifactCheck(
            name="workspace_repository_presence",
            ok=True,
            message=f"Repository '{repo.name}' is present at '{root}'.",
            fix="",
            finding_id="BASE-W010",
            details=workspace_repo_check_details(repo, root, present=True),
        )

    status = "error" if repo.required else "warn"
    return ArtifactCheck(
        name="workspace_repository_presence",
        ok=False,
        message=missing_repo_message(repo, root),
        fix=missing_repo_fix(repo, root),
        status=status,
        finding_id="BASE-W010",
        details=workspace_repo_check_details(repo, root, present=False),
    )


def workspace_extra_project_check(result: WorkspaceProjectCheckResult) -> ArtifactCheck:
    repository = result.repository or result.root.name
    return ArtifactCheck(
        name="workspace_manifest_membership",
        ok=False,
        message=f"Discovered Base-managed project '{repository}' is not listed in the workspace manifest.",
        fix=f"Add '{repository}' to the workspace manifest if it belongs in this workspace.",
        status="warn",
        finding_id="BASE-W011",
        details={
            "repository": repository,
            "path": str(result.root),
            "expected": False,
            "present": True,
        },
    )


def workspace_non_base_repo_check(repo: WorkspaceManifestRepo, root: Path) -> ArtifactCheck:
    return ArtifactCheck(
        name="workspace_project_manifest",
        ok=True,
        message=(
            f"Repository '{repo.name}' is present at '{root}' but does not contain base_manifest.yaml; "
            "project diagnostics skipped."
        ),
        fix="",
        finding_id="BASE-W012",
        details=workspace_repo_check_details(repo, root, present=True),
    )


def project_venv_check(manifest: BaseManifest) -> ArtifactCheck:
    venv_dir = project_venv_dir(manifest)
    if project_venv_ready(venv_dir):
        return ArtifactCheck(
            name="project_virtualenv",
            ok=True,
            message=f"Project virtual environment is ready at '{venv_dir}'.",
            fix="",
            finding_id="BASE-P050",
        )

    return ArtifactCheck(
        name="project_virtualenv",
        ok=False,
        message=f"Project virtual environment is missing or incomplete at '{venv_dir}'.",
        fix=f"Run 'basectl setup {manifest.project_name} --recreate-venv' to recreate the project virtual environment.",
        status="error",
        finding_id="BASE-P050",
    )


def workspace_error_count(results: tuple[WorkspaceProjectCheckResult, ...]) -> int:
    return sum(1 for result in results for check in result.checks if doctor_status(check) == "error")
