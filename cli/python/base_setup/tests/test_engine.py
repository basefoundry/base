from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from base_setup.engine import main
from base_setup.manifest import read_manifest


class ManifestTests(unittest.TestCase):
    def test_reads_basic_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: \"1.8.5\"",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.project_name, "demo")
        self.assertEqual(manifest.artifacts[0].artifact_type, "tool")
        self.assertEqual(manifest.artifacts[0].name, "terraform")
        self.assertEqual(manifest.artifacts[0].version, "1.8.5")

    def test_unknown_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: not-a-real-artifact",
                        "    version: \"1.0\"",
                    ]
                ),
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                status = main(["--manifest", str(manifest_path)])

        self.assertEqual(status, 1)
        self.assertIn("Unsupported artifact 'not-a-real-artifact' of type 'tool'", stderr.getvalue())

    def test_known_homebrew_artifact_dry_run_does_not_require_brew(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: \"1.8.5\"",
                    ]
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                status = main(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install terraform", stdout.getvalue())

    def test_project_argument_validates_manifest_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                    ]
                ),
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                status = main(["--manifest", str(manifest_path), "other"])

        self.assertEqual(status, 1)
        self.assertIn("project.name is 'demo', expected 'other'", stderr.getvalue())

    def test_empty_artifact_list_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.project_name, "demo")
        self.assertEqual(manifest.artifacts, ())

    def test_empty_artifact_list_logs_that_no_artifacts_are_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                status = main(["--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("Project 'demo' declares no artifacts.", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
