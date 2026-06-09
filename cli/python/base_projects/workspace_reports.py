from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

import base_cli
from base_cli.paths import base_state_root
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_manifest import read_workspace_manifest
from base_setup.checks import ArtifactCheck
from base_setup.checks import DIAGNOSTIC_JSON_SCHEMA_VERSION
from base_setup.checks import check_to_doctor_json
from base_setup.checks import check_to_json
from base_setup.checks import checks_status
from base_setup.checks import doctor_status
from base_setup.checks import print_doctor_finding
from base_setup.engine import manifest_checks
from base_setup.engine import pre_venv_manifest_checks
from base_setup.engine import read_default_manifest
from base_setup.manifest import BaseManifest, ManifestError, read_manifest


class ProjectDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManifestEntry:
    path: Path
    mtime_ns: int
    size: int


@dataclass(frozen=True)
class WorkspaceProjectStatus:
    name: str
    root: Path
    manifest_path: Path | None
    status: str
    venv: str
    manifest: str
    issues: tuple[str, ...]
    expected: bool = False
    required: bool = False
    repo: str = "present"
    repository: str | None = None
    url: str | None = None
    default_branch: str | None = None


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
    if root.exists():
        return WorkspaceProjectStatus(
            name=repo.name,
            root=root,
            manifest_path=None,
            status="ok",
            venv="not_applicable",
            manifest="missing",
            issues=(),
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
        )

    venv_dir = project_venv_dir(manifest.project_name)
    if project_venv_ready(venv_dir):
        return WorkspaceProjectStatus(
            name=manifest.project_name,
            root=root,
            manifest_path=entry.path.resolve(),
            status="ok",
            venv="ready",
            manifest="valid",
            issues=(),
        )

    return WorkspaceProjectStatus(
        name=manifest.project_name,
        root=root,
        manifest_path=entry.path.resolve(),
        status="warn",
        venv="missing",
        manifest="valid",
        issues=(f"project virtual environment missing at {venv_dir}",),
    )


def project_venv_dir(project_name: str) -> Path:
    return base_state_root() / project_name / ".venv"


def project_venv_ready(venv_dir: Path) -> bool:
    return (venv_dir / "bin" / "python").is_file()


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

    venv_check = project_venv_check(manifest.project_name)
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


def project_venv_check(project_name: str) -> ArtifactCheck:
    venv_dir = project_venv_dir(project_name)
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
        fix=f"Run 'basectl setup {project_name} --recreate-venv' to recreate the project virtual environment.",
        status="error",
        finding_id="BASE-P050",
    )


def workspace_error_count(results: tuple[WorkspaceProjectCheckResult, ...]) -> int:
    return sum(1 for result in results for check in result.checks if doctor_status(check) == "error")


def workspace_status_to_json(
    workspace_root: Path,
    statuses: tuple[WorkspaceProjectStatus, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workspace": str(workspace_root),
        "project_count": workspace_project_count(statuses, workspace_manifest),
        "projects": [workspace_status_item_to_json(status, workspace_manifest) for status in statuses],
    }
    add_workspace_manifest_json(payload, statuses, workspace_manifest)
    return payload


def workspace_status_item_to_json(
    status: WorkspaceProjectStatus,
    workspace_manifest: WorkspaceManifest | None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": status.name,
        "status": status.status,
        "path": str(status.root),
        "manifest_path": str(status.manifest_path) if status.manifest_path is not None else None,
        "venv": status.venv,
        "manifest": status.manifest,
        "issues": list(status.issues),
    }
    if workspace_manifest is not None:
        item.update(workspace_manifest_item_metadata(status))
    return item


def workspace_check_to_json(
    workspace_root: Path,
    results: tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    return workspace_checks_to_json(workspace_root, results, doctor=False, workspace_manifest=workspace_manifest)


def workspace_doctor_to_json(
    workspace_root: Path,
    results: tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    return workspace_checks_to_json(workspace_root, results, doctor=True, workspace_manifest=workspace_manifest)


def workspace_checks_to_json(
    workspace_root: Path,
    results: tuple[WorkspaceProjectCheckResult, ...],
    doctor: bool,
    workspace_manifest: WorkspaceManifest | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
        "workspace": str(workspace_root),
        "status": checks_status(tuple(check for result in results for check in result.checks)),
        "project_count": workspace_project_count(results, workspace_manifest),
        "projects": [workspace_check_result_to_json(result, doctor, workspace_manifest) for result in results],
    }
    add_workspace_manifest_json(payload, results, workspace_manifest)
    return payload


def workspace_check_result_to_json(
    result: WorkspaceProjectCheckResult,
    doctor: bool,
    workspace_manifest: WorkspaceManifest | None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": result.name,
        "status": result.status,
        "path": str(result.root),
        "manifest_path": str(result.manifest_path) if result.manifest_path is not None else None,
        "manifest": result.manifest,
        "checks": [workspace_check_item_to_json(check, doctor) for check in result.checks],
    }
    if workspace_manifest is not None:
        item.update(workspace_manifest_item_metadata(result))
    return item


def workspace_manifest_item_metadata(
    item: WorkspaceProjectStatus | WorkspaceProjectCheckResult,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "repository": item.repository or item.root.name,
        "expected": item.expected,
        "required": item.required,
        "repo": item.repo,
    }
    if item.url is not None:
        metadata["url"] = item.url
    if item.default_branch is not None:
        metadata["default_branch"] = item.default_branch
    return metadata


def workspace_project_count(
    items: tuple[WorkspaceProjectStatus, ...] | tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None,
) -> int:
    if workspace_manifest is None:
        return len(items)
    return sum(1 for item in items if item.manifest in ("valid", "invalid"))


def add_workspace_manifest_json(
    payload: dict[str, Any],
    items: tuple[WorkspaceProjectStatus, ...] | tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None,
) -> None:
    if workspace_manifest is None:
        return
    payload["workspace_manifest"] = {
        "path": str(workspace_manifest.path),
        "name": workspace_manifest.name,
        "schema_version": workspace_manifest.schema_version,
    }
    payload["repository_count"] = len(items)


def workspace_check_item_to_json(check: ArtifactCheck, doctor: bool) -> dict[str, Any]:
    if doctor:
        return check_to_doctor_json(check)
    return check_to_json(check)


def print_workspace_status(
    workspace_root: Path,
    statuses: tuple[WorkspaceProjectStatus, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> None:
    if workspace_manifest is not None:
        print_manifest_workspace_status(workspace_root, statuses, workspace_manifest)
        return

    print(f"Workspace: {workspace_root} ({len(statuses)} projects)")
    print()
    if not statuses:
        print("No Base-managed projects discovered.")
        return

    print(f"{'PROJECT':<20} {'STATUS':<6} {'VENV':<8} {'MANIFEST':<8} {'LAST CHECK':<10} PATH")
    for status in statuses:
        print(
            f"{status.name:<20} "
            f"{status.status:<6} "
            f"{status.venv:<8} "
            f"{status.manifest:<8} "
            f"{'-':<10} "
            f"{status.root}"
        )

    attention_count = sum(1 for status in statuses if status.status != "ok")
    if attention_count:
        print(f"\n{attention_count} project(s) need attention. Run 'basectl doctor <project>' for details.")
    else:
        print("\nAll discovered projects look ok.")


def print_manifest_workspace_status(
    workspace_root: Path,
    statuses: tuple[WorkspaceProjectStatus, ...],
    workspace_manifest: WorkspaceManifest,
) -> None:
    print(f"Workspace: {workspace_root} ({len(statuses)} repositories)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print()
    if not statuses:
        print("No repositories reported by the workspace manifest.")
        return

    print(f"{'REPOSITORY':<20} {'STATUS':<6} {'REQUIRED':<8} {'REPO':<8} {'VENV':<14} {'MANIFEST':<8} PATH")
    for status in statuses:
        print(
            f"{status.repository or status.root.name:<20} "
            f"{status.status:<6} "
            f"{yes_no(status.required):<8} "
            f"{status.repo:<8} "
            f"{status.venv:<14} "
            f"{status.manifest:<8} "
            f"{status.root}"
        )

    attention_count = sum(1 for status in statuses if status.status != "ok")
    if attention_count:
        print(f"\n{attention_count} repositories need attention. Run 'basectl workspace doctor' for details.")
    else:
        print("\nAll workspace repositories look ok.")


def print_workspace_check(
    workspace_root: Path,
    results: tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> None:
    item_name = "repositories" if workspace_manifest is not None else "projects"
    print(f"Workspace check: {workspace_root} ({len(results)} {item_name})")
    if workspace_manifest is not None:
        print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print_workspace_check_results(results, workspace_manifest)


def print_workspace_doctor(
    workspace_root: Path,
    results: tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> None:
    item_name = "repositories" if workspace_manifest is not None else "projects"
    print(f"\nWorkspace doctor: {workspace_root} ({len(results)} {item_name})")
    if workspace_manifest is not None:
        print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print_workspace_check_results(results, workspace_manifest)


def print_workspace_check_results(
    results: tuple[WorkspaceProjectCheckResult, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> None:
    if not results:
        if workspace_manifest is None:
            print("\nNo Base-managed projects discovered.")
        else:
            print("\nNo repositories reported by the workspace manifest.")
        return

    label = "Repository" if workspace_manifest is not None else "Project"
    for result in results:
        name = result.repository or result.name
        print(f"\n{label}: {name} [{result.status}]")
        print(f"Path: {result.root}")
        for check in result.checks:
            print_doctor_finding(doctor_status(check), check.finding_id, check.name, check.message, check.fix)

    error_count = workspace_error_count(results)
    if error_count:
        print(f"\nWorkspace has {error_count} error finding(s).")
        return

    warn_count = sum(1 for result in results for check in result.checks if doctor_status(check) == "warn")
    if warn_count:
        print(f"\nWorkspace has {warn_count} warning finding(s).")
    elif workspace_manifest is not None:
        print("\nAll workspace repositories passed.")
    else:
        print("\nAll discovered projects passed.")


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def workspace_manifest_entries(workspace_root: Path) -> tuple[ManifestEntry, ...]:
    if not workspace_root.is_dir():
        raise ProjectDiscoveryError(f"Workspace '{workspace_root}' is not a directory.")

    entries: list[ManifestEntry] = []
    for candidate in sorted(workspace_root.iterdir(), key=lambda path: path.name):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "base_manifest.yaml"
        if not manifest_path.is_file():
            continue
        stat_result = manifest_path.stat()
        entries.append(
            ManifestEntry(
                path=manifest_path,
                mtime_ns=stat_result.st_mtime_ns,
                size=stat_result.st_size,
            )
        )

    return tuple(entries)


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"))
