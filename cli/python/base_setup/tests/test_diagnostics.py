from __future__ import annotations

import importlib.util
import io
import json
import os
import socket
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup import artifacts, checks as setup_checks, engine, health, ide
from base_setup.manifest import ArtifactRequest
from base_setup.manifest import BaseManifest
from base_setup.manifest import HealthConfig
from base_setup.manifest import IdeConfig
from base_setup.manifest import PortHealthConfig
from base_setup.manifest import PythonConfig
from base_setup.manifest_model import ActivateConfig
from base_setup.manifest import read_manifest
from base_setup.python_policy import PythonInterpreter
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

        payload = json.loads(stdout)
        checks = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project"], "demo")
        request_checks = [check for check in checks if check["name"] == "requests"]
        self.assertEqual(len(request_checks), 1)
        self.assertEqual(request_checks[0]["status"], "error")
        self.assertNotIn("ok", request_checks[0])
        self.assertEqual(request_checks[0]["fix"], "basectl setup demo")
        self.assertEqual(request_checks[0]["details"]["artifact_type"], "python-package")
        self.assertEqual(request_checks[0]["details"]["manager"], "pip")
        self.assertEqual(request_checks[0]["details"]["package"], "requests")
        self.assertEqual(request_checks[0]["details"]["target"], "project-venv")
        self.assertEqual(request_checks[0]["details"]["version_policy"], "requested")
        self.assertTrue(request_checks[0]["details"]["registry_source"].endswith("lib/base/artifact-registry.yaml"))



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

    def test_check_homebrew_artifact_reports_outdated_package(self) -> None:
        artifact = ArtifactRequest(artifact_type="tool", name="terraform", version="latest")
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)

        outdated = subprocess.CompletedProcess(
            ["brew", "outdated", "terraform"],
            0,
            stdout="terraform\n",
            stderr="",
        )
        with (
            mock.patch("base_setup.process.command_exists", return_value=True),
            mock.patch("base_setup.process.run_check", return_value=True),
            mock.patch("base_setup.process.run_capture", return_value=outdated),
        ):
            check = artifacts.check_homebrew_artifact("demo", artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P033")
        self.assertIn("outdated via Homebrew package 'terraform'", check.message)
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

        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Project doctor: demo", stderr.getvalue())
        self.assertIn("Fix: basectl setup demo", stderr.getvalue())



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

        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(status, 1)
        self.assertEqual(findings[0]["id"], "BASE-P040")
        self.assertEqual(findings[0]["status"], "error")
        self.assertEqual(findings[0]["fix"], "basectl setup demo")

    def test_doctor_stream_contract_separates_output_from_usage_errors(self) -> None:
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

        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="xml")

        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Unsupported doctor output format 'xml'. Expected text or json.", stderr.getvalue())

        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            status = engine.doctor_pre_venv_manifest(manifest, output_format="yaml")

        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Unsupported doctor output format 'yaml'. Expected text or json.", stderr.getvalue())

        check = setup_checks.ArtifactCheck(
            name="required-artifact",
            ok=False,
            message="Required project artifact is not installed.",
            fix="basectl setup demo",
            finding_id="BASE-P040",
        )
        with mock.patch("base_setup.engine.manifest_checks", return_value=(check,)):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error", stderr.getvalue())
        self.assertIn("BASE-P040", stderr.getvalue())



    def test_doctor_warning_status_does_not_fail(self) -> None:
        check = setup_checks.ArtifactCheck(
            name="optional-artifact",
            ok=False,
            message="Optional project artifact is not installed.",
            fix="basectl setup demo",
            finding_id="BASE-P033",
            status="warn",
        )

        self.assertEqual(engine.doctor_status(check), "warn")
        self.assertEqual(setup_checks.check_to_json(check)["id"], "BASE-P033")
        self.assertEqual(setup_checks.check_to_json(check)["status"], "warn")

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
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("warn", stderr.getvalue())

    def test_artifact_check_requires_explicit_finding_id(self) -> None:
        kwargs = {
            "name": "optional-artifact",
            "ok": False,
            "message": "Optional project artifact is not installed.",
            "fix": "basectl setup demo",
        }

        with self.assertRaises(TypeError):
            setup_checks.ArtifactCheck(**kwargs)



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
                    "BASE_TEST_REQUIRED_EMPTY",
                )
            ),
        )

        with mock.patch.dict(
            os.environ,
            {
                "BASE_TEST_REQUIRED_PRESENT": "super-secret-value",
                "BASE_TEST_REQUIRED_EMPTY": "",
            },
            clear=False,
        ):
            os.environ.pop("BASE_TEST_REQUIRED_MISSING", None)
            stdout = io.StringIO()
            doctor_stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.check_manifest(
                    fake_context(),
                    default_manifest,
                    manifest,
                    output_format="json",
                )
            with redirect_stdout(doctor_stdout):
                doctor_status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        output = stdout.getvalue()
        payload = json.loads(output)
        parsed_checks = payload["checks"]
        doctor_findings = json.loads(doctor_stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project"], "demo")
        self.assertEqual(doctor_status, 2)
        self.assertEqual(
            [check["name"] for check in parsed_checks],
            [
                "BASE_TEST_REQUIRED_PRESENT",
                "BASE_TEST_REQUIRED_MISSING",
                "BASE_TEST_REQUIRED_EMPTY",
            ],
        )
        self.assertEqual(
            [finding["id"] for finding in doctor_findings],
            ["BASE-H001", "BASE-H001", "BASE-H001"],
        )
        self.assertEqual(
            [finding["name"] for finding in doctor_findings],
            [
                "BASE_TEST_REQUIRED_PRESENT",
                "BASE_TEST_REQUIRED_MISSING",
                "BASE_TEST_REQUIRED_EMPTY",
            ],
        )
        self.assertEqual([check["status"] for check in parsed_checks], ["ok", "error", "error"])
        self.assertTrue(all("ok" not in check for check in parsed_checks))
        self.assertEqual(
            parsed_checks[1]["message"],
            "Environment variable 'BASE_TEST_REQUIRED_MISSING' is not set or is empty.",
        )
        self.assertEqual(
            parsed_checks[2]["message"],
            "Environment variable 'BASE_TEST_REQUIRED_EMPTY' is not set or is empty.",
        )
        self.assertEqual(
            parsed_checks[1]["fix"],
            "Set BASE_TEST_REQUIRED_MISSING in your shell, .env, or secrets manager.",
        )
        self.assertEqual(
            parsed_checks[2]["fix"],
            "Set BASE_TEST_REQUIRED_EMPTY in your shell, .env, or secrets manager.",
        )
        self.assertNotIn("super-secret-value", output)

        activation_manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            activate=ActivateConfig(source=(".base/activate.sh",)),
            health=HealthConfig(required_env=("BASE_TEST_ACTIVATION_ENV",)),
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BASE_TEST_ACTIVATION_ENV", None)
            activation_stdout = io.StringIO()
            with redirect_stdout(activation_stdout):
                activation_status = engine.check_manifest(
                    fake_context(),
                    default_manifest,
                    activation_manifest,
                    output_format="json",
                )
        activation_payload = json.loads(activation_stdout.getvalue())
        with self.subTest("activation hint"):
            self.assertEqual(activation_status, 1)
            self.assertEqual(
                activation_payload["checks"][0]["fix"],
                "Set BASE_TEST_ACTIVATION_ENV in your shell, .env, or secrets manager, "
                "or run 'basectl activate demo' if the project activation provides it.",
            )


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

        payload = json.loads(stdout.getvalue())
        parsed_checks = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project"], "demo")
        self.assertEqual(
            [check["name"] for check in parsed_checks],
            ["postgres", "app", "busy-app"],
        )
        self.assertEqual([check["status"] for check in parsed_checks], ["ok", "ok", "error"])
        self.assertTrue(all("ok" not in check for check in parsed_checks))
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
            with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        output = stdout.getvalue()
        error_output = stderr.getvalue()
        self.assertEqual(status, 1)
        self.assertIn("ok", output)
        self.assertIn("BASE_TEST_DOCTOR_PRESENT", output)
        self.assertIn("Environment variable 'BASE_TEST_DOCTOR_PRESENT' is set.", output)
        self.assertIn("error", error_output)
        self.assertIn("BASE_TEST_DOCTOR_MISSING", error_output)
        self.assertIn("Environment variable 'BASE_TEST_DOCTOR_MISSING' is not set or is empty.", error_output)
        self.assertIn("Fix: Set BASE_TEST_DOCTOR_MISSING in your shell, .env, or secrets manager.", error_output)
        self.assertNotIn("another-secret-value", output)
        self.assertNotIn("another-secret-value", error_output)


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

    def test_check_json_reports_unsupported_python_requirement(self) -> None:
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
            python=PythonConfig(requires_python="3.9"),
        )

        with redirect_stdout(io.StringIO()) as stdout:
            status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        payload = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual([check["id"] for check in payload["checks"]], ["BASE-P170"])
        self.assertEqual(payload["checks"][0]["status"], "error")
        self.assertIn("older than Base supports", payload["checks"][0]["message"])

    def test_pre_venv_checks_include_python_requirement_policy(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            python=PythonConfig(requires_python=">=3.14"),
        )

        checks = engine.pre_venv_manifest_checks(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P170"])
        self.assertIn("newer than Base supports", checks[0].message)

    def test_check_json_reports_supported_python_requirement_without_interpreter(self) -> None:
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
            python=PythonConfig(requires_python="3.12"),
        )

        with mock.patch("base_setup.python_policy.resolve_python_interpreter", return_value=None), redirect_stdout(
            io.StringIO()
        ) as stdout:
            status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        payload = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual([check["id"] for check in payload["checks"]], ["BASE-P170", "BASE-P171"])
        self.assertEqual([check["status"] for check in payload["checks"]], ["ok", "error"])
        self.assertIn("Python 3.12 is not available", payload["checks"][1]["message"])

    def test_check_json_reports_actual_project_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            project_root = root / "demo"
            home.mkdir()
            project_root.mkdir()
            manifest_path = project_root / "base_manifest.yaml"
            manifest_path.write_text(
                "project:\n  name: demo\npython:\n  requires_python: '3.12'\nartifacts: []\n",
                encoding="utf-8",
            )
            python_bin = (project_root / ".venv" / "bin" / "python").resolve()
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/bin/sh\nprintf '3.12\\n'\n", encoding="utf-8")
            python_bin.chmod(0o755)
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)

            with mock.patch.dict(os.environ, {"HOME": str(home)}), mock.patch(
                "base_setup.python_policy.resolve_python_interpreter",
                return_value=PythonInterpreter(path=python_bin, version=(3, 12)),
            ), redirect_stdout(io.StringIO()) as stdout:
                status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        payload = json.loads(stdout.getvalue())
        runtime_check = next(check for check in payload["checks"] if check["id"] == "BASE-P172")
        self.assertEqual(status, 0)
        self.assertEqual(runtime_check["status"], "ok")
        self.assertEqual(runtime_check["details"]["python_version"], "3.12")
        self.assertEqual(runtime_check["details"]["python"], str(python_bin))
        self.assertEqual(runtime_check["details"]["venv"], str(python_bin.parent.parent))
        self.assertEqual(runtime_check["details"]["requires_python"], "3.12")

    def test_manifest_checks_include_same_directory_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo-python\"\nrequires-python = \">=3.11\"\n",
                encoding="utf-8",
            )
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)

            checks = engine.manifest_checks(default_manifest, manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P140"])
        self.assertIn("demo-python", checks[0].message)


    def test_check_json_includes_pyproject_warnings_without_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo-python\"\ndependencies = [\"requests\"]\n",
                encoding="utf-8",
            )
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)

            with redirect_stdout(io.StringIO()) as stdout:
                status = engine.check_manifest(
                    fake_context(),
                    default_manifest,
                    manifest,
                    output_format="json",
                )

        payload = json.loads(stdout.getvalue())
        checks = payload["checks"]
        self.assertEqual(status, 0)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "warn")
        self.assertEqual(payload["project"], "demo")
        self.assertEqual([check["name"] for check in checks], ["pyproject.toml", "pyproject dependencies"])
        self.assertEqual([check["status"] for check in checks], ["ok", "warn"])
        self.assertTrue(all("ok" not in check for check in checks))
        self.assertIn("does not reconcile yet", checks[1]["message"])


    def test_doctor_json_reports_pyproject_warnings_without_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[tool.base]\ncommand = \"pytest\"\n", encoding="utf-8")
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)

            with redirect_stdout(io.StringIO()) as stdout:
                status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual([finding["id"] for finding in findings], ["BASE-P140", "BASE-P143"])
        self.assertEqual([finding["status"] for finding in findings], ["ok", "warn"])



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
                "base_setup.ide_extensions.list_ide_extensions",
                return_value={"ms-python.python"},
            ), mock.patch.dict(os.environ, {"HOME": tmpdir, "XDG_CONFIG_HOME": "", "BASE_SETUP_PROFILES": "dev"}):
                settings_file = ide.ide_settings_file(ide.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                stdout_buffer = io.StringIO()
                with redirect_stdout(stdout_buffer):
                    status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        payload = json.loads(stdout_buffer.getvalue())
        checks = payload["checks"]
        self.assertEqual(status, 0)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["project"], "demo")
        self.assertEqual(
            [check["name"] for check in checks],
            ["VS Code app", "ms-python.python", "VS Code setting: editor.formatOnSave"],
        )
        self.assertTrue(all(check["status"] == "ok" for check in checks))
        self.assertTrue(all("ok" not in check for check in checks))



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
            with mock.patch.dict(
                os.environ,
                {"HOME": home_dir, "XDG_CONFIG_HOME": "", "BASE_SETUP_PROFILES": "dev"},
            ), mock.patch(
                "base_setup.process.command_exists",
                return_value=False,
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        output = stdout.getvalue()
        error_output = stderr.getvalue()
        self.assertGreater(status, 0)
        self.assertEqual(output, "")
        self.assertIn("Project doctor: demo", error_output)
        self.assertIn("Cursor app", error_output)
        self.assertIn("github.copilot", error_output)
        self.assertIn("Cursor setting: editor.formatOnSave", error_output)
        self.assertIn("Fix:", error_output)
