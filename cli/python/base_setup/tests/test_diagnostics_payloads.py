from __future__ import annotations

import json
import unittest

from base_setup.diagnostics import DiagnosticCheck
from base_setup.diagnostics import render_base_check_payload
from base_setup.diagnostics import render_base_doctor_payload
from base_setup.diagnostics import render_check_record
from base_setup.diagnostics import render_project_venv_check_payload
from base_setup.diagnostics import render_project_venv_doctor_payload


class DiagnosticsPayloadTests(unittest.TestCase):
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
