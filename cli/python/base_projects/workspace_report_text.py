from __future__ import annotations

from pathlib import Path
from typing import Any

from base_projects.workspace_agent_brief import WorkspaceAgentBrief
from base_projects.workspace_agent_brief import WorkspaceAgentBriefRepository
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_onboarding import WorkspaceOnboardingRepository
from base_projects.workspace_onboarding import WorkspaceOnboardingSummary
from base_setup.checks import doctor_status
from base_setup.checks import print_doctor_finding


def last_check_display(last_check: Any) -> str:
    if last_check is None:
        return "-"
    if len(last_check.checked_at) >= 10:
        return last_check.checked_at[:10]
    return last_check.checked_at


def print_workspace_status(
    workspace_root: Path,
    statuses: tuple[Any, ...],
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

    print(f"{'PROJECT':<20} {'STATUS':<6} {'VENV':<14} {'MANIFEST':<8} {'LAST CHECK':<10} PATH")
    for status in statuses:
        print(
            f"{status.name:<20} "
            f"{status.status:<6} "
            f"{status.venv:<14} "
            f"{status.manifest:<8} "
            f"{last_check_display(status.last_check):<10} "
            f"{status.root}"
        )

    attention_count = sum(1 for status in statuses if status.status != "ok")
    if attention_count:
        print(f"\n{attention_count} project(s) need attention. Run 'basectl doctor <project>' for details.")
    else:
        print("\nAll discovered projects look ok.")


def print_manifest_workspace_status(
    workspace_root: Path,
    statuses: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest,
) -> None:
    print(f"Workspace: {workspace_root} ({len(statuses)} repositories)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print()
    if not statuses:
        print("No repositories reported by the workspace manifest.")
        return

    print(
        f"{'REPOSITORY':<20} {'STATUS':<6} {'REQUIRED':<8} {'REPO':<8} "
        f"{'VENV':<14} {'MANIFEST':<8} {'LAST CHECK':<10} PATH"
    )
    for status in statuses:
        print(
            f"{status.repository or status.root.name:<20} "
            f"{status.status:<6} "
            f"{yes_no(status.required):<8} "
            f"{status.repo:<8} "
            f"{status.venv:<14} "
            f"{status.manifest:<8} "
            f"{last_check_display(status.last_check):<10} "
            f"{status.root}"
        )

    attention_count = sum(1 for status in statuses if status.status != "ok")
    if attention_count:
        print(f"\n{attention_count} repositories need attention. Run 'basectl workspace doctor' for details.")
    else:
        print("\nAll workspace repositories look ok.")


def print_workspace_check(
    workspace_root: Path,
    results: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> None:
    item_name = "repositories" if workspace_manifest is not None else "projects"
    print(f"Workspace check: {workspace_root} ({len(results)} {item_name})")
    if workspace_manifest is not None:
        print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print_workspace_check_results(results, workspace_manifest)


def print_workspace_onboarding(summary: WorkspaceOnboardingSummary) -> None:
    print(f"Workspace onboarding: {summary.workspace_root} ({summary.workspace_manifest.name})")
    print(f"Workspace manifest: {summary.workspace_manifest.path}")
    print()
    if not summary.repositories:
        print("No repositories reported by the workspace manifest.")
        return

    print(f"{'REPOSITORY':<20} {'REQUIRED':<8} {'STATUS':<24} PATH")
    for repository in summary.repositories:
        print(
            f"{repository.repository:<20} "
            f"{yes_no(repository.required):<8} "
            f"{repository.status:<24} "
            f"{repository.path}"
        )

    print("\nNext actions:")
    for repository in summary.repositories:
        print_workspace_onboarding_action(repository)


def print_workspace_onboarding_action(repository: WorkspaceOnboardingRepository) -> None:
    print(f"- {repository.repository}: {repository.next_action}")
    if repository.clone_command is not None:
        print(f"  clone: {repository.clone_command}")
    if repository.setup_command is not None:
        print(f"  setup: {repository.setup_command}")
    if repository.validation_command is not None:
        print(f"  validate: {repository.validation_command}")
    if repository.test_command is not None:
        print(f"  test: {repository.test_command}")


def print_workspace_agent_brief(brief: WorkspaceAgentBrief) -> None:
    print(f"Workspace agent brief: {brief.workspace_root} ({brief.workspace_manifest.name})")
    print(f"Workspace manifest: {brief.workspace_manifest.path}")
    print()
    if not brief.repositories:
        print("No repositories reported by the workspace manifest or discovered locally.")
        return

    print(
        f"{'REPOSITORY':<20} {'SCOPE':<12} {'HANDOFF':<22} {'BASELINE':<11} "
        f"{'GUIDANCE':<11} {'VENV':<18} {'VALIDATION':<11} CONTEXT"
    )
    for repository in brief.repositories:
        print(
            f"{repository.repository:<20} "
            f"{repository.scope:<12} "
            f"{repository.handoff_status:<22} "
            f"{repository.baseline.status:<11} "
            f"{repository.agent_guidance.status:<11} "
            f"{repository.venv:<18} "
            f"{repository.validation.status:<11} "
            f"{repository.ai_context_status}"
        )

    required_repositories = tuple(
        repository for repository in brief.repositories if repository.expected and repository.required
    )
    ready_count = sum(1 for repository in required_repositories if repository.handoff_status == "ready")
    print(f"\nReady for agent handoff: {ready_count} of {len(required_repositories)} required repositories.")
    print(
        "Readiness is structural and based on non-executing local file and manifest evidence; "
        ".ai-context is reported but is not required."
    )
    print("\nNext actions:")
    for repository in brief.repositories:
        print_workspace_agent_brief_actions(repository)


def print_workspace_agent_brief_actions(repository: WorkspaceAgentBriefRepository) -> None:
    print(f"- {repository.repository} [{repository.handoff_status}]")
    if repository.baseline.missing_files:
        print(f"  missing baseline: {', '.join(repository.baseline.missing_files)}")
    if repository.baseline.not_executable_files:
        print(f"  not executable: {', '.join(repository.baseline.not_executable_files)}")
    if repository.agent_guidance.missing_files:
        print(f"  missing guidance: {', '.join(repository.agent_guidance.missing_files)}")
    if not repository.next_actions:
        if repository.handoff_status == "unmanaged":
            print("  no Base adoption action recommended")
        else:
            print("  no action required")
        return
    for action in repository.next_actions:
        print(f"  {action}")


def print_workspace_doctor(
    workspace_root: Path,
    results: tuple[Any, ...],
    workspace_manifest: WorkspaceManifest | None = None,
) -> None:
    item_name = "repositories" if workspace_manifest is not None else "projects"
    print(f"\nWorkspace doctor: {workspace_root} ({len(results)} {item_name})")
    if workspace_manifest is not None:
        print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print_workspace_check_results(results, workspace_manifest)


def print_workspace_check_results(
    results: tuple[Any, ...],
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


def workspace_error_count(results: tuple[Any, ...]) -> int:
    return sum(1 for result in results for check in result.checks if doctor_status(check) == "error")


def yes_no(value: bool) -> str:
    return "yes" if value else "no"
