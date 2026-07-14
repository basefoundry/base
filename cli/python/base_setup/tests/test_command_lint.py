from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from base_setup import engine
from base_setup.checks import doctor_status
from base_setup.manifest import BaseManifest
from base_setup.manifest import BuildConfig
from base_setup.manifest import BuildTargetConfig
from base_setup.manifest import CommandConfig
from base_setup.manifest import TestConfig as ManifestTestConfig
from base_setup.tests.helpers import fake_context


def default_manifest(path: Path) -> BaseManifest:
    return BaseManifest(
        path=path,
        project_name="base-defaults",
        brewfile=None,
        artifacts=(),
    )


class CommandLintDiagnosticsTests(unittest.TestCase):
    def test_manifest_checks_warn_for_missing_test_command_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                test=ManifestTestConfig(command="base-missing-tool-817 --flag"),
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        lint_checks = [check for check in checks if check.finding_id == "BASE-P160"]
        self.assertEqual(len(lint_checks), 1)
        self.assertEqual(lint_checks[0].status, "warn")
        self.assertEqual(doctor_status(lint_checks[0]), "warn")
        self.assertEqual(lint_checks[0].name, "test.command")
        self.assertIn("base-missing-tool-817", lint_checks[0].message)

    def test_manifest_checks_warn_for_missing_project_script_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                commands={
                    "audit": CommandConfig(command="./scripts/audit.sh --strict"),
                },
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        lint_checks = [check for check in checks if check.finding_id == "BASE-P161"]
        self.assertEqual(len(lint_checks), 1)
        self.assertEqual(lint_checks[0].status, "warn")
        self.assertEqual(lint_checks[0].name, "commands.audit.command")
        self.assertIn("scripts/audit.sh", lint_checks[0].message)
        self.assertIn("Create", lint_checks[0].fix)

    def test_manifest_checks_warn_for_missing_build_target_script_from_working_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "services" / "api").mkdir(parents=True)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                build=BuildConfig(
                    default=("api",),
                    targets={
                        "api": BuildTargetConfig(
                            command="./build.sh",
                            working_dir="services/api",
                        ),
                    },
                ),
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        lint_checks = [check for check in checks if check.finding_id == "BASE-P161"]
        self.assertEqual(len(lint_checks), 1)
        self.assertEqual(lint_checks[0].status, "warn")
        self.assertEqual(lint_checks[0].name, "build.targets.api.command")
        self.assertIn("services/api/build.sh", lint_checks[0].message)

    def test_command_lint_warnings_do_not_fail_check_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                test=ManifestTestConfig(command="base-missing-tool-817 | cat"),
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                status = engine.check_manifest(
                    fake_context(),
                    default_manifest(project_root / "default.yaml"),
                    manifest,
                    output_format="json",
                )

        payload = json.loads(stdout.getvalue())
        lint_checks = [check for check in payload["checks"] if check["id"] == "BASE-P160"]
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "warn")
        self.assertEqual(len(lint_checks), 1)
        self.assertEqual(lint_checks[0]["status"], "warn")

    def test_doctor_json_reports_command_lint_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                commands={
                    "audit": CommandConfig(command="base-missing-tool-817"),
                },
            )
            stdout = StringIO()

            with redirect_stdout(stdout):
                status = engine.doctor_manifest(
                    default_manifest(project_root / "default.yaml"),
                    manifest,
                    output_format="json",
                )

        findings = json.loads(stdout.getvalue())
        lint_findings = [finding for finding in findings if finding["id"] == "BASE-P160"]
        self.assertEqual(status, 0)
        self.assertEqual(len(lint_findings), 1)
        self.assertEqual(lint_findings[0]["status"], "warn")

    def test_complex_shell_expansion_in_first_token_is_not_warned(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                test=ManifestTestConfig(command="$PROJECT_TEST_RUNNER tests"),
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        self.assertNotIn("BASE-P160", [check.finding_id for check in checks])
        self.assertNotIn("BASE-P161", [check.finding_id for check in checks])

    def test_compound_shell_command_is_not_warned_as_missing_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                test=ManifestTestConfig(command="if command -v pytest; then pytest; fi"),
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        self.assertNotIn("BASE-P160", [check.finding_id for check in checks])
        self.assertNotIn("BASE-P161", [check.finding_id for check in checks])

    def test_absolute_executable_path_outside_project_root_is_allowed_when_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            project_root.mkdir()
            tool = root / "tools" / "audit"
            tool.parent.mkdir()
            tool.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            tool.chmod(0o755)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                commands={"audit": CommandConfig(command=f"{tool} --strict")},
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        self.assertNotIn("BASE-P160", [check.finding_id for check in checks])
        self.assertNotIn("BASE-P161", [check.finding_id for check in checks])

    def test_absolute_executable_path_warns_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            project_root.mkdir()
            missing_tool = root / "missing" / "audit"
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                commands={"audit": CommandConfig(command=f"{missing_tool} --strict")},
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        lint_checks = [check for check in checks if check.finding_id == "BASE-P160"]
        self.assertEqual(len(lint_checks), 1)
        self.assertEqual(lint_checks[0].name, "commands.audit.command")

    def test_uv_runner_uses_uv_diagnostic_without_command_executable_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                commands={
                    "audit": CommandConfig(command="pytest tests/audit", runner="uv"),
                },
            )

            with mock.patch("base_setup.uv.uv_executable", return_value=None):
                checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        self.assertIn("BASE-P150", [check.finding_id for check in checks])
        self.assertNotIn("BASE-P160", [check.finding_id for check in checks])

    def test_uv_runner_still_warns_for_missing_project_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                commands={
                    "audit": CommandConfig(command="./scripts/audit.sh --strict", runner="uv"),
                },
            )

            checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        findings = [check.finding_id for check in checks]
        self.assertIn("BASE-P161", findings)
        self.assertNotIn("BASE-P160", findings)

    def test_project_venv_command_executable_does_not_warn_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            home = Path(tmpdir) / "home"
            pytest_bin = project_root / ".venv" / "bin" / "pytest"
            pytest_bin.parent.mkdir(parents=True)
            pytest_bin.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            pytest_bin.chmod(0o755)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                artifacts=(),
                test=ManifestTestConfig(command="pytest tests"),
            )

            with mock.patch.dict("os.environ", {"HOME": str(home)}), mock.patch(
                "base_setup.process.command_exists",
                return_value=False,
            ):
                checks = engine.manifest_checks(default_manifest(project_root / "default.yaml"), manifest)

        self.assertNotIn("BASE-P160", [check.finding_id for check in checks])
