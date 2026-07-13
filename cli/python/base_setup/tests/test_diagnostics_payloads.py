from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup import diagnostics
from base_setup.diagnostics import DiagnosticCheck
from base_setup.diagnostics import base_check_metadata
from base_setup.diagnostics import render_base_check_metadata
from base_setup.diagnostics import render_base_check_payload
from base_setup.diagnostics import render_base_doctor_payload
from base_setup.diagnostics import render_check_record
from base_setup.diagnostics import render_project_venv_check_payload
from base_setup.diagnostics import render_project_venv_doctor_payload


class DiagnosticsPayloadTests(unittest.TestCase):
    def test_module_documents_internal_pre_cli_boundary(self) -> None:
        module_doc = diagnostics.__doc__ or ""

        self.assertIn("internal", module_doc.lower())
        self.assertIn("pre-CLI", module_doc)
        self.assertIn("base_cli.App", module_doc)

    def test_main_rejects_base_cli_standard_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "check.json"
            stderr = io.StringIO()
            with self.assertRaises(SystemExit) as raised:
                with redirect_stderr(stderr):
                    diagnostics.main(
                        [
                            "--debug",
                            "record-check",
                            "--project",
                            "demo",
                            "--status",
                            "ok",
                            "--checked-at",
                            "2026-06-28T12:00:00Z",
                            "--output-path",
                            str(output_path),
                        ]
                    )

            self.assertEqual(raised.exception.code, 2)
            self.assertIn("--debug", stderr.getvalue())
            self.assertFalse(output_path.exists())

    def test_main_does_not_create_base_cli_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_path = root / "check.json"
            cache_root = root / "cache"
            home = root / "home"
            home.mkdir()
            env = {
                "BASE_CACHE_DIR": str(cache_root),
                "HOME": str(home),
                "BASE_HOME": os.environ.get("BASE_HOME", str(root / "base")),
            }

            with mock.patch.dict(os.environ, env), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                status = diagnostics.main(
                    [
                        "record-check",
                        "--project",
                        "demo",
                        "--status",
                        "ok",
                        "--checked-at",
                        "2026-06-28T12:00:00Z",
                        "--output-path",
                        str(output_path),
                    ]
                )

            self.assertEqual(status, 0)
            self.assertTrue(output_path.exists())
            self.assertFalse((cache_root / "cli" / "base_setup.diagnostics").exists())

    def test_render_base_check_payload_merges_embedded_statuses(self) -> None:
        payload_text = render_base_check_payload(
            checks=(
                DiagnosticCheck("homebrew", "ok", "Homebrew is installed.", ""),
                DiagnosticCheck("xcode_command_line_tools", "warn", "Xcode is incomplete.", "Repair Xcode."),
            ),
            project="demo",
            embedded_payloads=(
                (
                    "profile_checks",
                    '{"schema_version":1,"status":"error","checks":[{"id":"BASE-D104","status":"error"}]}',
                ),
                (
                    "project_checks",
                    '{"schema_version":1,"status":"ok","project":"demo","checks":[]}',
                ),
            ),
        )

        payload = json.loads(payload_text)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project"], "demo")
        self.assertEqual(payload["checks"][0]["id"], "BASE-D001")
        self.assertEqual(payload["checks"][0]["status"], "ok")
        self.assertEqual(payload["checks"][1]["id"], "BASE-D002")
        self.assertEqual(payload["checks"][1]["status"], "warn")
        self.assertEqual(payload["profile_checks"]["status"], "error")
        self.assertEqual(payload["project_checks"]["status"], "ok")
        self.assertNotIn('"ok":', payload_text)

    def test_base_check_metadata_maps_ids_and_display_names(self) -> None:
        homebrew = base_check_metadata("homebrew")
        virtualenv = base_check_metadata("base_virtualenv")
        unknown = base_check_metadata("unexpected")

        self.assertEqual(homebrew.finding_id, "BASE-D001")
        self.assertEqual(homebrew.display_name, "Homebrew")
        self.assertEqual(virtualenv.finding_id, "BASE-D004")
        self.assertEqual(virtualenv.display_name, "Base virtualenv")
        self.assertEqual(unknown.finding_id, "BASE-D000")
        self.assertEqual(unknown.display_name, "unexpected")

    def test_base_check_metadata_respects_bootstrap_package_name_overrides(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "BASE_SETUP_PYYAML_PACKAGE": "CustomYAML",
                "BASE_SETUP_CLICK_PACKAGE": "CustomClick",
            },
        ):
            pyyaml = base_check_metadata("pyyaml")
            click = base_check_metadata("click")

        self.assertEqual(pyyaml.finding_id, "BASE-D005")
        self.assertEqual(pyyaml.display_name, "CustomYAML")
        self.assertEqual(click.finding_id, "BASE-D006")
        self.assertEqual(click.display_name, "CustomClick")

    def test_render_base_check_metadata_preserves_input_order(self) -> None:
        self.assertEqual(
            render_base_check_metadata(("homebrew", "base_virtualenv", "unexpected")),
            "homebrew\tBASE-D001\tHomebrew\n"
            "base_virtualenv\tBASE-D004\tBase virtualenv\n"
            "unexpected\tBASE-D000\tunexpected\n",
        )

    def test_render_base_doctor_payload_uses_findings_key(self) -> None:
        payload_text = render_base_doctor_payload(
            checks=(DiagnosticCheck("python", "ok", "Python is installed.", ""),),
            embedded_payloads=(("project_findings", '[{"id":"BASE-P040","status":"error"}]'),),
        )

        payload = json.loads(payload_text)
        self.assertEqual(payload["status"], "error")
        self.assertIn("findings", payload)
        self.assertNotIn("checks", payload)
        self.assertEqual(payload["findings"][0]["id"], "BASE-D003")
        self.assertEqual(payload["project_findings"][0]["id"], "BASE-P040")

    def test_render_base_check_payload_uses_python_json_escaping(self) -> None:
        payload_text = render_base_check_payload(
            checks=(
                DiagnosticCheck("pyyaml", "ok", "Python package 'Py\vYAML\177' is installed.", ""),
            )
        )

        self.assertIn("Py\\u000bYAML\\u007f", payload_text)
        self.assertNotIn("Py\vYAML\177", payload_text)
        payload = json.loads(payload_text)
        self.assertEqual(payload["checks"][0]["message"], "Python package 'Py\vYAML\177' is installed.")

    def test_render_project_venv_check_payload_merges_precheck_status(self) -> None:
        payload_text = render_project_venv_check_payload(
            project="demo",
            status="error",
            message="Virtual environment is missing.",
            fix="basectl setup demo --recreate-venv",
            precheck_json='[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"ok","fix":""}]',
        )

        payload = json.loads(payload_text)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["project"], "demo")
        self.assertEqual(payload["checks"][0]["id"], "BASE-P080")
        self.assertEqual(payload["checks"][1]["id"], "BASE-P050")

    def test_render_project_venv_doctor_payload_appends_virtualenv_finding(self) -> None:
        payload_text = render_project_venv_doctor_payload(
            status="error",
            message="Virtual environment is broken.",
            fix="basectl setup demo --recreate-venv",
            precheck_json='[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"ok","fix":""}]',
        )

        payload = json.loads(payload_text)
        self.assertEqual(payload[0]["id"], "BASE-P080")
        self.assertEqual(payload[1]["id"], "BASE-P050")
        self.assertEqual(payload[1]["status"], "error")

    def test_render_check_record_uses_python_json_escaping(self) -> None:
        payload = json.loads(
            render_check_record(project='demo"quoted', status="ok", checked_at="2026-06-23T01:00:00Z")
        )

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["project"], 'demo"quoted')
        self.assertEqual(payload["command"], "basectl check")
        self.assertEqual(payload["status"], "ok")
