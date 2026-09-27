from __future__ import annotations

import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup import checks as setup_checks
from base_setup import engine
from base_setup.manifest import BaseManifest
from base_setup.tests.helpers import fake_context


class ProjectCheckTextOutputTests(unittest.TestCase):
    def test_pre_venv_check_and_doctor_json_use_the_same_indented_renderer(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        check = setup_checks.ArtifactCheck(
            name="git-remote",
            ok=True,
            message="Git remote is available.",
            fix="",
            finding_id="BASE-P083",
        )
        expected = json.dumps([setup_checks.check_to_json(check)], indent=2) + "\n"

        with mock.patch("base_setup.engine.pre_venv_manifest_checks", return_value=(check,)):
            check_stdout = io.StringIO()
            with redirect_stdout(check_stdout):
                self.assertEqual(engine.check_pre_venv_manifest(fake_context(), manifest, "json"), 0)

        with mock.patch("base_setup.engine.pre_venv_manifest_checks", return_value=(check,)):
            doctor_stdout = io.StringIO()
            with redirect_stdout(doctor_stdout):
                self.assertEqual(engine.doctor_pre_venv_manifest(manifest, "json"), 0)

        self.assertEqual(check_stdout.getvalue(), expected)
        self.assertEqual(doctor_stdout.getvalue(), expected)

    def test_unsupported_pre_venv_formats_use_context_logging(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        ctx = fake_context()

        self.assertEqual(engine.check_pre_venv_manifest(ctx, manifest, "yaml"), 2)
        self.assertEqual(engine.doctor_pre_venv_manifest(manifest, "yaml", ctx=ctx), 2)
        self.assertEqual(ctx.log.error.call_count, 2)
        self.assertIn("Unsupported check output format 'yaml'", ctx.log.error.call_args_list[0].args[0])
        self.assertIn("Unsupported doctor output format 'yaml'", ctx.log.error.call_args_list[1].args[0])

    def test_check_manifest_publishes_warning_status_without_changing_exit_status(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        warning_check = setup_checks.ArtifactCheck(
            name="optional-artifact",
            ok=False,
            message="Optional project artifact is not installed.",
            fix="Review the optional project artifact.",
            finding_id="BASE-P033",
            status="warn",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            status_path = Path(temp_dir) / "project-check.status"
            with (
                mock.patch.dict(
                    os.environ,
                    {"BASE_SETUP_CHECK_STATUS_FILE": str(status_path)},
                    clear=False,
                ),
                mock.patch(
                    "base_setup.engine.manifest_checks",
                    return_value=(warning_check,),
                ),
            ):
                status = engine.check_manifest(
                    fake_context(),
                    default_manifest,
                    manifest,
                    output_format="text",
                )

            self.assertEqual(status, 0)
            self.assertEqual(status_path.read_text(encoding="utf-8"), "warn\n")

    def test_check_pre_venv_publishes_warning_status_without_changing_exit_status(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        warning_check = setup_checks.ArtifactCheck(
            name="git-remote",
            ok=False,
            message="The Git remote could not be checked.",
            fix="Review the Git remote manually.",
            finding_id="BASE-P083",
            status="warn",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            status_path = Path(temp_dir) / "project-precheck.status"
            with (
                mock.patch.dict(
                    os.environ,
                    {"BASE_SETUP_CHECK_STATUS_FILE": str(status_path)},
                    clear=False,
                ),
                mock.patch(
                    "base_setup.engine.pre_venv_manifest_checks",
                    return_value=(warning_check,),
                ),
            ):
                status = engine.check_pre_venv_manifest(
                    fake_context(),
                    manifest,
                    output_format="text",
                )

            self.assertEqual(status, 0)
            self.assertEqual(status_path.read_text(encoding="utf-8"), "warn\n")

    def test_doctor_finding_uses_shared_visual_status_format_on_tty(self) -> None:
        class TtyBuffer(io.StringIO):
            def isatty(self) -> bool:
                return True

        stdout = TtyBuffer()
        with mock.patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True), redirect_stdout(stdout):
            setup_checks.print_doctor_finding(
                "ok",
                "BASE-P040",
                "demo-artifact",
                "Project artifact check passed.",
            )

        self.assertEqual(
            stdout.getvalue(),
            "\033[0;32m✓ ok\033[0m     BASE-P040  demo-artifact               "
            "Project artifact check passed.\n",
        )

    def test_doctor_finding_aligns_visual_fix_under_finding_id(self) -> None:
        class TtyBuffer(io.StringIO):
            def isatty(self) -> bool:
                return True

        stderr = TtyBuffer()
        with (
            mock.patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True),
            redirect_stderr(stderr),
        ):
            setup_checks.print_doctor_finding(
                "error",
                "BASE-H001",
                "BASE_DEMO_ENV",
                "Environment variable is not set or is empty.",
                "Set BASE_DEMO_ENV in your shell.",
            )

        finding_line, fix_line = stderr.getvalue().splitlines()
        visible_finding_prefix = re.sub(r"\033\[[0-9;]*m", "", finding_line.split("BASE-H001", 1)[0])
        fix_prefix = fix_line.split("Fix:", 1)[0]
        self.assertEqual(len(visible_finding_prefix), len(fix_prefix))
        self.assertTrue(fix_line.endswith("Fix: Set BASE_DEMO_ENV in your shell."))

    def test_doctor_finding_aligns_plain_fix_under_finding_id(self) -> None:
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stderr(stderr):
            setup_checks.print_doctor_finding(
                "error",
                "BASE-H001",
                "BASE_DEMO_ENV",
                "Environment variable is not set or is empty.",
                "Set BASE_DEMO_ENV in your shell.",
            )

        finding_line, fix_line = stderr.getvalue().splitlines()
        self.assertEqual(
            len(finding_line.split("BASE-H001", 1)[0]),
            len(fix_line.split("Fix:", 1)[0]),
        )

    def test_check_manifest_text_routes_findings_by_status_and_preserves_exit_status(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        error_check = setup_checks.ArtifactCheck(
            name="required-artifact",
            ok=False,
            message="Required project artifact is not installed.",
            fix="basectl setup demo",
            finding_id="BASE-P040",
            status="error",
        )
        warning_check = setup_checks.ArtifactCheck(
            name="optional-artifact",
            ok=False,
            message="Optional project artifact is not installed.",
            fix="Review the optional project artifact.",
            finding_id="BASE-P033",
            status="warn",
        )

        ctx = fake_context()
        with mock.patch("base_setup.engine.manifest_checks", return_value=(error_check, warning_check)):
            status = engine.check_manifest(ctx, default_manifest, manifest, output_format="text")

        self.assertEqual(status, 1)
        self.assertEqual(
            ctx.log.error.call_args_list,
            [
                mock.call(error_check.message),
                mock.call("Fix: %s", error_check.fix),
            ],
        )
        self.assertEqual(
            ctx.log.warning.call_args_list,
            [
                mock.call(warning_check.message),
                mock.call("Fix: %s", warning_check.fix),
            ],
        )

        warning_ctx = fake_context()
        with mock.patch("base_setup.engine.manifest_checks", return_value=(warning_check,)):
            warning_status = engine.check_manifest(
                warning_ctx,
                default_manifest,
                manifest,
                output_format="text",
            )

        self.assertEqual(warning_status, 0)
        warning_ctx.log.error.assert_not_called()
        self.assertEqual(
            warning_ctx.log.warning.call_args_list,
            [
                mock.call(warning_check.message),
                mock.call("Fix: %s", warning_check.fix),
            ],
        )

    def test_check_pre_venv_text_routes_findings_by_status_and_preserves_exit_status(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        error_check = setup_checks.ArtifactCheck(
            name="python-version",
            ok=False,
            message="The project Python requirement is not satisfied.",
            fix="Install a supported Python version.",
            finding_id="BASE-P170",
            status="error",
        )
        warning_check = setup_checks.ArtifactCheck(
            name="git-remote",
            ok=False,
            message="The Git remote could not be checked.",
            fix="Review the Git remote manually.",
            finding_id="BASE-P083",
            status="warn",
        )

        ctx = fake_context()
        with mock.patch(
            "base_setup.engine.pre_venv_manifest_checks",
            return_value=(error_check, warning_check),
        ):
            status = engine.check_pre_venv_manifest(ctx, manifest, output_format="text")

        self.assertEqual(status, 1)
        self.assertEqual(
            ctx.log.error.call_args_list,
            [
                mock.call(error_check.message),
                mock.call("Fix: %s", error_check.fix),
            ],
        )
        self.assertEqual(
            ctx.log.warning.call_args_list,
            [
                mock.call(warning_check.message),
                mock.call("Fix: %s", warning_check.fix),
            ],
        )

        warning_ctx = fake_context()
        with mock.patch("base_setup.engine.pre_venv_manifest_checks", return_value=(warning_check,)):
            warning_status = engine.check_pre_venv_manifest(
                warning_ctx,
                manifest,
                output_format="text",
            )

        self.assertEqual(warning_status, 0)
        warning_ctx.log.error.assert_not_called()
        self.assertEqual(
            warning_ctx.log.warning.call_args_list,
            [
                mock.call(warning_check.message),
                mock.call("Fix: %s", warning_check.fix),
            ],
        )


if __name__ == "__main__":
    unittest.main()
