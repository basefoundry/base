from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_repo_inspection import inspect_workspace_repo


def write_manifest(root: Path, name: str) -> None:
    root.mkdir(parents=True)
    (root / "base_manifest.yaml").write_text(
        f"schema_version: 1\nproject:\n  name: {name}\n",
        encoding="utf-8",
    )


class WorkspaceRepoInspectionTests(unittest.TestCase):
    def test_inspection_reports_each_repository_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            outside = root / "outside"
            workspace.mkdir()
            outside.mkdir()
            (workspace / "outside").symlink_to(outside, target_is_directory=True)
            (workspace / "missing-manifest").mkdir()
            (workspace / "invalid").mkdir()
            (workspace / "invalid" / "base_manifest.yaml").write_text("invalid: true\n", encoding="utf-8")
            write_manifest(workspace / "ready", "ready")

            cases = {
                "outside": ("outside_workspace", True),
                "missing": ("missing_repository", True),
                "missing-manifest": ("missing_manifest", False),
                "invalid": ("invalid_manifest", True),
                "ready": ("inspected", False),
            }
            for name, (state, fatal) in cases.items():
                with self.subTest(name=name):
                    inspection = inspect_workspace_repo(workspace, WorkspaceManifestRepo(name=name))
                    self.assertEqual(inspection.state, state)
                    self.assertEqual(inspection.fatal, fatal)

            skipped = inspect_workspace_repo(
                workspace,
                WorkspaceManifestRepo(name="ready"),
                parse_manifest=False,
            )
            self.assertEqual(skipped.state, "inspected")
            self.assertIsNone(skipped.manifest)
            self.assertEqual(skipped.manifest_path, (workspace / "ready" / "base_manifest.yaml").resolve())
