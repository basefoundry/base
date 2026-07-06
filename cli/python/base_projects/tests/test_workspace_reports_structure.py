from __future__ import annotations

from pathlib import Path
import unittest

from base_projects import workspace_checks
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
