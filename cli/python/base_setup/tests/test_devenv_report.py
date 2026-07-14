from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from base_setup.tests.helpers import run_engine


def write_manifest(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


class DevenvReportTests(unittest.TestCase):
    def test_devenv_report_json_classifies_minimal_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(
                manifest_path,
                "project:\n  name: demo\nartifacts: []\n",
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "devenv-report", "--format", "json", "demo"]
            )

        payload = json.loads(stdout)
        fields = {item["field"]: item for item in payload["fields"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["project"], "demo")
        self.assertEqual(payload["target"], "nix/devenv")
        self.assertEqual(fields["project.name"]["classification"], "supported")
        self.assertEqual(payload["summary"], {"supported": 1, "unsupported": 0, "lossy": 0, "project-owned": 0})

    def test_devenv_report_json_classifies_unsupported_lossy_and_project_owned_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(
                manifest_path,
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
                        "  - type: python-package",
                        "    name: requests",
                        "    version: latest",
                        "test:",
                        "  command: pytest",
                        "commands:",
                        "  lint: ruff check .",
                        "health:",
                        "  required_env:",
                        "    - API_TOKEN",
                        "build:",
                        "  default:",
                        "    - api",
                        "  targets:",
                        "    api:",
                        "      command: go build ./cmd/api",
                        "",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "devenv-report", "--format", "json", "demo"]
            )

        payload = json.loads(stdout)
        classifications = {item["field"]: item["classification"] for item in payload["fields"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(classifications["brewfile"], "unsupported")
        self.assertEqual(classifications["ide.vscode"], "unsupported")
        self.assertEqual(classifications["artifacts[1]"], "lossy")
        self.assertEqual(classifications["artifacts[2]"], "lossy")
        self.assertEqual(classifications["python.manager"], "lossy")
        self.assertEqual(classifications["python.requires_python"], "lossy")
        self.assertEqual(classifications["mise"], "project-owned")
        self.assertEqual(classifications["test"], "project-owned")
        self.assertEqual(classifications["commands"], "project-owned")
        self.assertEqual(classifications["health.required_env"], "project-owned")
        self.assertEqual(classifications["build"], "project-owned")
        self.assertEqual(
            payload["summary"],
            {"supported": 1, "unsupported": 2, "lossy": 4, "project-owned": 5},
        )

    def test_devenv_report_json_classifies_external_python_venv_location_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(
                manifest_path,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  venv_location: external",
                        "artifacts: []",
                        "",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "devenv-report", "--format", "json", "demo"]
            )

        payload = json.loads(stdout)
        classifications = {item["field"]: item["classification"] for item in payload["fields"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(classifications["python.venv_location"], "unsupported")

    def test_devenv_report_text_is_human_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(
                manifest_path,
                "project:\n  name: demo\npython:\n  requires_python: '>=3.12'\nartifacts: []\n",
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "devenv-report", "demo"]
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Nix/devenv compatibility for project 'demo'", stdout)
        self.assertIn("project.name", stdout)
        self.assertIn("python.requires_python", stdout)
        self.assertIn("lossy", stdout)
