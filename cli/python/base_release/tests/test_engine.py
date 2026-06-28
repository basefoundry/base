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

from base_release import engine
from base_release.engine import ReleaseError
from base_release.engine import ReleaseFinding
from base_release.engine import main


READY_FINDINGS = (
    ReleaseFinding("ok", "manifest", "Release metadata found."),
    ReleaseFinding("ok", "version_file", "VERSION matches."),
    ReleaseFinding("ok", "changelog", "CHANGELOG.md has a section."),
    ReleaseFinding("ok", "git", "Git worktree is clean."),
    ReleaseFinding("ok", "branch", "Current branch is main."),
    ReleaseFinding("ok", "gh", "GitHub CLI is authenticated."),
    ReleaseFinding("ok", "local_tag", "Local tag is available."),
    ReleaseFinding("ok", "remote_tag", "Remote tag is available."),
)


@contextmanager
def pushd(path: Path):
    old_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def run_engine(args: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    env = {
        "BASE_CLI_DISPLAY_COMMAND": "",
        "BASE_HOME": str(Path(__file__).resolve().parents[4]),
        "HOME": "",
    }
    if extra_env:
        env.update(extra_env)
    with tempfile.TemporaryDirectory() as home_dir:
        env["HOME"] = home_dir
        with mock.patch.dict(os.environ, env):
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


class ReleaseUsageTests(unittest.TestCase):
    def test_delegated_unknown_option_usage_uses_basectl_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = run_engine(
                ["check", "--wat"],
                Path(tmpdir),
                {"BASE_CLI_DISPLAY_COMMAND": "basectl release"},
            )

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("basectl release check --version <version>", stderr)
        self.assertIn("ERROR: Unknown release check option '--wat'.", stderr)
        self.assertNotIn("base_release", stderr)

    def test_delegated_missing_required_option_usage_uses_basectl_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = run_engine(
                ["check"],
                Path(tmpdir),
                {"BASE_CLI_DISPLAY_COMMAND": "basectl release"},
            )

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("basectl release check --version <version>", stderr)
        self.assertIn("ERROR: The 'release check' command requires --version.", stderr)
        self.assertNotIn("base_release", stderr)


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
        self.assertIn("brew install --build-from-source Formula/demo.rb", stdout)
        self.assertIn("brew test codeforester/demo/demo", stdout)
        self.assertIn("brew audit --new --formula Formula/demo.rb", stdout)
        self.assertIn("brew upgrade codeforester/demo/demo", stdout)


    def test_plan_prints_1_0_homebrew_upgrade_reminder_without_issue_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            changelog = "\n".join(
                [
                    "# Changelog",
                    "",
                    "## [1.0.0] - 2026-06-10",
                    "",
                    "- Stable release.",
                ]
            )
            manifest_path = write_release_project(
                root,
                version_file_content="1.0.0\n",
                changelog=changelog,
            )

            status, stdout, stderr = run_engine(
                ["plan", "--version", "1.0.0", "--manifest", str(manifest_path)],
                root,
            )

        self.assertEqual(status, 0, stderr)
        self.assertIn("1.0 reminder: validate the Homebrew upgrade path before publishing.", stdout)
        self.assertNotIn("#526", stdout)


    def test_plan_prints_no_homebrew_handoff_for_github_only_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root, homebrew=False)

            status, stdout, stderr = run_engine(
                ["plan", "--version", "1.2.3", "--manifest", str(manifest_path)],
                root,
            )

        self.assertEqual(status, 0, stderr)
        self.assertIn("Homebrew handoff: not declared", stdout)
        self.assertNotIn("Homebrew handoff required", stdout)


    def test_publish_dry_run_prints_planned_actions_without_running_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)

            with mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS), mock.patch(
                "base_release.engine.github_release_finding",
                return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                create=True,
            ), mock.patch("base_release.engine.run_release_step", create=True) as run_step:
                status, stdout, stderr = run_engine(
                    ["publish", "--dry-run", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stderr)
        self.assertIn("DRY RUN", stdout)
        self.assertIn("Would create annotated tag: v1.2.3", stdout)
        self.assertIn("Would push tag to origin: v1.2.3", stdout)
        self.assertIn("Would create GitHub Release: Demo v1.2.3", stdout)
        self.assertIn("Homebrew handoff required after GitHub release", stdout)
        run_step.assert_not_called()

    def test_run_release_step_uses_bounded_timeout(self) -> None:
        completed = subprocess.CompletedProcess(["git", "tag"], 0, stdout="")

        with mock.patch("base_release.engine.subprocess.run", return_value=completed) as run:
            engine.run_release_step(["git", "tag"], cwd=Path("/repo"))

        self.assertEqual(run.call_args.kwargs["timeout"], engine.RELEASE_STEP_TIMEOUT_SECONDS)

    def test_run_release_step_reports_timeout_as_release_error(self) -> None:
        command = ["git", "push", "origin", "v1.2.3"]

        with mock.patch(
            "base_release.engine.subprocess.run",
            side_effect=subprocess.TimeoutExpired(command, timeout=30),
        ):
            with self.assertRaisesRegex(ReleaseError, "timed out"):
                engine.run_release_step(command)

    def test_run_release_step_reports_os_error_as_release_error(self) -> None:
        command = ["gh", "release", "create", "v1.2.3"]

        with mock.patch("base_release.engine.subprocess.run", side_effect=OSError("network unavailable")):
            with self.assertRaisesRegex(ReleaseError, "Unable to run release command"):
                engine.run_release_step(command)


    def test_publish_requires_yes_when_stdin_is_not_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)

            with mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS), mock.patch(
                "base_release.engine.github_release_finding",
                return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                create=True,
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("release publish requires --yes when stdin is not interactive", stderr)


    def test_publish_yes_creates_annotated_tag_pushes_and_creates_github_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)
            commands: list[tuple[list[str], Path | None]] = []

            def fake_run_release_step(command: list[str], *, cwd: Path | None = None) -> None:
                if command[:3] == ["gh", "release", "create"]:
                    notes_path = Path(command[-1])
                    self.assertIn("Added the release assistant.", notes_path.read_text(encoding="utf-8"))
                commands.append((command, cwd))

            with mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS), mock.patch(
                "base_release.engine.github_release_finding",
                return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                create=True,
            ), mock.patch(
                "base_release.engine.run_release_step",
                side_effect=fake_run_release_step,
                create=True,
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stderr)
        self.assertEqual(commands[0][0], ["git", "tag", "-a", "v1.2.3", "-m", "Release v1.2.3"])
        self.assertEqual(commands[0][1], root.resolve())
        self.assertEqual(commands[1][0], ["git", "push", "origin", "v1.2.3"])
        self.assertEqual(commands[1][1], root.resolve())
        self.assertEqual(
            commands[2][0][:7],
            ["gh", "release", "create", "v1.2.3", "--repo", "codeforester/demo", "--title"],
        )
        self.assertEqual(
            commands[2][1],
            root.resolve(),
        )
        self.assertIn("GitHub Release published: https://github.com/codeforester/demo/releases/tag/v1.2.3", stdout)
        self.assertIn("Tag URL: https://github.com/codeforester/demo/tree/v1.2.3", stdout)
        self.assertIn("Homebrew handoff required after GitHub release", stdout)


    def test_publish_yes_reports_recovery_when_github_release_create_fails_after_tag_push(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)
            commands: list[tuple[list[str], Path | None]] = []

            def fake_run_release_step(command: list[str], *, cwd: Path | None = None) -> None:
                commands.append((command, cwd))
                if command[:3] == ["gh", "release", "create"]:
                    raise ReleaseError("Release command failed: gh release create v1.2.3: network unavailable")

            with mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS), mock.patch(
                "base_release.engine.github_release_finding",
                return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                create=True,
            ), mock.patch(
                "base_release.engine.run_release_step",
                side_effect=fake_run_release_step,
                create=True,
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(commands[0][0], ["git", "tag", "-a", "v1.2.3", "-m", "Release v1.2.3"])
        self.assertEqual(commands[1][0], ["git", "push", "origin", "v1.2.3"])
        self.assertIn("Release command failed: gh release create v1.2.3: network unavailable", stderr)
        self.assertIn("Release publish already created and pushed tag v1.2.3", stderr)
        self.assertIn("basectl release notes --version 1.2.3", stderr)
        self.assertIn("gh release create v1.2.3 --repo codeforester/demo", stderr)
        self.assertIn("git push origin :refs/tags/v1.2.3", stderr)


    def test_publish_fails_when_readiness_has_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)

            with mock.patch(
                "base_release.engine.release_findings",
                return_value=(ReleaseFinding("error", "git", "Git worktree has tracked or untracked changes."),),
            ), mock.patch("base_release.engine.run_release_step", create=True) as run_step:
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertIn("Release publish blocked by readiness findings", stdout)
        self.assertIn("error  git", stdout)
        self.assertEqual(stderr, "")
        run_step.assert_not_called()


    def test_publish_fails_when_github_release_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = write_release_project(root)

            with mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS), mock.patch(
                "base_release.engine.github_release_finding",
                return_value=ReleaseFinding(
                    "error",
                    "github_release",
                    "GitHub Release v1.2.3 already exists.",
                ),
                create=True,
            ), mock.patch("base_release.engine.run_release_step", create=True) as run_step:
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertIn("Release publish blocked by readiness findings", stdout)
        self.assertIn("GitHub Release v1.2.3 already exists.", stdout)
        self.assertEqual(stderr, "")
        run_step.assert_not_called()


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
