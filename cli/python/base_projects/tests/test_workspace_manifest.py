from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_projects.workspace_manifest import WorkspaceManifestError, read_workspace_manifest


def write_workspace_manifest(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


class WorkspaceManifestParserTests(unittest.TestCase):
    def test_reads_workspace_manifest_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo-workspace
repos:
  - name: base
    url: git@github.com:codeforester/base.git
    default_branch: master
  - name: optional-tool
    required: false
""",
            )

            manifest = read_workspace_manifest(path)

        self.assertEqual(manifest.path, path.resolve())
        self.assertEqual(manifest.schema_version, 1)
        self.assertEqual(manifest.name, "demo-workspace")
        self.assertEqual([repo.name for repo in manifest.repos], ["base", "optional-tool"])
        self.assertTrue(manifest.repos[0].required)
        self.assertEqual(manifest.repos[0].url, "git@github.com:codeforester/base.git")
        self.assertEqual(manifest.repos[0].default_branch, "master")
        self.assertFalse(manifest.repos[1].required)
        self.assertIsNone(manifest.repos[1].url)

    def test_accepts_common_git_url_forms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "workspace.yaml"
            local_repo = root / "local-repo"
            write_workspace_manifest(
                path,
                f"""
schema_version: 1
workspace:
  name: demo-workspace
repos:
  - name: https-repo
    url: https://github.com/codeforester/base.git
  - name: ssh-repo
    url: ssh://git@github.com/codeforester/base.git
  - name: git-protocol-repo
    url: git://github.com/codeforester/base.git
  - name: scp-repo
    url: git@github.com:codeforester/base.git
  - name: file-repo
    url: file:///opt/repos/base.git
  - name: local-repo
    url: {local_repo}
""",
            )

            manifest = read_workspace_manifest(path)

        self.assertEqual(
            [repo.url for repo in manifest.repos],
            [
                "https://github.com/codeforester/base.git",
                "ssh://git@github.com/codeforester/base.git",
                "git://github.com/codeforester/base.git",
                "git@github.com:codeforester/base.git",
                "file:///opt/repos/base.git",
                str(local_repo),
            ],
        )

    def test_rejects_cleartext_http_repo_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo-workspace
repos:
  - name: base
    url: http://github.com/codeforester/base.git
""",
            )

            with self.assertRaisesRegex(
                WorkspaceManifestError,
                "repos\\[1\\]\\.url uses insecure cleartext HTTP",
            ):
                read_workspace_manifest(path)

    def test_rejects_repo_url_without_git_url_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo-workspace
repos:
  - name: base
    url: github.com/codeforester/base.git
""",
            )

            with self.assertRaisesRegex(
                WorkspaceManifestError,
                "repos\\[1\\]\\.url does not look like a Git URL or local path",
            ):
                read_workspace_manifest(path)

    def test_requires_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(path, "workspace:\n  name: demo\nrepos: []\n")

            with self.assertRaisesRegex(WorkspaceManifestError, "schema_version is required"):
                read_workspace_manifest(path)

    def test_rejects_newer_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(path, "schema_version: 99\nworkspace:\n  name: demo\nrepos: []\n")

            with self.assertRaisesRegex(WorkspaceManifestError, "newer than supported schema version 1"):
                read_workspace_manifest(path)

    def test_requires_workspace_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(path, "schema_version: 1\nworkspace: {}\nrepos: []\n")

            with self.assertRaisesRegex(WorkspaceManifestError, "workspace.name is required"):
                read_workspace_manifest(path)

    def test_rejects_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo
repos: []
clone: true
""",
            )

            with self.assertRaisesRegex(WorkspaceManifestError, "unsupported top-level keys: clone"):
                read_workspace_manifest(path)

    def test_rejects_duplicate_repo_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo
repos:
  - name: base
  - name: base
""",
            )

            with self.assertRaisesRegex(WorkspaceManifestError, "duplicate repo names: base"):
                read_workspace_manifest(path)

    def test_rejects_repo_names_that_are_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo
repos:
  - name: nested/base
""",
            )

            with self.assertRaisesRegex(WorkspaceManifestError, "repos\\[1\\].name must be a directory name"):
                read_workspace_manifest(path)

    def test_rejects_non_boolean_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            write_workspace_manifest(
                path,
                """
schema_version: 1
workspace:
  name: demo
repos:
  - name: base
    required: "yes"
""",
            )

            with self.assertRaisesRegex(WorkspaceManifestError, "repos\\[1\\].required must be a boolean"):
                read_workspace_manifest(path)
