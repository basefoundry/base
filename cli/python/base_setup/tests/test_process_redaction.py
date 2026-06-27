from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from base_setup import process
from base_setup.errors import ArtifactError
from base_setup.tests.helpers import fake_context


class ProcessCommandRedactionTests(unittest.TestCase):
    def test_run_command_redacts_sensitive_command_arguments_from_failure(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        stderr = io.StringIO()
        command = [
            sys.executable,
            "-c",
            "import sys; raise SystemExit(9)",
            "--token",
            "super-secret",
            "--api-key=api-secret",
            "https://user:url-secret@example.invalid/pkg.whl",
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(ArtifactError) as exc:
                process.run_command(ctx, command)

        message = str(exc.exception)
        self.assertNotIn("super-secret", message)
        self.assertNotIn("api-secret", message)
        self.assertNotIn("url-secret", message)
        self.assertIn("[REDACTED]", message)

    def test_run_command_redacts_sensitive_command_arguments_from_success_logs(self) -> None:
        ctx = fake_context()
        command = [
            sys.executable,
            "-c",
            "import sys; assert sys.argv[1:]",
            "--token",
            "super-secret",
            "--api-key=api-secret",
            "https://user:url-secret@example.invalid/pkg.whl",
        ]

        process.run_command(ctx, command)

        debug_text = "\n".join(str(call.args) for call in ctx.log.debug.call_args_list)
        self.assertNotIn("super-secret", debug_text)
        self.assertNotIn("api-secret", debug_text)
        self.assertNotIn("url-secret", debug_text)
        self.assertIn("[REDACTED]", debug_text)

    def test_dry_run_command_redacts_sensitive_command_arguments(self) -> None:
        ctx = fake_context()
        command = [
            "pip",
            "install",
            "--token",
            "super-secret",
            "--api-key=api-secret",
            "https://user:url-secret@example.invalid/pkg.whl",
        ]

        process.dry_run_command(ctx, command)

        info_text = "\n".join(str(call.args) for call in ctx.log.info.call_args_list)
        self.assertNotIn("super-secret", info_text)
        self.assertNotIn("api-secret", info_text)
        self.assertNotIn("url-secret", info_text)
        self.assertIn("[REDACTED]", info_text)
