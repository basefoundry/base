from __future__ import annotations

from base_projects.workspace_checks import WorkspaceProjectCheckResult
from base_projects.workspace_checks import attach_check_result_repo_metadata
from base_projects.workspace_checks import invalid_manifest_check
from base_projects.workspace_checks import project_venv_check
from base_projects.workspace_checks import workspace_error_count
from base_projects.workspace_checks import workspace_expected_repo_check_result
from base_projects.workspace_checks import workspace_extra_project_check
from base_projects.workspace_checks import workspace_extra_project_check_result
from base_projects.workspace_checks import workspace_manifest_project_check_results
from base_projects.workspace_checks import workspace_non_base_repo_check
from base_projects.workspace_checks import workspace_project_check_result
from base_projects.workspace_checks import workspace_project_check_results
from base_projects.workspace_checks import workspace_repo_presence_check
from base_projects.workspace_agent_brief import RepositoryFileSignal
from base_projects.workspace_agent_brief import RepositoryValidationSignal
from base_projects.workspace_agent_brief import WorkspaceAgentBrief
from base_projects.workspace_agent_brief import WorkspaceAgentBriefRepository
from base_projects.workspace_agent_brief import workspace_agent_brief
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_onboarding import WorkspaceOnboardingRepository
from base_projects.workspace_onboarding import WorkspaceOnboardingSummary
from base_projects.workspace_onboarding import workspace_onboarding_summary
from base_projects.workspace_report_common import ProjectLastCheck
from base_projects.workspace_report_common import missing_repo_fix
from base_projects.workspace_report_common import missing_repo_message
from base_projects.workspace_report_common import most_severe_status
from base_projects.workspace_report_common import project_last_check
from base_projects.workspace_report_common import project_venv_dir
from base_projects.workspace_report_common import project_venv_ready
from base_projects.workspace_report_common import workspace_repo_check_details
from base_projects.workspace_report_json import dumps_json
from base_projects.workspace_report_json import workspace_check_to_json
from base_projects.workspace_report_json import workspace_doctor_to_json
from base_projects.workspace_report_json import workspace_agent_brief_to_json
from base_projects.workspace_report_json import workspace_onboarding_to_json
from base_projects.workspace_report_json import workspace_status_to_json
from base_projects.workspace_report_text import print_workspace_check
from base_projects.workspace_report_text import print_workspace_doctor
from base_projects.workspace_report_text import print_workspace_agent_brief
from base_projects.workspace_report_text import print_workspace_onboarding
from base_projects.workspace_report_text import print_workspace_status
from base_projects.workspace_statuses import WorkspaceProjectStatus
from base_projects.workspace_statuses import attach_status_repo_metadata
from base_projects.workspace_statuses import workspace_expected_repo_status
from base_projects.workspace_statuses import workspace_extra_project_status
from base_projects.workspace_statuses import workspace_manifest_project_statuses
from base_projects.workspace_statuses import workspace_project_status
from base_projects.workspace_statuses import workspace_project_statuses

# Compatibility facade for callers that imported workspace reporting helpers from
# this module before the report, check, status, and context modules were split.
__all__ = (
    "ProjectLastCheck",
    "RepositoryFileSignal",
    "RepositoryValidationSignal",
    "WorkspaceAgentBrief",
    "WorkspaceAgentBriefRepository",
    "WorkspaceManifest",
    "WorkspaceOnboardingRepository",
    "WorkspaceOnboardingSummary",
    "WorkspaceProjectCheckResult",
    "WorkspaceProjectStatus",
    "attach_check_result_repo_metadata",
    "attach_status_repo_metadata",
    "dumps_json",
    "invalid_manifest_check",
    "missing_repo_fix",
    "missing_repo_message",
    "most_severe_status",
    "print_workspace_check",
    "print_workspace_doctor",
    "print_workspace_agent_brief",
    "print_workspace_onboarding",
    "print_workspace_status",
    "project_last_check",
    "project_venv_check",
    "project_venv_dir",
    "project_venv_ready",
    "resolve_workspace_manifest",
    "workspace_check_to_json",
    "workspace_doctor_to_json",
    "workspace_agent_brief",
    "workspace_agent_brief_to_json",
    "workspace_error_count",
    "workspace_expected_repo_check_result",
    "workspace_expected_repo_status",
    "workspace_extra_project_check",
    "workspace_extra_project_check_result",
    "workspace_extra_project_status",
    "workspace_manifest_project_check_results",
    "workspace_manifest_project_statuses",
    "workspace_non_base_repo_check",
    "workspace_onboarding_summary",
    "workspace_onboarding_to_json",
    "workspace_project_check_result",
    "workspace_project_check_results",
    "workspace_project_status",
    "workspace_project_statuses",
    "workspace_repo_check_details",
    "workspace_repo_presence_check",
    "workspace_status_to_json",
)
