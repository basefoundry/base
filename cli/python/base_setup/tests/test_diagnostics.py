from __future__ import annotations

import importlib.util
import io
import json
import os
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup import artifacts, checks as setup_checks, engine, health, ide
from base_setup.manifest import ArtifactRequest
from base_setup.manifest import BaseManifest
from base_setup.manifest import HealthConfig
from base_setup.manifest import IdeConfig
from base_setup.manifest import PortHealthConfig
from base_setup.manifest import read_manifest
from base_setup.registry import get_artifact_definition
from base_setup.tests.helpers import fake_context, run_engine

class ProjectCheckTests(unittest.TestCase):

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_project_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: python-package",
                        "    name: requests",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, _stderr = run_engine(
                ["--action", "check", "--format", "json", "--manifest", str(manifest_path), "demo"]
            )

        self.assertEqual(status, 1)
        self.assertIn('"name": "requests"', stdout)
        self.assertIn('"ok": false', stdout)
        self.assertIn('"fix": "basectl setup demo"', stdout)



    def test_check_homebrew_artifact_reports_missing_package(self) -> None:
        artifact = ArtifactRequest(artifact_type="tool", name="terraform", version="latest")
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.process.run_check",
            return_value=False,
        ):
            check = artifacts.check_homebrew_artifact("demo", artifact, definition)

        self.assertFalse(check.ok)
        self.assertIn("not installed via Homebrew package 'terraform'", check.message)
        self.assertEqual(check.fix, "basectl setup demo")



    def test_doctor_manifest_counts_failed_project_artifacts(self) -> None:
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
            artifacts=(ArtifactRequest(artifact_type="python-package", name="requests", version="latest"),),
        )

        with redirect_stdout(io.StringIO()) as stdout:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 1)
        self.assertIn("Project doctor: demo", stdout.getvalue())
        self.assertIn("Fix: basectl setup demo", stdout.getvalue())



    def test_doctor_manifest_supports_json_output(self) -> None:
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
            artifacts=(ArtifactRequest(artifact_type="python-package", name="requests", version="latest"),),
        )

        with redirect_stdout(io.StringIO()) as stdout:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(findings[0]["id"], "BASE-P040")
        self.assertEqual(findings[0]["status"], "error")
        self.assertEqual(findings[0]["fix"], "basectl setup demo")



    def test_doctor_warning_status_does_not_fail(self) -> None:
        check = setup_checks.ArtifactCheck(
            name="optional-artifact",
            ok=False,
            message="Optional project artifact is not installed.",
            fix="basectl setup demo",
            status="warn",
        )

        self.assertEqual(engine.doctor_status(check), "warn")
        self.assertEqual(setup_checks.check_to_doctor_json(check)["id"], "BASE-P000")
        self.assertEqual(setup_checks.check_to_doctor_json(check)["status"], "warn")

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
        with mock.patch("base_setup.engine.manifest_checks", return_value=(check,)):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 0)
        self.assertIn("warn", stdout.getvalue())



    def test_check_manifest_reports_required_environment_variables(self) -> None:
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
            health=HealthConfig(
                required_env=(
                    "BASE_TEST_REQUIRED_PRESENT",
                    "BASE_TEST_REQUIRED_MISSING",
                )
            ),
        )

        with mock.patch.dict(os.environ, {"BASE_TEST_REQUIRED_PRESENT": "super-secret-value"}, clear=False):
            os.environ.pop("BASE_TEST_REQUIRED_MISSING", None)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.check_manifest(
                    fake_context(),
                    default_manifest,
                    manifest,
                    output_format="json",
                )

        output = stdout.getvalue()
        parsed_checks = json.loads(output)
        self.assertEqual(status, 1)
        self.assertEqual(
            [check["name"] for check in parsed_checks],
            ["BASE_TEST_REQUIRED_PRESENT", "BASE_TEST_REQUIRED_MISSING"],
        )
        self.assertTrue(parsed_checks[0]["ok"])
        self.assertFalse(parsed_checks[1]["ok"])
        self.assertEqual(
            parsed_checks[1]["fix"],
            "Set BASE_TEST_REQUIRED_MISSING in your shell, .env, or secrets manager.",
        )
        self.assertNotIn("super-secret-value", output)


    def test_check_manifest_reports_required_ports(self) -> None:
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
            health=HealthConfig(
                required_ports=(
                    PortHealthConfig(
                        name="postgres",
                        host="127.0.0.1",
                        port=5432,
                        state="listening",
                    ),
                    PortHealthConfig(name="app", host="127.0.0.1", port=8000, state="free"),
                    PortHealthConfig(name="busy-app", host="127.0.0.1", port=9000, state="free"),
                )
            ),
        )

        def fake_port_probe(_host: str, port: int) -> bool:
            return port in (5432, 9000)

        with mock.patch("base_setup.health.tcp_port_is_listening", side_effect=fake_port_probe):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.check_manifest(
                    fake_context(),
                    default_manifest,
                    manifest,
                    output_format="json",
                )

        parsed_checks = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(
            [check["name"] for check in parsed_checks],
            ["postgres", "app", "busy-app"],
        )
        self.assertTrue(parsed_checks[0]["ok"])
        self.assertTrue(parsed_checks[1]["ok"])
        self.assertFalse(parsed_checks[2]["ok"])
        self.assertIn("already listening", parsed_checks[2]["message"])
        self.assertEqual(
            parsed_checks[2]["fix"],
            "Stop the process using 127.0.0.1:9000 or choose a different project port.",
        )


    def test_tcp_port_probe_reports_listening_socket(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            try:
                listener.bind(("127.0.0.1", 0))
            except PermissionError as exc:
                self.skipTest(f"Loopback socket bind is not permitted: {exc}")
            listener.listen(1)
            port = listener.getsockname()[1]

            self.assertTrue(health.tcp_port_is_listening("127.0.0.1", port))



    def test_doctor_manifest_reports_required_environment_variables_without_values(self) -> None:
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
            health=HealthConfig(
                required_env=(
                    "BASE_TEST_DOCTOR_PRESENT",
                    "BASE_TEST_DOCTOR_MISSING",
                )
            ),
        )

        with mock.patch.dict(os.environ, {"BASE_TEST_DOCTOR_PRESENT": "another-secret-value"}, clear=False):
            os.environ.pop("BASE_TEST_DOCTOR_MISSING", None)
            with redirect_stdout(io.StringIO()) as stdout:
                status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        output = stdout.getvalue()
        self.assertEqual(status, 1)
        self.assertIn("ok", output)
        self.assertIn("BASE_TEST_DOCTOR_PRESENT", output)
        self.assertIn("Environment variable 'BASE_TEST_DOCTOR_PRESENT' is set.", output)
        self.assertIn("error", output)
        self.assertIn("BASE_TEST_DOCTOR_MISSING", output)
        self.assertIn("Fix: Set BASE_TEST_DOCTOR_MISSING in your shell, .env, or secrets manager.", output)
        self.assertNotIn("another-secret-value", output)


    def test_doctor_manifest_reports_required_ports_with_finding_ids(self) -> None:
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
            health=HealthConfig(
                required_ports=(
                    PortHealthConfig(name="postgres", port=5432, state="listening"),
                    PortHealthConfig(name="app", port=8000, state="free"),
                )
            ),
        )

        with mock.patch("base_setup.health.tcp_port_is_listening", return_value=False):
            with redirect_stdout(io.StringIO()) as stdout:
                status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(
            [finding["id"] for finding in findings],
            ["BASE-H002", "BASE-H002"],
        )
        self.assertEqual(
            [finding["status"] for finding in findings],
            ["error", "ok"],
        )
        self.assertEqual(
            findings[0]["fix"],
            "Start the service that should listen on 127.0.0.1:5432.",
        )



class IdeDiagnosticsTests(unittest.TestCase):

    def test_check_json_reports_ide_app_extension_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    install: true",
                        "    extensions:",
                        "      - ms-python.python",
                        "    settings:",
                        "      editor.formatOnSave: true",
                    ]
                ),
                encoding="utf-8",
            )

            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)
            with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
                "base_setup.process.run_check",
                return_value=True,
            ), mock.patch(
                "base_setup.ide.list_ide_extensions",
                return_value={"ms-python.python"},
            ), mock.patch.dict(os.environ, {"HOME": tmpdir, "XDG_CONFIG_HOME": ""}):
                settings_file = ide.ide_settings_file(ide.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                stdout_buffer = io.StringIO()
                with redirect_stdout(stdout_buffer):
                    status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        checks = json.loads(stdout_buffer.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(
            [check["name"] for check in checks],
            ["VS Code app", "ms-python.python", "VS Code setting: editor.formatOnSave"],
        )
        self.assertTrue(all(check["ok"] for check in checks))



    def test_doctor_text_reports_ide_fix_guidance(self) -> None:
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
            ide={
                "cursor": IdeConfig(
                    install=True,
                    extensions=("github.copilot",),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}), mock.patch(
                "base_setup.process.command_exists",
                return_value=False,
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        output = stdout.getvalue()
        self.assertGreater(status, 0)
        self.assertIn("Project doctor: demo", output)
        self.assertIn("Cursor app", output)
        self.assertIn("github.copilot", output)
        self.assertIn("Cursor setting: editor.formatOnSave", output)
        self.assertIn("Fix:", output)
