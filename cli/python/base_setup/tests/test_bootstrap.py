from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import engine
from base_setup.artifacts import merge_artifacts
from base_setup.manifest import ArtifactRequest, BaseManifest, ManifestError, read_manifest
from base_setup.tests.helpers import fake_context

class BootstrapManifestTests(unittest.TestCase):

    def test_reconcile_bootstrap_artifacts_uses_only_bootstrap_defaults(self) -> None:
        ctx = fake_context()
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1", bootstrap=True),
                ArtifactRequest(artifact_type="python-package", name="pytest", version="latest"),
            ),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )

        with mock.patch("base_setup.engine.reconcile_artifacts") as reconcile_artifacts:
            engine.reconcile_bootstrap_artifacts(ctx, default_manifest, manifest, dry_run=True)

        reconcile_artifacts.assert_called_once()
        self.assertEqual(reconcile_artifacts.call_args.args[1][0].name, "click")
        self.assertEqual(reconcile_artifacts.call_args.args[3], "demo")



    def test_merge_artifacts_preserves_default_bootstrap_marker(self) -> None:
        merged = merge_artifacts(
            (
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1", bootstrap=True),
            ),
            (
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1"),
            ),
        )

        self.assertTrue(merged[0].bootstrap)



    def test_reads_bootstrap_artifact_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: python-package",
                        "    name: click",
                        "    version: \"8.4.1\"",
                        "    bootstrap: true",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertTrue(manifest.artifacts[0].bootstrap)



    def test_rejects_non_boolean_bootstrap_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: python-package",
                        "    name: click",
                        "    version: \"8.4.1\"",
                        "    bootstrap: \"yes\"",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "bootstrap must be a boolean"):
                read_manifest(manifest_path)



    def test_default_manifest_marks_python_bootstrap_packages(self) -> None:
        manifest = read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "default_manifest.yaml")
        bootstrap_artifacts = {
            (artifact.artifact_type, artifact.name): artifact.bootstrap for artifact in manifest.artifacts
        }

        self.assertEqual(
            bootstrap_artifacts,
            {
                ("python-package", "click"): True,
                ("python-package", "PyYAML"): True,
            },
        )
