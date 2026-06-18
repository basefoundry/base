from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine
from base_projects.workspace_pull import MAX_WORKSPACE_MANIFEST_SOURCE_BYTES


WORKSPACE_MANIFEST = """\
schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
    url: git@github.com:codeforester/base.git
"""


def invoke_engine(
    args: list[str],
    base_home: Path,
    home: Path,
    user_config: str | None = None,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    if user_config is not None:
        config_path = home / ".base.d" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(user_config, encoding="utf-8")
    env = {
        "HOME": str(home),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_MANIFEST": "",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class WorkspacePullTests(unittest.TestCase):
    def test_workspace_pull_dry_run_reports_source_target_and_change_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            source = root / "canonical.yaml"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            source.write_text(WORKSPACE_MANIFEST, encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["pull", "--dry-run"],
                base_home,
                home,
                user_config=(
                    "workspace:\n"
                    f"  manifest: {target}\n"
                    f"  manifest_source: {source}\n"
                ),
            )
            target_exists = target.exists()

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertFalse(target_exists)
        self.assertIn("Workspace manifest pull", stdout)
        self.assertIn(f"Source: {source}", stdout)
        self.assertIn(f"Target: {target.resolve(strict=False)}", stdout)
        self.assertIn("Manifest: demo-suite (1 repositories)", stdout)
        self.assertIn("Status: would create", stdout)
        self.assertIn("[DRY-RUN] No files changed.", stdout)

    def test_workspace_pull_writes_valid_manifest_from_configured_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            source = root / "canonical.yaml"
            target = root / "manifests" / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            source.write_text(WORKSPACE_MANIFEST, encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["pull"],
                base_home,
                home,
                user_config=(
                    "workspace:\n"
                    f"  manifest: {target}\n"
                    f"  manifest_source: {source}\n"
                ),
            )
            target_content = target.read_text(encoding="utf-8") if target.exists() else ""

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(target_content, WORKSPACE_MANIFEST)
        self.assertIn("Status: created", stdout)
        self.assertIn(f"Updated workspace manifest: {target.resolve(strict=False)}", stdout)

    def test_workspace_pull_accepts_explicit_source_and_manifest_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            configured_source = root / "configured.yaml"
            cli_source = root / "cli.yaml"
            configured_target = root / "configured-target.yaml"
            cli_target = root / "cli-target.yaml"
            home.mkdir()
            base_home.mkdir()
            configured_source.write_text("not yaml: [", encoding="utf-8")
            cli_source.write_text(WORKSPACE_MANIFEST, encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                [
                    "pull",
                    "--source",
                    str(cli_source),
                    "--manifest",
                    str(cli_target),
                ],
                base_home,
                home,
                user_config=(
                    "workspace:\n"
                    f"  manifest: {configured_target}\n"
                    f"  manifest_source: {configured_source}\n"
                ),
            )
            cli_target_content = cli_target.read_text(encoding="utf-8") if cli_target.exists() else ""
            configured_target_exists = configured_target.exists()

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertFalse(configured_target_exists)
        self.assertEqual(cli_target_content, WORKSPACE_MANIFEST)
        self.assertIn(f"Source: {cli_source}", stdout)
        self.assertIn(f"Target: {cli_target.resolve(strict=False)}", stdout)

    def test_workspace_pull_accepts_file_url_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            source = root / "canonical.yaml"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            source.write_text(WORKSPACE_MANIFEST, encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["pull", "--source", source.as_uri(), "--manifest", str(target)],
                base_home,
                home,
            )
            target_content = target.read_text(encoding="utf-8") if target.exists() else ""

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(target_content, WORKSPACE_MANIFEST)
        self.assertIn(f"Source: {source.as_uri()}", stdout)
        self.assertIn("Status: created", stdout)

    def test_workspace_pull_rejects_cleartext_http_source_before_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()

            with mock.patch("base_projects.workspace_pull.urlopen") as urlopen:
                status, stdout, stderr = invoke_engine(
                    ["pull", "--source", "http://example.test/workspace.yaml", "--manifest", str(target)],
                    base_home,
                    home,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertFalse(target.exists())
        urlopen.assert_not_called()
        self.assertIn("Insecure workspace manifest source", stderr)
        self.assertIn("Use https://, file://, or a local path", stderr)

    def test_workspace_pull_accepts_https_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()

            response = mock.MagicMock()
            response.read.return_value = WORKSPACE_MANIFEST.encode("utf-8")
            response.__enter__.return_value = response
            with mock.patch("base_projects.workspace_pull.urlopen", return_value=response) as urlopen:
                status, stdout, stderr = invoke_engine(
                    ["pull", "--source", "https://example.test/workspace.yaml", "--manifest", str(target)],
                    base_home,
                    home,
                )
            target_content = target.read_text(encoding="utf-8") if target.exists() else ""

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(target_content, WORKSPACE_MANIFEST)
        urlopen.assert_called_once_with("https://example.test/workspace.yaml", timeout=30)
        self.assertIn("Status: created", stdout)

    def test_workspace_pull_rejects_invalid_manifest_without_overwriting_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            source = root / "bad.yaml"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            source.write_text("schema_version: 99\nworkspace:\n  name: demo\nrepos: []\n", encoding="utf-8")
            target.write_text(WORKSPACE_MANIFEST, encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["pull"],
                base_home,
                home,
                user_config=(
                    "workspace:\n"
                    f"  manifest: {target}\n"
                    f"  manifest_source: {source}\n"
                ),
            )
            target_content = target.read_text(encoding="utf-8")

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(target_content, WORKSPACE_MANIFEST)
        self.assertIn("Fetched workspace manifest from", stderr)
        self.assertIn("newer than supported schema version 1", stderr)

    def test_workspace_pull_rejects_oversized_manifest_without_overwriting_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            source = root / "large.yaml"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            source.write_bytes(b"x" * (MAX_WORKSPACE_MANIFEST_SOURCE_BYTES + 1))
            target.write_text(WORKSPACE_MANIFEST, encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                ["pull", "--source", str(source), "--manifest", str(target)],
                base_home,
                home,
            )
            target_content = target.read_text(encoding="utf-8")

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(target_content, WORKSPACE_MANIFEST)
        self.assertIn("exceeds the", stderr)
        self.assertIn("byte limit", stderr)

    def test_workspace_pull_requires_source_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            home.mkdir()
            base_home.mkdir()

            missing_source_status, _stdout, missing_source_stderr = invoke_engine(
                ["pull", "--manifest", str(root / "workspace.yaml")],
                base_home,
                home,
            )
            missing_target_status, _stdout, missing_target_stderr = invoke_engine(
                ["pull", "--source", str(root / "canonical.yaml")],
                base_home,
                home,
            )

        self.assertEqual(missing_source_status, 2)
        self.assertIn("workspace pull requires --source <url-or-path>", missing_source_stderr)
        self.assertEqual(missing_target_status, 2)
        self.assertIn("workspace pull requires --manifest <path>", missing_target_stderr)

    def test_workspace_pull_reports_unavailable_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            missing_source = root / "missing.yaml"
            target = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()

            status, stdout, stderr = invoke_engine(
                ["pull", "--source", str(missing_source), "--manifest", str(target)],
                base_home,
                home,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Unable to fetch workspace manifest source", stderr)
