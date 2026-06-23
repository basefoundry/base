from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from base_setup.tests.helpers import run_engine


def write_manifest(root: Path, content: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "base_manifest.yaml"
    manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


class ProjectRoutingTests(unittest.TestCase):
    def test_route_json_reports_uv_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            manifest_path = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts: []",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "route", "--format", "json", "demo"]
            )

        self.assertEqual(status, 0, stderr)
        route = json.loads(stdout)
        self.assertEqual(route["schema_version"], 1)
        self.assertEqual(route["project"], "demo")
        self.assertEqual(route["project_root"], str(root.resolve()))
        self.assertEqual(route["manifest_path"], str(manifest_path.resolve()))
        self.assertEqual(route["project_venv_dir"], str(root.resolve() / ".venv"))
        self.assertTrue(route["uses_uv_manager"])

    def test_route_json_reports_base_managed_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            manifest_path = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "artifacts: []",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(
                ["--manifest", str(manifest_path), "--action", "route", "--format", "json", "demo"]
            )

        self.assertEqual(status, 0, stderr)
        route = json.loads(stdout)
        self.assertTrue(route["project_venv_dir"].endswith("/.base.d/demo/.venv"))
        self.assertNotEqual(route["project_venv_dir"], str(root.resolve() / ".venv"))
        self.assertFalse(route["uses_uv_manager"])

    def test_route_text_emits_shell_friendly_tsv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            manifest_path = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  manager: uv",
                        "artifacts: []",
                    ]
                ),
            )

            status, stdout, stderr = run_engine(["--manifest", str(manifest_path), "--action", "route", "demo"])

        self.assertEqual(status, 0, stderr)
        self.assertEqual(
            stdout,
            "\t".join(
                [
                    "demo",
                    str(root.resolve()),
                    str(manifest_path.resolve()),
                    str(root.resolve() / ".venv"),
                    "true",
                ]
            )
            + "\n",
        )
