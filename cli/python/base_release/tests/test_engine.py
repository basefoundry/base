from __future__ import annotations

# Keep the release engine's end-to-end matrix together for readable workflow coverage.
# pylint: disable=too-many-lines

import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

from base_cli_adapters.history import build_finished_record
from base_release import release_publish
from base_release import release_readiness
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
READY_SHA = "a" * 40
READY_PROVENANCE_FINDINGS = (
    ReleaseFinding("ok", "origin_repository", "Origin repository matches."),
    ReleaseFinding("ok", "default_branch", "Current branch is main."),
    ReleaseFinding("ok", "release_commit", f"Release commit is {READY_SHA}."),
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
    stdout = TerminalStringIO()
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


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


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
    def test_json_usage_error_stays_structured_after_later_invalid_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = run_engine(
                ["check", "--format", "json", "--format", "xml"],
                Path(tmpdir),
                {"BASE_CLI_DISPLAY_COMMAND": "basectl release"},
            )

        self.assertEqual(status, 2)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["command"], "release check")
        self.assertEqual(payload["error"]["type"], "usage_error")

    def test_json_usage_error_uses_inspection_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status, stdout, stderr = run_engine(
                ["check", "--format", "json", "--wat"],
                Path(tmpdir),
                {"BASE_CLI_DISPLAY_COMMAND": "basectl release"},
            )

        self.assertEqual(status, 2)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "release check")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["data"], {})
        self.assertEqual(payload["error"]["type"], "usage_error")
        self.assertIn("Unknown release check option '--wat'", payload["error"]["message"])

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


class ReleaseEngineTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    manifest_factory: Any

    def test_explicit_manifest_populates_history_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            manifest_path = self.manifest_factory.write_release(project_root)
            outside = root / "outside"
            outside.mkdir()
            captured: list[tuple[object, ...]] = []

            with (
                mock.patch("base_cli.app.current_working_dir", return_value=outside),
                mock.patch(
                    "base_cli_profile.write_finished_record",
                    side_effect=lambda *args: captured.append(args),
                ),
            ):
                status, _stdout, stderr = run_engine(
                    ["notes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    outside,
                )

            self.assertEqual((status, stderr), (0, ""))
            self.assertEqual(len(captured), 1)
            record = build_finished_record(*captured[0])

        self.assertEqual(record["project"], "demo")
        self.assertEqual(record["project_root"], str(project_root.resolve()))
        self.assertEqual(record["manifest"], str(manifest_path.resolve()))

    def test_check_json_reports_ready_findings_with_stable_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

            with mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS):
                status, stdout, stderr = run_engine(
                    ["check", "--format", "json", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stderr)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(
            list(payload),
            ["schema_version", "command", "status", "data", "error"],
        )
        self.assertEqual(payload["command"], "release check")
        self.assertEqual(payload["status"], "ok")
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["data"]["project"], "demo")
        self.assertEqual(payload["data"]["version"], "1.2.3")
        self.assertEqual(payload["data"]["tag_name"], "v1.2.3")
        self.assertEqual(payload["data"]["findings"][0]["name"], "manifest")
        self.assertEqual(
            set(payload["data"]),
            {"project", "version", "tag_name", "manifest_path", "findings"},
        )
        self.assertEqual(
            set(payload["data"]["findings"][0]),
            {"status", "name", "message"},
        )

    def test_check_json_finding_is_error_with_null_execution_error(self) -> None:
        findings = (
            ReleaseFinding("ok", "manifest", "Release metadata found."),
            ReleaseFinding("error", "gh", "GitHub CLI auth check failed: upstream unavailable."),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

            with mock.patch("base_release.engine.release_findings", return_value=findings):
                status, stdout, stderr = run_engine(
                    ["check", "--format", "json", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "error")
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["data"]["findings"][1]["status"], "error")

    def test_check_json_warning_and_empty_findings_preserve_success_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

            with mock.patch(
                "base_release.engine.release_findings",
                return_value=(ReleaseFinding("warn", "branch", "Unable to inspect current Git branch."),),
            ):
                status, stdout, stderr = run_engine(
                    ["check", "--format", "json", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

            self.assertEqual(status, 0, stderr)
            self.assertEqual(json.loads(stdout)["status"], "warn")

            with mock.patch("base_release.engine.release_findings", return_value=()):
                status, stdout, stderr = run_engine(
                    ["check", "--format", "json", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data"]["findings"], [])

    def test_check_json_controlled_manifest_failure_has_error_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            status, stdout, stderr = run_engine(
                ["check", "--format", "json", "--version", "1.2.3", "--manifest", str(root / "missing.yaml")],
                root,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["data"], {})
        self.assertEqual(payload["error"]["type"], "execution_error")
        self.assertIn("missing.yaml", payload["error"]["message"])

    def test_notes_prints_changelog_section_for_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

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
            manifest_path = self.manifest_factory.write_release(root)

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
            manifest_path = self.manifest_factory.write_release(
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
            manifest_path = self.manifest_factory.write_release(root, homebrew=False)

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
            manifest_path = self.manifest_factory.write_release(root)

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                    create=True,
                ),
                mock.patch("base_release.engine.require_release_provenance", return_value=READY_SHA),
                mock.patch("base_release.engine.run_release_step", create=True) as run_step,
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--dry-run", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stderr)
        self.assertIn("DRY RUN", stdout)
        self.assertIn(f"Verified reviewed release commit: {READY_SHA}", stdout)
        self.assertIn("Would create annotated tag: v1.2.3", stdout)
        self.assertIn("Would push tag to origin: v1.2.3", stdout)
        self.assertIn("Would create GitHub Release: Demo v1.2.3", stdout)
        self.assertIn("Homebrew handoff required after GitHub release", stdout)
        run_step.assert_not_called()

    def test_publish_requires_yes_when_stdin_is_not_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

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
            manifest_path = self.manifest_factory.write_release(root)
            commands: list[tuple[list[str], Path | None]] = []

            def fake_run_release_step(command: list[str], *, cwd: Path | None = None) -> None:
                if command[:3] == ["gh", "release", "create"]:
                    notes_path = Path(command[-1])
                    self.assertIn("Added the release assistant.", notes_path.read_text(encoding="utf-8"))
                commands.append((command, cwd))

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                    create=True,
                ),
                mock.patch("base_release.engine.require_release_provenance", return_value=READY_SHA),
                mock.patch("base_release.engine.verify_local_annotated_tag") as verify_local,
                mock.patch("base_release.engine.verify_remote_annotated_tag") as verify_remote,
                mock.patch("base_release.engine.verify_github_release") as verify_github,
                mock.patch(
                    "base_release.engine.run_release_step",
                    side_effect=fake_run_release_step,
                    create=True,
                ),
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 0, stderr)
        self.assertEqual(
            commands[0][0],
            ["git", "tag", "-a", "v1.2.3", READY_SHA, "-m", "Release v1.2.3"],
        )
        self.assertEqual(commands[0][1], root.resolve())
        self.assertEqual(commands[1][0], ["git", "push", "origin", "v1.2.3"])
        self.assertEqual(commands[1][1], root.resolve())
        self.assertEqual(commands[2][0][:8], [
            "gh", "release", "create", "v1.2.3", "--verify-tag", "--repo", "codeforester/demo", "--title"
        ])
        self.assertEqual(
            commands[2][1],
            root.resolve(),
        )
        self.assertIn("GitHub Release published: https://github.com/codeforester/demo/releases/tag/v1.2.3", stdout)
        self.assertIn("Tag URL: https://github.com/codeforester/demo/tree/v1.2.3", stdout)
        self.assertIn("Homebrew handoff required after GitHub release", stdout)
        self.assertIn(f"Release commit verified: {READY_SHA}", stdout)
        verify_local.assert_called_once_with(root.resolve(), "v1.2.3", READY_SHA)
        verify_remote.assert_called_once_with(root.resolve(), "v1.2.3", READY_SHA)
        verify_github.assert_called_once()


    def test_publish_with_bom_uploads_and_verifies_stable_release_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)
            bom_path = root / "candidate-bom.json"
            bom_bytes = b'{"release":"base-1.9.0"}\n'
            bom_path.write_bytes(bom_bytes)
            commands: list[tuple[list[str], Path | None]] = []
            uploaded_contents: dict[str, bytes] = {}

            def fake_run_release_step(command: list[str], *, cwd: Path | None = None) -> None:
                commands.append((command, cwd))
                if command[:3] == ["gh", "release", "upload"]:
                    uploaded_contents[Path(command[4]).name] = Path(command[4]).read_bytes()
                    uploaded_contents[Path(command[5]).name] = Path(command[5]).read_bytes()

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                    create=True,
                ),
                mock.patch("base_release.engine.require_release_provenance", return_value=READY_SHA),
                mock.patch("base_release.engine.verify_local_annotated_tag"),
                mock.patch("base_release.engine.verify_remote_annotated_tag"),
                mock.patch("base_release.engine.verify_github_release") as verify_github,
                mock.patch(
                    "base_release.engine.run_release_step",
                    side_effect=fake_run_release_step,
                    create=True,
                ),
                mock.patch(
                    "base_release.release_publish.run_release_step",
                    side_effect=fake_run_release_step,
                ),
            ):
                status, stdout, stderr = run_engine(
                    [
                        "publish",
                        "--yes",
                        "--version",
                        "1.2.3",
                        "--manifest",
                        str(manifest_path),
                        "--bom",
                        str(bom_path),
                    ],
                    root,
                )

        self.assertEqual((status, stderr), (0, ""), stdout)
        upload_commands = [command for command, _cwd in commands if command[:3] == ["gh", "release", "upload"]]
        self.assertEqual(len(upload_commands), 1)
        upload_command = upload_commands[0]
        self.assertEqual(upload_command[0:4], ["gh", "release", "upload", "v1.2.3"])
        self.assertEqual(upload_command[6:], ["--repo", "codeforester/demo", "--clobber"])
        self.assertEqual(uploaded_contents["release-bom.json"], bom_bytes)
        self.assertEqual(
            uploaded_contents["release-bom.sha256"].decode(),
            f"{hashlib.sha256(bom_bytes).hexdigest()}  release-bom.json\n",
        )
        verify_github.assert_called_once()
        verify_context, verify_sha = verify_github.call_args.args
        self.assertEqual(verify_context.manifest_path.parent, root.resolve())
        self.assertEqual(verify_sha, READY_SHA)
        self.assertEqual(
            verify_github.call_args.kwargs["expected_assets"],
            ("release-bom.json", "release-bom.sha256"),
        )
        self.assertIn("release-bom.json", stdout)


    def test_publish_yes_reports_recovery_when_github_release_create_fails_after_tag_push(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)
            commands: list[tuple[list[str], Path | None]] = []

            def fake_run_release_step(command: list[str], *, cwd: Path | None = None) -> None:
                commands.append((command, cwd))
                if command[:3] == ["gh", "release", "create"]:
                    raise ReleaseError("Release command failed: gh release create v1.2.3: network unavailable")

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                    create=True,
                ),
                mock.patch("base_release.engine.require_release_provenance", return_value=READY_SHA),
                mock.patch("base_release.engine.verify_local_annotated_tag"),
                mock.patch("base_release.engine.verify_remote_annotated_tag"),
                mock.patch(
                    "base_release.engine.run_release_step",
                    side_effect=fake_run_release_step,
                    create=True,
                ),
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(
            commands[0][0],
            ["git", "tag", "-a", "v1.2.3", READY_SHA, "-m", "Release v1.2.3"],
        )
        self.assertEqual(commands[1][0], ["git", "push", "origin", "v1.2.3"])
        stderr_lines = stderr.splitlines()
        self.assertEqual(
            stderr_lines[0],
            "ERROR: Release command failed: gh release create v1.2.3: network unavailable",
        )
        self.assertIn("Recovery guidance:", stderr_lines)
        self.assertIn("Release publish already created and pushed tag v1.2.3", stderr)
        self.assertIn("basectl release notes --version 1.2.3", stderr)
        self.assertIn("gh release create v1.2.3 --verify-tag --repo codeforester/demo", stderr)
        self.assertIn("git push origin :refs/tags/v1.2.3", stderr)


    def test_publish_push_failure_reports_local_tag_recovery_when_remote_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

            def fail_push(command: list[str], *, cwd: Path | None = None) -> None:
                del cwd
                if command[:3] == ["git", "push", "origin"]:
                    raise ReleaseError("Release command failed: git push origin v1.2.3: network unavailable")

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                    create=True,
                ),
                mock.patch("base_release.engine.require_release_provenance", return_value=READY_SHA),
                mock.patch("base_release.engine.verify_local_annotated_tag"),
                mock.patch("base_release.engine.inspect_remote_annotated_tag", return_value="absent") as inspect,
                mock.patch("base_release.engine.run_release_step", side_effect=fail_push, create=True),
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        inspect.assert_called_once_with(root.resolve(), "v1.2.3", READY_SHA)
        self.assertIn("local annotated tag v1.2.3 remains", stderr)
        self.assertIn("remote tag is absent", stderr)
        self.assertIn("git push origin v1.2.3", stderr)
        self.assertIn("git tag -d v1.2.3", stderr)
        self.assertNotIn("refs/tags/v1.2.3", stderr)


    def test_publish_push_timeout_checks_remote_and_guides_github_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

            def timeout_push(command: list[str], *, cwd: Path | None = None) -> None:
                del cwd
                if command[:3] == ["git", "push", "origin"]:
                    raise ReleaseError("Release command timed out after 120 seconds: git push origin v1.2.3")

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                    create=True,
                ),
                mock.patch("base_release.engine.require_release_provenance", return_value=READY_SHA),
                mock.patch("base_release.engine.verify_local_annotated_tag"),
                mock.patch("base_release.engine.inspect_remote_annotated_tag", return_value="intended") as inspect,
                mock.patch("base_release.engine.run_release_step", side_effect=timeout_push, create=True),
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        inspect.assert_called_once_with(root.resolve(), "v1.2.3", READY_SHA)
        self.assertIn("remote tag v1.2.3 is present and resolves to the intended release commit", stderr)
        self.assertIn("gh release create v1.2.3 --verify-tag --repo codeforester/demo", stderr)


    def test_publish_fails_when_readiness_has_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

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

    def test_publish_rechecks_provenance_before_first_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

            with (
                mock.patch("base_release.engine.release_findings", return_value=READY_FINDINGS),
                mock.patch(
                    "base_release.engine.github_release_finding",
                    return_value=ReleaseFinding("ok", "github_release", "GitHub Release is available."),
                ),
                mock.patch(
                    "base_release.engine.require_release_provenance",
                    side_effect=ReleaseError("Local HEAD changed after readiness."),
                ),
                mock.patch("base_release.engine.run_release_step") as run_step,
            ):
                status, stdout, stderr = run_engine(
                    ["publish", "--yes", "--version", "1.2.3", "--manifest", str(manifest_path)],
                    root,
                )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Local HEAD changed after readiness", stderr)
        run_step.assert_not_called()


    def test_publish_fails_when_github_release_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = self.manifest_factory.write_release(root)

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
            manifest_path = self.manifest_factory.write_release(root, version_file_content="1.2.2\n")

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
            manifest_path = self.manifest_factory.write_release(
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
            manifest_path = self.manifest_factory.write_release(root)
            add_origin(root)

            with (
                mock.patch(
                    "base_release.engine.gh_cli_finding",
                    return_value=ReleaseFinding("ok", "gh", "GitHub CLI is authenticated for github.com."),
                ),
                mock.patch(
                    "base_release.release_readiness.inspect_release_provenance",
                    return_value=release_readiness.ReleaseProvenanceInspection(
                        findings=READY_PROVENANCE_FINDINGS,
                        commit_sha=READY_SHA,
                    ),
                ),
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
            manifest_path = self.manifest_factory.write_release(root)
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
            manifest_path = self.manifest_factory.write_release(root)
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
            manifest_path = self.manifest_factory.write_release(root)
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


class ReleaseHelperTests(unittest.TestCase):
    def test_origin_repository_requires_matching_fetch_and_push_identities(self) -> None:
        matching = (
            ("https://github.com/codeforester/demo.git",),
            ("git@github.com:codeforester/demo.git",),
        )
        with mock.patch("base_release.release_readiness.git_remote_urls", side_effect=matching):
            finding = release_readiness.origin_repository_finding(Path("/repo"), "codeforester/demo")

        self.assertEqual(finding.status, "ok")

        mismatched_push = (
            ("https://github.com/codeforester/demo.git",),
            ("git@github.com:other/wrong.git",),
        )
        with mock.patch("base_release.release_readiness.git_remote_urls", side_effect=mismatched_push):
            finding = release_readiness.origin_repository_finding(Path("/repo"), "codeforester/demo")

        self.assertEqual(finding.status, "error")
        self.assertIn("other/wrong", finding.message)
        self.assertIn("codeforester/demo", finding.message)

    def test_remote_default_branch_uses_live_origin_head_not_tracking_refs(self) -> None:
        output = f"ref: refs/heads/main\tHEAD\n{READY_SHA}\tHEAD\n"
        completed = subprocess.CompletedProcess(["git", "ls-remote"], 0, stdout=output)
        with mock.patch("base_release.release_readiness.subprocess.run", return_value=completed) as run_git:
            remote, error = release_readiness.remote_default_branch(Path("/repo"))

        self.assertEqual((remote, error), (("main", READY_SHA), None))
        self.assertEqual(run_git.call_args.args[0], ["git", "ls-remote", "--symref", "origin", "HEAD"])

    def test_remote_default_branch_rejects_ambiguous_or_incomplete_responses(self) -> None:
        cases = (
            (f"{READY_SHA}\tHEAD\n", "did not advertise HEAD as a branch"),
            ("ref: refs/heads/main\tHEAD\ndeadbeef\tHEAD\n", "full commit SHA"),
            ("", "did not advertise HEAD as a branch"),
        )
        for output, expected_error in cases:
            with self.subTest(output=output):
                remote, error = release_readiness.parse_remote_default_branch(output)
                self.assertIsNone(remote)
                self.assertIn(expected_error, error or "")

    def test_feature_detached_and_unsynchronized_release_commits_fail_closed(self) -> None:
        branch_cases = (
            ("feature/release", "not origin's default branch"),
            ("", "detached"),
            (None, "Unable to inspect"),
        )
        for branch, expected in branch_cases:
            with self.subTest(branch=branch):
                finding = release_readiness.release_default_branch_finding(branch, "main")
                self.assertEqual(finding.status, "error")
                self.assertIn(expected, finding.message)

        for local_head in ("b" * 40, "c" * 40):
            with self.subTest(local_head=local_head):
                finding = release_readiness.release_commit_finding(local_head, "main", READY_SHA)
                self.assertEqual(finding.status, "error")
                self.assertIn(f"Local HEAD {local_head}", finding.message)
                self.assertIn(f"origin/main {READY_SHA}", finding.message)
                self.assertIn("behind, ahead, or diverged", finding.message)

    def test_provenance_recheck_returns_only_an_exact_ready_commit(self) -> None:
        ctx = mock.Mock()
        ctx.manifest_path = Path("/repo/base_manifest.yaml")
        ctx.release.github.repository = "codeforester/demo"
        with (
            mock.patch(
                "base_release.release_readiness.origin_repository_finding",
                return_value=READY_PROVENANCE_FINDINGS[0],
            ),
            mock.patch(
                "base_release.release_readiness.remote_default_branch",
                return_value=(("main", READY_SHA), None),
            ),
            mock.patch("base_release.release_readiness.current_git_branch", return_value="main"),
            mock.patch("base_release.release_readiness.current_git_head", return_value=READY_SHA),
        ):
            inspection = release_readiness.inspect_release_provenance(ctx)
            commit_sha = release_readiness.require_release_provenance(ctx)

        self.assertEqual(inspection.commit_sha, READY_SHA)
        self.assertEqual(commit_sha, READY_SHA)
        self.assertTrue(all(finding.status == "ok" for finding in inspection.findings))

    def test_local_and_remote_tag_verification_requires_annotated_expected_sha(self) -> None:
        tag_object_sha = "b" * 40
        remote_output = (
            f"{tag_object_sha}\trefs/tags/v1.2.3\n"
            f"{READY_SHA}\trefs/tags/v1.2.3^{{}}\n"
        )
        with mock.patch(
            "base_release.release_publish.capture_release_step",
            side_effect=("tag", READY_SHA, remote_output),
        ):
            release_publish.verify_local_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA)
            release_publish.verify_remote_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA)

        with mock.patch(
            "base_release.release_publish.capture_release_step",
            return_value=f"{tag_object_sha}\trefs/tags/v1.2.3\n",
        ):
            with self.assertRaisesRegex(ReleaseError, "missing or is not an annotated tag"):
                release_publish.verify_remote_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA)

    def test_inspect_remote_annotated_tag_classifies_safe_recovery_states(self) -> None:
        tag_object_sha = "b" * 40
        intended_output = (
            f"{tag_object_sha}\trefs/tags/v1.2.3\n"
            f"{READY_SHA}\trefs/tags/v1.2.3^{{}}\n"
        )
        with mock.patch("base_release.release_publish.capture_release_step", return_value=intended_output):
            self.assertEqual(
                release_publish.inspect_remote_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA), "intended"
            )
        with mock.patch("base_release.release_publish.capture_release_step", return_value=""):
            self.assertEqual(
                release_publish.inspect_remote_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA), "absent"
            )
        with mock.patch(
            "base_release.release_publish.capture_release_step",
            return_value=f"{tag_object_sha}\trefs/tags/v1.2.3\n",
        ):
            self.assertEqual(
                release_publish.inspect_remote_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA), "conflict"
            )
        with mock.patch(
            "base_release.release_publish.capture_release_step",
            side_effect=ReleaseError("network unavailable"),
        ):
            self.assertEqual(
                release_publish.inspect_remote_annotated_tag(Path("/repo"), "v1.2.3", READY_SHA), "unavailable"
            )

    def test_tag_verifiers_accept_a_real_annotated_tag_at_one_full_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            checkout = root / "checkout"
            remote = root / "remote.git"
            subprocess.run(["git", "init", "-b", "main", str(checkout)], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.name", "Base Test"], cwd=checkout, check=True)
            subprocess.run(["git", "config", "user.email", "base@example.invalid"], cwd=checkout, check=True)
            checkout.joinpath("README.md").write_text("release fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=checkout, check=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=checkout, check=True, stdout=subprocess.DEVNULL)
            expected_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=checkout, check=True)
            subprocess.run(
                ["git", "tag", "-a", "v1.2.3", expected_sha, "-m", "Release v1.2.3"],
                cwd=checkout,
                check=True,
            )
            subprocess.run(["git", "push", "origin", "v1.2.3"], cwd=checkout, check=True, stdout=subprocess.DEVNULL)

            release_publish.verify_local_annotated_tag(checkout, "v1.2.3", expected_sha)
            release_publish.verify_remote_annotated_tag(checkout, "v1.2.3", expected_sha)

    def test_github_release_verification_resolves_same_repository_tag_and_commit(self) -> None:
        ctx = mock.Mock()
        ctx.tag_name = "v1.2.3"
        ctx.manifest_path = Path("/repo/base_manifest.yaml")
        ctx.release.github.repository = "codeforester/demo"
        tag_object_sha = "b" * 40
        with mock.patch(
            "base_release.release_publish.capture_release_step",
            side_effect=(
                "v1.2.3",
                f"tag\t{tag_object_sha}",
                f"commit\t{READY_SHA}",
            ),
        ) as capture:
            release_publish.verify_github_release(ctx, READY_SHA)

        commands = [call.args[0] for call in capture.call_args_list]
        self.assertIn("repos/codeforester/demo/git/ref/tags/v1.2.3", commands[1])
        self.assertIn(f"repos/codeforester/demo/git/tags/{tag_object_sha}", commands[2])

        with mock.patch(
            "base_release.release_publish.capture_release_step",
            side_effect=(
                "v1.2.3",
                f"tag\t{tag_object_sha}",
                f"commit\t{'c' * 40}",
            ),
        ):
            with self.assertRaisesRegex(ReleaseError, "expected commit"):
                release_publish.verify_github_release(ctx, READY_SHA)

    def test_run_release_step_uses_bounded_timeout(self) -> None:
        completed = subprocess.CompletedProcess(["git", "tag"], 0, stdout="")

        with mock.patch("base_release.release_publish.process.run_capture", return_value=completed) as run_capture:
            release_publish.run_release_step(["git", "tag"], cwd=Path("/repo"))

        self.assertEqual(
            run_capture.call_args.kwargs["timeout_seconds"],
            release_publish.RELEASE_STEP_TIMEOUT_SECONDS,
        )

    def test_run_release_step_uses_shared_capture_helper(self) -> None:
        completed = subprocess.CompletedProcess(["git", "tag"], 0, stdout="")

        with mock.patch("base_release.release_publish.process.run_capture", return_value=completed) as run_capture:
            release_publish.run_release_step(["git", "tag"], cwd=Path("/repo"))

        run_capture.assert_called_once_with(
            ["git", "tag"],
            cwd=Path("/repo"),
            timeout_seconds=release_publish.RELEASE_STEP_TIMEOUT_SECONDS,
            stderr=subprocess.STDOUT,
        )

    def test_run_release_step_reports_timeout_as_release_error(self) -> None:
        command = ["git", "push", "origin", "v1.2.3"]

        with mock.patch(
            "base_release.release_publish.process.run_capture",
            side_effect=subprocess.TimeoutExpired(command, timeout=30),
        ):
            with self.assertRaisesRegex(ReleaseError, "timed out"):
                release_publish.run_release_step(command)

    def test_run_release_step_reports_os_error_as_release_error(self) -> None:
        command = ["gh", "release", "create", "v1.2.3"]

        with mock.patch(
            "base_release.release_publish.process.run_capture",
            side_effect=OSError("network unavailable"),
        ):
            with self.assertRaisesRegex(ReleaseError, "Unable to run release command"):
                release_publish.run_release_step(command)

    def test_run_release_step_quotes_spaced_arguments_in_errors(self) -> None:
        command = ["gh", "release", "create", "v1.2.3", "--title", "Demo Release"]
        completed = subprocess.CompletedProcess(command, 1, stdout="release failed\n")

        with mock.patch("base_release.release_publish.process.run_capture", return_value=completed):
            with self.assertRaisesRegex(
                ReleaseError,
                "gh release create v1.2.3 --title 'Demo Release'",
            ):
                release_publish.run_release_step(command)

    def test_git_worktree_finding_warns_when_status_times_out(self) -> None:
        with mock.patch(
            "base_release.release_readiness.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["git", "status", "--porcelain"], timeout=10),
        ):
            finding = release_readiness.git_worktree_finding(Path("/repo"))

        self.assertEqual(finding.status, "warn")
        self.assertIn("Unable to inspect Git worktree status", finding.message)

    def test_git_branch_finding_warns_when_branch_check_times_out(self) -> None:
        with mock.patch(
            "base_release.release_readiness.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["git", "branch", "--show-current"], timeout=10),
        ):
            finding = release_readiness.git_branch_finding(Path("/repo"))

        self.assertEqual(finding.status, "warn")
        self.assertIn("Unable to inspect current Git branch", finding.message)

    def test_local_tag_finding_warns_when_tag_check_times_out(self) -> None:
        with mock.patch(
            "base_release.release_readiness.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                ["git", "rev-parse", "--verify", "--quiet", "refs/tags/v1.2.3"],
                timeout=10,
            ),
        ):
            finding = release_readiness.local_tag_finding(Path("/repo"), "v1.2.3")

        self.assertEqual(finding.status, "warn")
        self.assertIn("Unable to inspect local tag v1.2.3", finding.message)
