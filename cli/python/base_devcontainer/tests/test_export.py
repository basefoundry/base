from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from base_devcontainer.export import DevcontainerExportError
from base_devcontainer.export import build_devcontainer_export
from base_devcontainer.export import devcontainer_export_to_json
from base_devcontainer.export import dumps_export_json
from base_devcontainer.export import print_devcontainer_export_text
from base_devcontainer.export import write_devcontainer_export
from base_setup.manifest import read_manifest


def write_manifest(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


class DevcontainerExportTests(unittest.TestCase):
    def test_build_devcontainer_export_uses_manifest_metadata(self) -> None:
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
                        "artifacts: []",
                        "",
                    ]
                ),
            )

            export = build_devcontainer_export(read_manifest(manifest_path))

        self.assertEqual(export.project, "demo")
        self.assertEqual(export.target_path, manifest_path.parent / ".devcontainer" / "devcontainer.json")
        self.assertEqual(
            export.devcontainer,
            {
                "customizations": {"vscode": {"extensions": ["ms-python.python"]}},
                "name": "demo",
            },
        )
        self.assertEqual(export.supported, ("project.name", "ide.vscode.extensions"))

    def test_write_devcontainer_export_writes_stable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)

            write_devcontainer_export(export)

            payload = json.loads(export.target_path.read_text(encoding="utf-8"))

        self.assertEqual(payload, {"name": "demo"})

    def test_build_export_classifies_supported_unsupported_and_ambiguous_fields(self) -> None:
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
                        "    settings:",
                        "      python.defaultInterpreterPath: .venv/bin/python",
                        "  cursor:",
                        "    extensions: [github.copilot]",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: latest",
                        "test:",
                        "  command: pytest",
                        "health:",
                        "  required_env: [API_TOKEN]",
                        "  required_ports:",
                        "    - port: 8080",
                        "      state: listening",
                        "commands:",
                        "  lint: ruff check .",
                        "activate:",
                        "  source: [.base/activate.sh]",
                        "build:",
                        "  targets:",
                        "    app:",
                        "      command: make build",
                        "",
                    ]
                ),
            )

            export = build_devcontainer_export(read_manifest(manifest_path))

        self.assertEqual(
            export.devcontainer["customizations"],
            {"vscode": {"settings": {"python.defaultInterpreterPath": ".venv/bin/python"}}},
        )
        self.assertEqual(export.supported, ("project.name", "ide.vscode.settings"))
        self.assertEqual(
            {finding.field for finding in export.unsupported},
            {
                "ide.cursor",
                "brewfile",
                "mise",
                "artifacts[1]",
                "test",
                "health.required_env",
                "health.required_ports",
                "commands",
                "activate.source",
                "build",
            },
        )
        self.assertEqual(
            {finding.field for finding in export.ambiguous},
            {"python.manager", "python.requires_python"},
        )

    def test_build_export_classifies_external_python_environment_as_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            write_manifest(
                manifest_path,
                "project:\n  name: demo\npython:\n  venv_location: external\nartifacts: []\n",
            )

            export = build_devcontainer_export(read_manifest(manifest_path))

        self.assertEqual([finding.field for finding in export.ambiguous], ["python.venv_location"])

    def test_write_export_refuses_to_replace_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            target_path = root / ".devcontainer" / "devcontainer.json"
            target_path.parent.mkdir()
            target_path.write_text('{"name":"owned"}\n', encoding="utf-8")
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)

            with self.assertRaisesRegex(DevcontainerExportError, "refusing to replace"):
                write_devcontainer_export(export)

            self.assertEqual(target_path.read_text(encoding="utf-8"), '{"name":"owned"}\n')

    def test_write_export_refuses_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outside = root / "outside"
            outside.mkdir()
            manifest_path = root / "base_manifest.yaml"
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            (root / ".devcontainer").symlink_to(outside, target_is_directory=True)
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)

            with self.assertRaisesRegex(DevcontainerExportError, "symlink"):
                write_devcontainer_export(export)

            self.assertFalse((outside / "devcontainer.json").exists())

    def test_write_export_refuses_dangling_target_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outside_target = root / "outside" / "devcontainer.json"
            manifest_path = root / "base_manifest.yaml"
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            target_path = root / ".devcontainer" / "devcontainer.json"
            target_path.parent.mkdir()
            target_path.symlink_to(outside_target)
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)

            with self.assertRaisesRegex(DevcontainerExportError, "already exists"):
                write_devcontainer_export(export)

            self.assertFalse(outside_target.exists())

    def test_write_export_refuses_in_project_dangling_target_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            target_path = root / ".devcontainer" / "devcontainer.json"
            target_path.parent.mkdir()
            target_path.symlink_to(root / "templates" / "devcontainer.json")
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)

            with self.assertRaisesRegex(DevcontainerExportError, "already exists|unsafe"):
                write_devcontainer_export(export)

    def test_write_export_rechecks_target_after_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)
            export.target_path.parent.mkdir()
            export.target_path.write_text('{"name":"owned"}\n', encoding="utf-8")

            with self.assertRaisesRegex(DevcontainerExportError, "already exists"):
                write_devcontainer_export(export)

            self.assertEqual(export.target_path.read_text(encoding="utf-8"), '{"name":"owned"}\n')

    def test_json_and_text_rendering_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(
                manifest_path,
                "project:\n  name: demo\ntest:\n  command: pytest\nartifacts: []\n",
            )
            export = build_devcontainer_export(read_manifest(manifest_path))
            output = io.StringIO()

            with redirect_stdout(output):
                print_devcontainer_export_text(export)

        payload = devcontainer_export_to_json(export)
        self.assertEqual(json.loads(dumps_export_json(export)), payload)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["unsupported"][0]["field"], "test")
        self.assertIn("Mode: dry-run", output.getvalue())
        self.assertIn("Dry run: no files were written.", output.getvalue())
        self.assertIn("Unsupported fields:\n- test:", output.getvalue())
        self.assertNotIn("Ambiguous fields:", output.getvalue())

    def test_text_rendering_reports_write_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            write_manifest(manifest_path, "project:\n  name: demo\nartifacts: []\n")
            export = build_devcontainer_export(read_manifest(manifest_path), write=True)
            output = io.StringIO()

            with redirect_stdout(output):
                print_devcontainer_export_text(export)

        self.assertIn("Mode: write", output.getvalue())
        self.assertIn("Wrote devcontainer JSON.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
