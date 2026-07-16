from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from base_cli.command_protocol import loads_records
from base_setup.manifest import read_manifest
from base_setup.project_routing import manifest_requires_project_python
from base_setup.tests.helpers import run_engine


def write_manifest(root: Path, content: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "base_manifest.yaml"
    manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


class ProjectRoutingTests(unittest.TestCase):
    def test_manifest_requires_project_python_only_for_explicit_python_contracts(self) -> None:
        cases = (
            ("project:\n  name: shell-only\nartifacts: []\n", False),
            ("project:\n  name: taxonomy-only\n  languages: [python]\nartifacts: []\n", False),
            ("project:\n  name: explicit-empty\npython: {}\nartifacts: []\n", True),
            (
                "project:\n  name: packages\nartifacts:\n"
                "  - type: python-package\n    name: requests\n    version: latest\n",
                True,
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for index, (content, expected) in enumerate(cases):
                with self.subTest(content=content):
                    manifest = read_manifest(write_manifest(root / str(index), content))
                    self.assertEqual(manifest_requires_project_python(manifest), expected)

    def test_route_command_protocol_reports_explicit_route_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo λ"
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
                ["--manifest", str(manifest_path), "--action", "route", "--format", "command-protocol", "demo"]
            )

        self.assertEqual((status, stderr), (0, ""))
        _, records = loads_records(stdout, "project-route")
        self.assertEqual(records[0]["project_name"], "demo")
        self.assertEqual(records[0]["project_root"], str(root.resolve()))
        self.assertEqual(records[0]["project_venv_dir"], str(root.resolve() / ".venv"))
        self.assertTrue(records[0]["uses_uv_manager"])
        self.assertTrue(records[0]["requires_project_python"])
        self.assertFalse(records[0]["manifest_command_trust_required"])

    def test_route_ignores_different_active_project_venv_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            active_venv = Path(tmpdir) / "base" / ".venv"
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
                ["--manifest", str(manifest_path), "--action", "route", "--format", "json", "demo"],
                extra_env={"BASE_PROJECT": "base", "BASE_PROJECT_VENV_DIR": str(active_venv)},
            )

        self.assertEqual(status, 0, stderr)
        route = json.loads(stdout)
        self.assertEqual(route["project_venv_dir"], str(root.resolve() / ".venv"))
        self.assertNotEqual(route["project_venv_dir"], str(active_venv))

    def test_route_honors_same_project_venv_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            override_venv = Path(tmpdir) / "custom-venv"
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
                ["--manifest", str(manifest_path), "--action", "route", "--format", "json", "demo"],
                extra_env={"BASE_PROJECT": "demo", "BASE_PROJECT_VENV_DIR": str(override_venv)},
            )

        self.assertEqual(status, 0, stderr)
        route = json.loads(stdout)
        self.assertEqual(route["project_venv_dir"], str(override_venv))

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
        self.assertTrue(route["requires_project_python"])

    def test_route_json_reports_project_local_venv_by_default(self) -> None:
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
        self.assertEqual(route["project_venv_dir"], str(root.resolve() / ".venv"))
        self.assertFalse(route["uses_uv_manager"])
        self.assertFalse(route["requires_project_python"])

    def test_route_json_preserves_external_project_venv_when_manifest_opts_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            manifest_path = write_manifest(
                root,
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "python:",
                        "  venv_location: external",
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
                    "true",
                ]
            )
            + "\n",
        )
