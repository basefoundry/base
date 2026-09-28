from __future__ import annotations

from dataclasses import fields
from unittest import TestCase
from unittest import mock

import base_cli
from base_projects import project_dispatch
from base_projects.command_helpers import ProjectUsageError


def actions_with_mocks() -> project_dispatch.ProjectCommandActions:
    return project_dispatch.ProjectCommandActions(
        **{field.name: mock.Mock(return_value=17) for field in fields(project_dispatch.ProjectCommandActions)}
    )


class ProjectDispatchTests(TestCase):
    def setUp(self) -> None:
        self.ctx = mock.Mock()
        self.options = project_dispatch.WorkspaceCommandOptions(workspace="/workspace", output_format="json")

    def test_every_registered_command_routes_to_its_action(self) -> None:
        command_arguments = {
            "list": (),
            "current": (),
            "manifest": ("demo",),
            "resolve": ("demo",),
            "status": (),
            "check": (),
            "doctor": (),
            "onboarding": (),
            "agent-brief": (),
            "clone": (),
            "configure": (),
            "setup": (),
            "test": (),
            "init": ("workspace.yaml",),
            "test-command": (),
            "demo-script": (),
            "activation-sources": ("demo",),
            "run-command": ("lint",),
            "run-commands": (),
            "build-targets": ("api",),
            "build-target-list": (),
            "pull": (),
            "update": (),
        }
        handler_actions = {
            "list": "list_projects",
            "current": "current_project",
            "manifest": "manifest_project",
            "resolve": "resolve_project",
            "status": "workspace_status",
            "check": "workspace_check",
            "doctor": "workspace_doctor",
            "onboarding": "workspace_onboarding",
            "agent-brief": "workspace_agent_brief",
            "clone": "workspace_clone",
            "configure": "workspace_configure",
            "setup": "workspace_setup",
            "test": "workspace_test",
            "init": "workspace_init",
            "test-command": "test_command_project",
            "demo-script": "demo_script_project",
            "activation-sources": "activation_sources_project",
            "run-command": "run_command_project",
            "run-commands": "list_run_commands",
            "build-targets": "build_targets",
            "build-target-list": "build_target_list",
            "pull": "workspace_pull",
            "update": "workspace_update",
        }

        for command, arguments in command_arguments.items():
            with self.subTest(command=command):
                actions = actions_with_mocks()
                result = project_dispatch.dispatch_projects_command(
                    self.ctx, (command, *arguments), self.options, actions
                )

                self.assertEqual(result, 17)
                action = getattr(actions, handler_actions[command])
                action.assert_called_once()

    def test_empty_arguments_default_to_list(self) -> None:
        actions = actions_with_mocks()

        result = project_dispatch.dispatch_projects_command(self.ctx, (), self.options, actions)

        self.assertEqual(result, 17)
        actions.list_projects.assert_called_once_with(self.ctx, "/workspace", "json")

    def test_unknown_command_returns_usage_error(self) -> None:
        actions = actions_with_mocks()

        result = project_dispatch.dispatch_projects_command(self.ctx, ("unknown",), self.options, actions)

        self.assertEqual(result, base_cli.ExitCode.USAGE_ERROR)
        self.ctx.log.error.assert_called_once()
        self.assertIn("Unknown projects command '%s'", self.ctx.log.error.call_args.args[0])
        self.assertEqual(self.ctx.log.error.call_args.args[1], "unknown")

    def test_runtime_verification_is_restricted_to_check_and_doctor(self) -> None:
        options = project_dispatch.WorkspaceCommandOptions(
            workspace=None,
            output_format="text",
            verify_project_runtime=True,
        )

        with self.assertRaisesRegex(ProjectUsageError, "only supported for workspace check and doctor"):
            project_dispatch.dispatch_projects_command(self.ctx, ("list",), options, actions_with_mocks())


if __name__ == "__main__":
    import unittest

    unittest.main()
