from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

import base_cli
from base_cli.paths import base_state_root
from base_projects.workspace_scanner import ManifestEntry
from base_projects.workspace_scanner import workspace_manifest_entries
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_manifest import read_workspace_manifest
from base_projects.workspace_report_json import dumps_json  # pylint: disable=unused-import
from base_projects.workspace_report_json import workspace_check_to_json  # pylint: disable=unused-import
from base_projects.workspace_report_json import workspace_doctor_to_json  # pylint: disable=unused-import
from base_projects.workspace_report_json import workspace_status_to_json  # pylint: disable=unused-import
from base_projects.workspace_report_text import print_workspace_check  # pylint: disable=unused-import
from base_projects.workspace_report_text import print_workspace_doctor  # pylint: disable=unused-import
from base_projects.workspace_report_text import print_workspace_status  # pylint: disable=unused-import
from base_setup.checks import ArtifactCheck
from base_setup.checks import checks_status
from base_setup.checks import doctor_status
from base_setup.engine import manifest_checks
from base_setup.engine import pre_venv_manifest_checks
from base_setup.engine import read_default_manifest
from base_setup.manifest import BaseManifest, ManifestError, read_manifest
from base_setup.python_runtime import ProjectPythonRuntime
from base_setup.python_runtime import project_python_runtime
from base_setup.uv import manifest_uses_uv_project_manager


@dataclass(frozen=True)
class ProjectLastCheck:
    checked_at: str
    status: str


@dataclass(frozen=True)
class WorkspaceProjectStatus:
    name: str
    root: Path
    manifest_path: Path | None
    status: str
    venv: str
    manifest: str
    issues: tuple[str, ...]
    last_check: ProjectLastCheck | None = None
    expected: bool = False
    required: bool = False
    repo: str = "present"
    repository: str | None = None
    url: str | None = None
    default_branch: str | None = None
    python_runtime: ProjectPythonRuntime | None = None


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


def resolve_workspace_manifest(workspace_manifest: str | None) -> WorkspaceManifest | None:
    if workspace_manifest is None:
        return None
    return read_workspace_manifest(Path(workspace_manifest))


def workspace_project_statuses(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest | None = None,
) -> tuple[WorkspaceProjectStatus, ...]:
    if workspace_manifest is None:
        return tuple(workspace_project_status(entry) for entry in workspace_manifest_entries(workspace_root))
    return workspace_manifest_project_statuses(workspace_root, workspace_manifest)


def workspace_manifest_project_statuses(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
) -> tuple[WorkspaceProjectStatus, ...]:
    entries_by_repo = {
        entry.path.parent.resolve().name: entry
        for entry in workspace_manifest_entries(workspace_root)
    }
    statuses: list[WorkspaceProjectStatus] = []

    for repo in workspace_manifest.repos:
        entry = entries_by_repo.pop(repo.name, None)
        statuses.append(workspace_expected_repo_status(workspace_root, repo, entry))

    for repo_name in sorted(entries_by_repo):
        statuses.append(workspace_extra_project_status(entries_by_repo[repo_name]))

    return tuple(statuses)


def workspace_expected_repo_status(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
    entry: ManifestEntry | None,
) -> WorkspaceProjectStatus:
    root = (workspace_root / repo.name).resolve()
    if entry is not None:
        status = workspace_project_status(entry)
        return attach_status_repo_metadata(status, repo)
    last_check = project_last_check(repo.name)
    if root.exists():
        return WorkspaceProjectStatus(
            name=repo.name,
            root=root,
            manifest_path=None,
            status="ok",
            venv="not_applicable",
            manifest="missing",
            issues=(),
            last_check=last_check,
            expected=True,
            required=repo.required,
            repo="present",
            repository=repo.name,
            url=repo.url,
            default_branch=repo.default_branch,
        )

    return WorkspaceProjectStatus(
        name=repo.name,
        root=root,
        manifest_path=None,
        status="error" if repo.required else "warn",
        venv="unknown",
        manifest="unknown",
        issues=(missing_repo_message(repo, root),),
        last_check=last_check,
        expected=True,
        required=repo.required,
        repo="missing",
        repository=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
    )


def attach_status_repo_metadata(
    status: WorkspaceProjectStatus,
    repo: WorkspaceManifestRepo,
) -> WorkspaceProjectStatus:
    return replace(
        status,
        expected=True,
        required=repo.required,
        repo="present",
        repository=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
    )


def workspace_extra_project_status(entry: ManifestEntry) -> WorkspaceProjectStatus:
    status = workspace_project_status(entry)
    return replace(
        status,
        status=most_severe_status(status.status, "warn"),
        issues=status.issues + ("discovered Base-managed project is not listed in the workspace manifest",),
        expected=False,
        required=False,
        repo="present",
        repository=entry.path.parent.resolve().name,
    )


def workspace_project_status(entry: ManifestEntry) -> WorkspaceProjectStatus:
    root = entry.path.parent.resolve()
    try:
        manifest = read_manifest(entry.path)
    except ManifestError as exc:
        return WorkspaceProjectStatus(
            name=root.name,
            root=root,
            manifest_path=entry.path.resolve(),
            status="error",
            venv="unknown",
            manifest="invalid",
            issues=(str(exc),),
            last_check=project_last_check(root.name),
        )

    last_check = project_last_check(manifest.project_name)
    venv_dir = project_venv_dir(manifest)
    if project_venv_ready(venv_dir):
        return WorkspaceProjectStatus(
            name=manifest.project_name,
            root=root,
            manifest_path=entry.path.resolve(),
            status="ok",
            venv="ready",
            manifest="valid",
            issues=(),
            last_check=last_check,
            python_runtime=project_python_runtime(manifest, venv_dir=venv_dir),
        )

    return WorkspaceProjectStatus(
        name=manifest.project_name,
        root=root,
        manifest_path=entry.path.resolve(),
        status="warn",
        venv="missing",
        manifest="valid",
        issues=(f"project virtual environment missing at {venv_dir}",),
        last_check=last_check,
    )


def project_venv_dir(manifest: BaseManifest) -> Path:
    if manifest_uses_uv_project_manager(manifest):
        return manifest.path.parent / ".venv"
    return base_state_root() / manifest.project_name / ".venv"


def project_venv_ready(venv_dir: Path) -> bool:
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.is_file():
        return False
    try:
        completed = subprocess.run(
            [str(python_bin), "-c", "import sys"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def project_last_check(project_name: str) -> ProjectLastCheck | None:
    record_path = base_state_root() / project_name / "checks" / "last.json"
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("schema_version") != 1:
        return None
    if payload.get("project") != project_name:
        return None

    checked_at = payload.get("checked_at")
    status = payload.get("status")
    if not isinstance(checked_at, str) or not isinstance(status, str):
        return None
    return ProjectLastCheck(checked_at=checked_at, status=status)


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


def workspace_repo_check_details(repo: WorkspaceManifestRepo, root: Path, present: bool) -> dict[str, Any]:
    details: dict[str, Any] = {
        "repository": repo.name,
        "path": str(root),
        "required": repo.required,
        "present": present,
    }
    if repo.url is not None:
        details["url"] = repo.url
    if repo.default_branch is not None:
        details["default_branch"] = repo.default_branch
    return details


def missing_repo_message(repo: WorkspaceManifestRepo, root: Path) -> str:
    requirement = "Required" if repo.required else "Optional"
    return f"{requirement} repository '{repo.name}' is missing at '{root}'."


def missing_repo_fix(repo: WorkspaceManifestRepo, root: Path) -> str:
    if repo.url:
        return f"Clone '{repo.url}' into '{root}'."
    return f"Create or clone repository '{repo.name}' into '{root}'."


def most_severe_status(*statuses: str) -> str:
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


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
