from __future__ import annotations

from pathlib import Path

from base_projects.workspace_checks import WorkspaceProjectCheckResult  # pylint: disable=unused-import
from base_projects.workspace_checks import attach_check_result_repo_metadata  # pylint: disable=unused-import
from base_projects.workspace_checks import invalid_manifest_check  # pylint: disable=unused-import
from base_projects.workspace_checks import project_venv_check  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_error_count  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_expected_repo_check_result  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_extra_project_check  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_extra_project_check_result  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_manifest_project_check_results  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_non_base_repo_check  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_project_check_result  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_project_check_results  # pylint: disable=unused-import
from base_projects.workspace_checks import workspace_repo_presence_check  # pylint: disable=unused-import
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import read_workspace_manifest
from base_projects.workspace_report_common import ProjectLastCheck  # pylint: disable=unused-import
from base_projects.workspace_report_common import missing_repo_fix  # pylint: disable=unused-import
from base_projects.workspace_report_common import missing_repo_message  # pylint: disable=unused-import
from base_projects.workspace_report_common import most_severe_status  # pylint: disable=unused-import
from base_projects.workspace_report_common import project_last_check  # pylint: disable=unused-import
from base_projects.workspace_report_common import project_venv_dir  # pylint: disable=unused-import
from base_projects.workspace_report_common import project_venv_ready  # pylint: disable=unused-import
from base_projects.workspace_report_common import workspace_repo_check_details  # pylint: disable=unused-import
from base_projects.workspace_report_json import dumps_json  # pylint: disable=unused-import
from base_projects.workspace_report_json import workspace_check_to_json  # pylint: disable=unused-import
from base_projects.workspace_report_json import workspace_doctor_to_json  # pylint: disable=unused-import
from base_projects.workspace_report_json import workspace_status_to_json  # pylint: disable=unused-import
from base_projects.workspace_report_text import print_workspace_check  # pylint: disable=unused-import
from base_projects.workspace_report_text import print_workspace_doctor  # pylint: disable=unused-import
from base_projects.workspace_report_text import print_workspace_status  # pylint: disable=unused-import
from base_projects.workspace_statuses import WorkspaceProjectStatus  # pylint: disable=unused-import
from base_projects.workspace_statuses import attach_status_repo_metadata  # pylint: disable=unused-import
from base_projects.workspace_statuses import workspace_expected_repo_status  # pylint: disable=unused-import
from base_projects.workspace_statuses import workspace_extra_project_status  # pylint: disable=unused-import
from base_projects.workspace_statuses import workspace_manifest_project_statuses  # pylint: disable=unused-import
from base_projects.workspace_statuses import workspace_project_status  # pylint: disable=unused-import
from base_projects.workspace_statuses import workspace_project_statuses  # pylint: disable=unused-import


def resolve_workspace_manifest(workspace_manifest: str | None) -> WorkspaceManifest | None:
    if workspace_manifest is None:
        return None
    return read_workspace_manifest(Path(workspace_manifest))
