from __future__ import annotations

from pathlib import Path
import unittest

from base_projects import engine
from base_projects import project_dispatch
from base_projects import workspace_clone_command


class BaseProjectsEngineStructureTests(unittest.TestCase):
    def test_workspace_clone_orchestration_lives_outside_engine(self) -> None:
        engine_source = Path(engine.__file__).read_text(encoding="utf-8")
        clone_source = Path(workspace_clone_command.__file__).read_text(encoding="utf-8")

        self.assertIn("def workspace_clone_command", clone_source)
        self.assertNotIn("def workspace_clone_command", engine_source)
        self.assertNotIn("def clone_workspace_repo", engine_source)
        self.assertIs(engine.workspace_clone_command, workspace_clone_command.workspace_clone_command)

    def test_project_command_dispatch_lives_outside_engine(self) -> None:
        engine_source = Path(engine.__file__).read_text(encoding="utf-8")
        dispatch_source = Path(project_dispatch.__file__).read_text(encoding="utf-8")

        self.assertIn("def dispatch_projects_command", dispatch_source)
        self.assertNotIn("def dispatch_projects_command", engine_source)
        self.assertNotIn("PROJECT_COMMAND_HANDLERS", engine_source)
