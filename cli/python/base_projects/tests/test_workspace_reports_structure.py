from __future__ import annotations

from pathlib import Path
import unittest

from base_projects import workspace_checks
from base_projects import engine
from base_projects import workspace_reports
from base_projects import workspace_statuses


class WorkspaceReportStructureTests(unittest.TestCase):
    def test_workspace_report_computation_lives_in_focused_modules(self) -> None:
        reports_source = Path(workspace_reports.__file__).read_text(encoding="utf-8")
        statuses_source = Path(workspace_statuses.__file__).read_text(encoding="utf-8")
        checks_source = Path(workspace_checks.__file__).read_text(encoding="utf-8")

        self.assertIn("def workspace_project_statuses", statuses_source)
        self.assertIn("def workspace_project_check_results", checks_source)
        self.assertNotIn("def workspace_project_statuses", reports_source)
        self.assertNotIn("def workspace_project_check_results", reports_source)
        self.assertNotIn("subprocess.run", reports_source)

    def test_workspace_reports_declares_compatibility_exports(self) -> None:
        self.assertIn("resolve_workspace_manifest", workspace_reports.__all__)
        self.assertIn("workspace_project_statuses", workspace_reports.__all__)
        self.assertIn("workspace_project_check_results", workspace_reports.__all__)
        self.assertIn("print_workspace_doctor", workspace_reports.__all__)

    def test_projects_engine_uses_focused_report_modules(self) -> None:
        engine_source = Path(engine.__file__).read_text(encoding="utf-8")

        self.assertNotIn("workspace_reports import", engine_source)
        self.assertIn("workspace_report_json import workspace_status_to_json", engine_source)
        self.assertIn("workspace_report_text import print_workspace_doctor", engine_source)
        self.assertIn("workspace_checks import workspace_project_check_results", engine_source)
        self.assertIn("workspace_statuses import workspace_project_statuses", engine_source)
