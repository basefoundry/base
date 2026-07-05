from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from base_github_projects import engine as github_engine
from base_projects import engine as projects_engine
from base_projects.command_helpers import ProjectCommandError
from base_projects.command_helpers import ProjectUsageError
from base_projects.command_helpers import PROJECT_COMMAND_TIMEOUT_SECONDS
from base_projects.command_helpers import format_project_command
from base_projects.command_helpers import github_repo_spec
from base_projects.command_helpers import github_repo_spec_from_path
from base_projects.command_helpers import run_project_command


class ProjectCommandHelperTests(unittest.TestCase):
    def test_project_usage_error_is_shared_across_project_commands(self) -> None:
        self.assertIs(projects_engine.ProjectUsageError, ProjectUsageError)
        self.assertIs(github_engine.ProjectUsageError, ProjectUsageError)

    def test_github_repo_spec_from_path_normalizes_owner_repo_paths(self) -> None:
        cases = {
            "basefoundry/base": "basefoundry/base",
            "/basefoundry/base.git": "basefoundry/base",
            " basefoundry/base.git ": "basefoundry/base",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(github_repo_spec_from_path(value), expected)

    def test_github_repo_spec_normalizes_github_urls(self) -> None:
        cases = {
            "https://github.com/basefoundry/base.git": "basefoundry/base",
            "git@github.com:basefoundry/base.git": "basefoundry/base",
            " basefoundry/base.git ": "basefoundry/base",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(github_repo_spec(value, allow_path=True), expected)

    def test_github_repo_spec_rejects_non_github_urls(self) -> None:
        self.assertIsNone(github_repo_spec("https://gitlab.com/basefoundry/base.git"))

    def test_format_project_command_redacts_url_credentials(self) -> None:
        formatted = format_project_command(
            [
                "basectl",
                "repo",
                "clone",
                "https://user:secret@github.com/basefoundry/base.git",
            ]
        )

        self.assertNotIn("secret", formatted)
        self.assertIn("[REDACTED]", formatted)

    def test_run_project_command_captures_text_output(self) -> None:
        completed = subprocess.CompletedProcess(
            ["basectl", "repo", "clone"],
            0,
            stdout="cloned\n",
            stderr="",
        )

        with mock.patch("base_projects.command_helpers.process.run_capture", return_value=completed) as run_capture:
            result = run_project_command(
                ["basectl", "repo", "clone"],
                error_context="basectl repo clone for repository 'base'",
            )

        run_capture.assert_called_once_with(
            ["basectl", "repo", "clone"],
            timeout_seconds=PROJECT_COMMAND_TIMEOUT_SECONDS,
        )
        self.assertEqual(result.stdout, "cloned\n")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0)

    def test_run_project_command_uses_shared_capture_helper(self) -> None:
        completed = subprocess.CompletedProcess(
            ["basectl", "repo", "clone"],
            0,
            stdout="cloned\n",
            stderr="",
        )

        with mock.patch("base_projects.command_helpers.process.run_capture", return_value=completed) as run_capture:
            run_project_command(
                ["basectl", "repo", "clone"],
                error_context="basectl repo clone for repository 'base'",
            )

        run_capture.assert_called_once_with(
            ["basectl", "repo", "clone"],
            timeout_seconds=PROJECT_COMMAND_TIMEOUT_SECONDS,
        )

    def test_run_project_command_reports_os_error_with_redacted_command(self) -> None:
        command = [
            "basectl",
            "repo",
            "clone",
            "https://user:secret@github.com/basefoundry/base.git",
        ]

        with mock.patch("base_projects.command_helpers.subprocess.run", side_effect=OSError("missing basectl")):
            with self.assertRaises(ProjectCommandError) as exc:
                run_project_command(command, error_context="basectl repo clone")

        message = str(exc.exception)
        self.assertIn("Could not run basectl repo clone", message)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn("secret", message)

    def test_run_project_command_reports_timeout_with_redacted_command(self) -> None:
        command = [
            "basectl",
            "repo",
            "clone",
            "https://user:secret@github.com/basefoundry/base.git",
        ]

        with mock.patch(
            "base_projects.command_helpers.subprocess.run",
            side_effect=subprocess.TimeoutExpired(command, timeout=PROJECT_COMMAND_TIMEOUT_SECONDS),
        ):
            with self.assertRaises(ProjectCommandError) as exc:
                run_project_command(command, error_context="basectl repo clone")

        message = str(exc.exception)
        self.assertIn("Timed out running basectl repo clone", message)
        self.assertIn(str(PROJECT_COMMAND_TIMEOUT_SECONDS), message)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn("secret", message)
