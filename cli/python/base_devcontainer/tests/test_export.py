from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from base_devcontainer.export import build_devcontainer_export
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


if __name__ == "__main__":
    unittest.main()
