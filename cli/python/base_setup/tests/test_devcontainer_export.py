from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from base_setup.tests.helpers import run_engine


def write_manifest(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


class DevcontainerExportTests(unittest.TestCase):
    def test_devcontainer_export_defaults_to_stable_json_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(
                manifest_path,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    extensions:",
                        "      - ms-python.python",
                        "    settings:",
                        "      python.defaultInterpreterPath: .venv/bin/python",
                        "artifacts: []",
                        "",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "devcontainer", "--format", "json", "demo"]
            )

            target_path = manifest_path.resolve().parent / ".devcontainer" / "devcontainer.json"

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(stdout.startswith("{\n"))
        self.assertEqual(payload["schema_version"], 1)
        self.assertFalse(payload["write"])
        self.assertFalse(payload["target_exists"])
        self.assertEqual(payload["target_path"], str(target_path))
        self.assertFalse(target_path.exists())
        self.assertEqual(
            payload["devcontainer"],
            {
                "customizations": {
                    "vscode": {
                        "extensions": ["ms-python.python"],
                        "settings": {"python.defaultInterpreterPath": ".venv/bin/python"},
                    }
                },
                "name": "demo",
            },
        )
        self.assertEqual(payload["supported"], ["project.name", "ide.vscode.extensions", "ide.vscode.settings"])
        self.assertEqual(payload["unsupported"], [])
        self.assertEqual(payload["ambiguous"], [])

    def test_devcontainer_export_reports_unsupported_and_ambiguous_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            (root / "Brewfile").write_text("brew 'jq'\n", encoding="utf-8")
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
                        "  cursor:",
                        "    extensions:",
                        "      - github.copilot",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: latest",
                        "test:",
                        "  command: pytest",
                        "health:",
                        "  required_env:",
                        "    - API_TOKEN",
                        "",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "devcontainer", "--format", "json", "demo"]
            )

        payload = json.loads(stdout)
        unsupported_fields = {item["field"] for item in payload["unsupported"]}
        ambiguous_fields = {item["field"] for item in payload["ambiguous"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["devcontainer"]["customizations"]["vscode"]["extensions"], ["ms-python.python"])
        self.assertLessEqual(
            {"brewfile", "mise", "ide.cursor", "artifacts[1]", "test", "health.required_env"},
            unsupported_fields,
        )
        self.assertEqual({"python.manager", "python.requires_python"}, ambiguous_fields)

    def test_devcontainer_write_refuses_to_replace_existing_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            target_path = root / ".devcontainer" / "devcontainer.json"
            target_path.parent.mkdir()
            target_path.write_text('{"name":"project-owned"}\n', encoding="utf-8")
            write_manifest(
                manifest_path,
                "project:\n  name: demo\nartifacts: []\n",
            )

            status, stdout, stderr = run_engine(
                [
                    "--manifest",
                    str(manifest_path),
                    "--action",
                    "devcontainer",
                    "--format",
                    "json",
                    "--write",
                    "demo",
                ]
            )
            target_content = target_path.read_text(encoding="utf-8")

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("already exists; refusing to replace project-owned devcontainer file", stderr)
        self.assertEqual(target_content, '{"name":"project-owned"}\n')

    def test_devcontainer_write_creates_target_only_with_write_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            target_path = root / ".devcontainer" / "devcontainer.json"
            write_manifest(
                manifest_path,
                "project:\n  name: demo\nartifacts: []\n",
            )

            status, stdout, stderr = run_engine(
                [
                    "--manifest",
                    str(manifest_path),
                    "--action",
                    "devcontainer",
                    "--format",
                    "json",
                    "--write",
                    "demo",
                ]
            )
            target_payload = json.loads(target_path.read_text(encoding="utf-8"))

        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(payload["write"])
        self.assertEqual(target_payload, {"name": "demo"})
