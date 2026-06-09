from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from base_release.engine import ReleaseFinding
from base_release.engine import main


@contextmanager
def pushd(path: Path):
    old_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def run_engine(args: list[str], cwd: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(
            os.environ,
            {"BASE_HOME": str(Path(__file__).resolve().parents[4]), "HOME": home_dir},
        ):
            with pushd(cwd), redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def write_release_project(
    root: Path,
    *,
    version_file_content: str = "1.2.3\n",
    changelog: str | None = None,
    homebrew: bool = True,
) -> Path:
    changelog_content = changelog or "\n".join(
        [
            "# Changelog",
            "",
            "## [Unreleased]",
            "",
            "## [1.2.3] - 2026-06-09",
            "",
            "- Added the release assistant.",
            "",
            "## [1.2.2] - 2026-06-01",
            "",
            "- Previous release.",
        ]
    )
    root.joinpath("VERSION").write_text(version_file_content, encoding="utf-8")
    root.joinpath("CHANGELOG.md").write_text(changelog_content, encoding="utf-8")
    manifest_lines = [
        "project:",
        "  name: demo",
        "",
        "release:",
        "  version_file: VERSION",
        "  changelog: CHANGELOG.md",
        "  tag_prefix: v",
        "  github:",
        "    repository: codeforester/demo",
        "    release_title: \"Demo v{version}\"",
    ]
    if homebrew:
        manifest_lines.extend(
            [
                "  homebrew:",
                "    required: true",
                "    tap_repository: codeforester/homebrew-demo",
                "    formula_path: Formula/demo.rb",
                "    package: codeforester/demo/demo",
            ]
        )
    manifest_lines.extend(["", "artifacts: []"])
    manifest_path = root / "base_manifest.yaml"
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "base@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Base Tests"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    return manifest_path


def add_origin(root: Path) -> None:
    remote_path = root.parent / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote_path)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "remote", "add", "origin", str(remote_path)], cwd=root, check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=root, check=True, stdout=subprocess.DEVNULL)


def add_origin_with_remote_tag(root: Path, tag_name: str) -> None:
    add_origin(root)
    subprocess.run(["git", "tag", tag_name], cwd=root, check=True)
    subprocess.run(["git", "push", "origin", tag_name], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "tag", "-d", tag_name], cwd=root, check=True, stdout=subprocess.DEVNULL)


class ReleaseEngineTests(unittest.TestCase):

    def test_notes_prints_changelog_section_for_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)

            status, stdout, stderr = run_engine(
                ["notes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                root,
            )

        self.assertEqual(status, 0, stderr)
        self.assertIn("Added the release assistant.", stdout)
        self.assertNotIn("Previous release.", stdout)


    def test_plan_prints_github_and_homebrew_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)

            status, stdout, stderr = run_engine(
                ["plan", "--version", "1.2.3", "--manifest", str(manifest_path)],
                root,
            )

        self.assertEqual(status, 0, stderr)
        self.assertIn("Release plan for demo v1.2.3", stdout)
        self.assertIn("Tag: v1.2.3", stdout)
        self.assertIn("GitHub repository: codeforester/demo", stdout)
        self.assertIn("GitHub release title: Demo v1.2.3", stdout)
        self.assertIn("Homebrew handoff required", stdout)
        self.assertIn("Tap repository: codeforester/homebrew-demo", stdout)
        self.assertIn("Formula path: Formula/demo.rb", stdout)
        self.assertIn("Package: codeforester/demo/demo", stdout)
        self.assertIn(
            "curl -fsSL https://github.com/codeforester/demo/archive/refs/tags/v1.2.3.tar.gz | shasum -a 256",
            stdout,
        )


    def test_check_fails_when_version_file_does_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root, version_file_content="1.2.2\n")

            status, stdout, stderr = run_engine(
                ["check", "--version", "1.2.3", "--manifest", str(manifest_path)],
                root,
            )

        self.assertEqual(status, 1)
        self.assertIn("VERSION contains 1.2.2, expected 1.2.3", stdout)
        self.assertEqual(stderr, "")


    def test_check_fails_when_changelog_section_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(
                root,
                changelog="# Changelog\n\n## [1.2.2] - 2026-06-01\n\n- Previous release.\n",
            )

            status, stdout, stderr = run_engine(
                ["check", "--version", "1.2.3", "--manifest", str(manifest_path)],
                root,
            )

        self.assertEqual(status, 1)
        self.assertIn("CHANGELOG.md has no section for 1.2.3", stdout)
        self.assertEqual(stderr, "")


    def test_check_passes_for_clean_release_ready_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            root.mkdir()
            manifest_path = write_release_project(root)
            add_origin(root)

            with mock.patch(
                "base_release.engine.gh_cli_finding",
                return_value=ReleaseFinding("ok", "gh", "GitHub CLI is authenticated for github.com."),
            ):
                status, stdout, stderr = run_engine(
                    ["check", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stdout + stderr)
        self.assertIn("Git worktree is clean.", stdout)
        self.assertIn("Local tag v1.2.3 is available.", stdout)
        self.assertIn("Remote tag v1.2.3 is available on origin.", stdout)
        self.assertEqual(stderr, "")


    def test_check_fails_when_worktree_is_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            root.mkdir()
            manifest_path = write_release_project(root)
            add_origin(root)
            root.joinpath("scratch.txt").write_text("dirty\n", encoding="utf-8")

            with mock.patch(
                "base_release.engine.gh_cli_finding",
                return_value=ReleaseFinding("ok", "gh", "GitHub CLI is authenticated for github.com."),
            ):
                status, stdout, stderr = run_engine(
                    ["check", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertIn("Git worktree has tracked or untracked changes.", stdout)
        self.assertEqual(stderr, "")


    def test_check_fails_when_local_tag_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            root.mkdir()
            manifest_path = write_release_project(root)
            add_origin(root)
            subprocess.run(["git", "tag", "v1.2.3"], cwd=root, check=True)

            with mock.patch(
                "base_release.engine.gh_cli_finding",
                return_value=ReleaseFinding("ok", "gh", "GitHub CLI is authenticated for github.com."),
            ):
                status, stdout, stderr = run_engine(
                    ["check", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertIn("Local tag v1.2.3 already exists.", stdout)
        self.assertEqual(stderr, "")


    def test_check_fails_when_remote_tag_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            root.mkdir()
            manifest_path = write_release_project(root)
            add_origin_with_remote_tag(root, "v1.2.3")

            with mock.patch(
                "base_release.engine.gh_cli_finding",
                return_value=ReleaseFinding("ok", "gh", "GitHub CLI is authenticated for github.com."),
            ):
                status, stdout, stderr = run_engine(
                    ["check", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertIn("Remote tag v1.2.3 already exists on origin.", stdout)
        self.assertEqual(stderr, "")
