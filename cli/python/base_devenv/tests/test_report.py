from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from base_devenv.report import build_devenv_report
from base_devenv.report import dumps_devenv_report_json
from base_devenv.report import print_devenv_report_text
from base_setup.manifest import read_manifest


def read_manifest_text(root: Path, body: str):
    manifest_path = root / "base_manifest.yaml"
    manifest_path.write_text(body, encoding="utf-8")
    return read_manifest(manifest_path)


class DevenvReportPackageTests(unittest.TestCase):
    def test_build_devenv_report_classifies_minimal_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = read_manifest_text(
                Path(tmpdir),
                "project:\n  name: demo\nartifacts: []\n",
            )

            report = build_devenv_report(manifest)

        self.assertEqual(report.project, "demo")
        self.assertEqual(report.fields[0].field, "project.name")
        self.assertEqual(report.fields[0].classification, "supported")

    def test_devenv_report_json_classifies_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = read_manifest_text(
                Path(tmpdir),
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "brewfile: Brewfile",
                        "mise: .mise.toml",
                        "python:",
                        "  manager: uv",
                        "  requires_python: '>=3.12'",
                        "ide:",
                        "  vscode:",
                        "    extensions:",
                        "      - ms-python.python",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: latest",
                        "test:",
                        "  command: pytest",
                        "commands:",
                        "  lint: ruff check .",
                        "health:",
                        "  required_env:",
                        "    - API_TOKEN",
                        "  required_ports:",
                        "    - port: 8080",
                        "      state: listening",
                        "activate:",
                        "  source:",
                        "    - .venv/bin/activate",
                        "build:",
                        "  default:",
                        "    - api",
                        "  targets:",
                        "    api:",
                        "      command: go build ./cmd/api",
                        "demo:",
                        "  script: ./demo.sh",
                        "",
                    ]
                ),
            )

            payload = json.loads(dumps_devenv_report_json(build_devenv_report(manifest)))

        classifications = {item["field"]: item["classification"] for item in payload["fields"]}
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["target"], "nix/devenv")
        self.assertEqual(classifications["project.name"], "supported")
        self.assertEqual(classifications["brewfile"], "unsupported")
        self.assertEqual(classifications["ide.vscode"], "unsupported")
        self.assertEqual(classifications["artifacts[1]"], "lossy")
        self.assertEqual(classifications["python.manager"], "lossy")
        self.assertEqual(classifications["python.requires_python"], "lossy")
        self.assertEqual(classifications["mise"], "project-owned")
        self.assertEqual(classifications["test"], "project-owned")
        self.assertEqual(classifications["commands"], "project-owned")
        self.assertEqual(classifications["health.required_env"], "project-owned")
        self.assertEqual(classifications["health.required_ports"], "project-owned")
        self.assertEqual(classifications["activate.source"], "project-owned")
        self.assertEqual(classifications["build"], "project-owned")
        self.assertEqual(classifications["demo"], "project-owned")
        self.assertEqual(
            payload["summary"],
            {"supported": 1, "unsupported": 2, "lossy": 3, "project-owned": 8},
        )

    def test_print_devenv_report_text_is_human_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = read_manifest_text(
                Path(tmpdir),
                "project:\n  name: demo\npython:\n  requires_python: '>=3.12'\nartifacts: []\n",
            )
            report = build_devenv_report(manifest)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                print_devenv_report_text(report)

        output = stdout.getvalue()
        self.assertIn("Nix/devenv compatibility for project 'demo'", output)
        self.assertIn("project.name", output)
        self.assertIn("python.requires_python", output)
        self.assertIn("lossy", output)


if __name__ == "__main__":
    unittest.main()
