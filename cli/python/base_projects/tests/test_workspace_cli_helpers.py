from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_projects import engine
from base_projects.tests.workspace_cli_helpers import invoke_engine


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


class WorkspaceCliInvocationHelperTests(unittest.TestCase):
    def test_invoke_engine_overrides_environment_and_restores_success_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            stdout = TerminalStringIO()
            stderr = io.StringIO()
            keys = ("HOME", "BASE_HOME", "BASE_PROJECT", "BASE_PROJECT_MANIFEST", "HELPER_OVERRIDE")

            with mock.patch.dict(
                os.environ,
                {
                    "HOME": "original-home",
                    "BASE_HOME": "original-base",
                    "BASE_PROJECT": "original-project",
                    "BASE_PROJECT_MANIFEST": "original-manifest",
                    "HELPER_OVERRIDE": "original-value",
                },
            ):
                original_environment = {key: os.environ[key] for key in keys}
                original_stdout = sys.stdout
                original_stderr = sys.stderr

                def fake_main(args: list[str]) -> int:
                    self.assertEqual(args, ["workspace", "check"])
                    self.assertEqual(os.environ["BASE_PROJECT"], "temporary-project")
                    self.assertEqual(os.environ["HELPER_OVERRIDE"], "temporary-value")
                    self.assertIs(sys.stdout, stdout)
                    self.assertIs(sys.stderr, stderr)
                    self.assertTrue(sys.stdout.isatty())
                    print("captured stdout")
                    print("captured stderr", file=sys.stderr)
                    return 17

                with mock.patch.object(engine, "main", side_effect=fake_main):
                    status, out, err = invoke_engine(
                        ["workspace", "check"],
                        root / "base",
                        root / "home",
                        stdout_stream=stdout,
                        stderr_stream=stderr,
                        env_overrides={
                            "BASE_PROJECT": "temporary-project",
                            "HELPER_OVERRIDE": "temporary-value",
                        },
                    )

                self.assertEqual(status, 17)
                self.assertEqual(out, "captured stdout\n")
                self.assertEqual(err, "captured stderr\n")
                self.assertEqual({key: os.environ[key] for key in keys}, original_environment)
                self.assertIs(sys.stdout, original_stdout)
                self.assertIs(sys.stderr, original_stderr)

    def test_invoke_engine_restores_environment_and_streams_after_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            stdout = io.StringIO()
            stderr = io.StringIO()
            keys = ("HOME", "BASE_HOME", "BASE_PROJECT", "BASE_PROJECT_MANIFEST", "HELPER_OVERRIDE")

            with mock.patch.dict(
                os.environ,
                {
                    "HOME": "original-home",
                    "BASE_HOME": "original-base",
                    "BASE_PROJECT": "original-project",
                    "BASE_PROJECT_MANIFEST": "original-manifest",
                    "HELPER_OVERRIDE": "original-value",
                },
            ):
                original_environment = {key: os.environ[key] for key in keys}
                original_stdout = sys.stdout
                original_stderr = sys.stderr

                def failing_main(_args: list[str]) -> int:
                    print("before exception")
                    print("diagnostic", file=sys.stderr)
                    raise RuntimeError("expected engine failure")

                with mock.patch.object(engine, "main", side_effect=failing_main):
                    with self.assertRaisesRegex(RuntimeError, "expected engine failure"):
                        invoke_engine(
                            ["workspace", "check"],
                            root / "base",
                            root / "home",
                            stdout_stream=stdout,
                            stderr_stream=stderr,
                            env_overrides={"HELPER_OVERRIDE": "temporary-value"},
                        )

                self.assertEqual(stdout.getvalue(), "before exception\n")
                self.assertEqual(stderr.getvalue(), "diagnostic\n")
                self.assertEqual({key: os.environ[key] for key in keys}, original_environment)
                self.assertIs(sys.stdout, original_stdout)
                self.assertIs(sys.stderr, original_stderr)
