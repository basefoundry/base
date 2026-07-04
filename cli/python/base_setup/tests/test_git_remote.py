from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import git_remote as git_remote_module
from base_setup.checks import check_to_json
from base_setup.checks import doctor_status
from base_setup.git_remote import check_git_remote
from base_setup.manifest import BaseManifest


def manifest_for(project_root: Path) -> BaseManifest:
    manifest_path = project_root / "base_manifest.yaml"
    manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
    return BaseManifest(path=manifest_path, project_name="demo", brewfile=None, artifacts=())


def git(project_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(project_root), *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def completed_process(
    args: list[str],
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


@unittest.skipUnless(shutil.which("git"), "Git is not installed")
class GitRemoteCheckTests(unittest.TestCase):
    def test_skips_project_directory_outside_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = manifest_for(Path(tmpdir))

            checks = check_git_remote(manifest)

        self.assertEqual(checks, ())

    def test_reports_git_repository_without_origin_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            manifest = manifest_for(project_root)

            checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081"])
        self.assertTrue(checks[0].ok)
        self.assertFalse(checks[1].ok)
        self.assertIn("does not have an 'origin' remote", checks[1].message)
        self.assertEqual(checks[1].details["network_checked"], False)

    def test_reports_github_remote_with_unavailable_auth_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "git@github.com:codeforester/base.git")
            manifest = manifest_for(project_root)

            with (
                mock.patch("base_setup.git_remote.process.command_exists", return_value=True),
                mock.patch("base_setup.git_remote.process.run_check", return_value=False) as run_check,
            ):
                checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081", "BASE-P082"])
        self.assertTrue(checks[1].ok)
        self.assertEqual(checks[1].details["provider"], "github")
        self.assertEqual(checks[1].details["transport"], "ssh")
        self.assertEqual(checks[1].details["repository"], "codeforester/base")
        self.assertFalse(checks[2].ok)
        self.assertEqual(doctor_status(checks[2]), "warn")
        self.assertEqual(checks[2].fix, "gh auth login -h github.com")
        run_check.assert_called_once_with(
            ["gh", "auth", "status", "-h", "github.com"],
            timeout_seconds=git_remote_module.REMOTE_REACHABILITY_TIMEOUT_SECONDS,
        )

    def test_reports_missing_github_cli_with_linux_install_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "git@github.com:codeforester/base.git")
            manifest = manifest_for(project_root)

            def command_exists(name: str) -> bool:
                return name == "git"

            with (
                mock.patch("base_setup.git_remote.process.command_exists", side_effect=command_exists),
                mock.patch.dict("os.environ", {"BASE_PLATFORM": "linux-debian"}, clear=False),
            ):
                checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081", "BASE-P082"])
        self.assertFalse(checks[2].ok)
        self.assertEqual(doctor_status(checks[2]), "warn")
        self.assertIn("official Debian/Ubuntu apt repository", checks[2].fix)
        self.assertIn("github.com/cli/cli/blob/trunk/docs/install_linux.md#debian", checks[2].fix)
        self.assertNotIn("basectl setup --profile dev", checks[2].fix)

    def test_reports_github_auth_timeout_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "git@github.com:codeforester/base.git")
            manifest = manifest_for(project_root)

            with (
                mock.patch("base_setup.git_remote.process.command_exists", return_value=True),
                mock.patch(
                    "base_setup.git_remote.process.run_check",
                    side_effect=subprocess.TimeoutExpired(["gh", "auth", "status"], 5),
                ) as run_check,
            ):
                checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081", "BASE-P082"])
        self.assertFalse(checks[2].ok)
        self.assertEqual(doctor_status(checks[2]), "warn")
        self.assertIn("timed out", checks[2].message)
        self.assertIn("retry", checks[2].fix)
        self.assertEqual(checks[2].details["gh_available"], True)
        self.assertEqual(checks[2].details["authenticated"], False)
        self.assertEqual(checks[2].details["failure_category"], "timeout")
        run_check.assert_called_once_with(
            ["gh", "auth", "status", "-h", "github.com"],
            timeout_seconds=git_remote_module.REMOTE_REACHABILITY_TIMEOUT_SECONDS,
        )

    def test_non_github_remote_does_not_check_github_cli_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "https://example.com/team/demo.git")
            manifest = manifest_for(project_root)

            def command_exists(name: str) -> bool:
                if name == "git":
                    return True
                raise AssertionError(f"unexpected command lookup: {name}")

            with (
                mock.patch("base_setup.git_remote.process.command_exists", side_effect=command_exists),
                mock.patch("base_setup.git_remote.process.run_check") as run_check,
            ):
                checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081"])
        self.assertTrue(checks[1].ok)
        self.assertEqual(checks[1].details["provider"], "other")
        self.assertEqual(checks[1].details["host"], "example.com")
        run_check.assert_not_called()

    def test_reports_missing_local_origin_path_without_network_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "../missing-remote.git")
            manifest = manifest_for(project_root)

            checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081"])
        self.assertFalse(checks[1].ok)
        self.assertEqual(checks[1].details["provider"], "local")
        self.assertEqual(checks[1].details["network_checked"], False)
        self.assertEqual(checks[1].details["reachable"], False)

    def test_reports_malformed_github_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "config", "remote.origin.url", "https://github.com")
            manifest = manifest_for(project_root)

            checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081"])
        self.assertFalse(checks[1].ok)
        self.assertIn("malformed", checks[1].message)
        self.assertEqual(checks[1].details["network_checked"], False)

    def test_sanitizes_credential_bearing_github_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "https://token:secret@github.com/codeforester/base.git")
            manifest = manifest_for(project_root)

            with (
                mock.patch("base_setup.git_remote.process.command_exists", return_value=True),
                mock.patch("base_setup.git_remote.process.run_check", return_value=True),
            ):
                checks = check_git_remote(manifest)

        payload = json.dumps([check_to_json(check) for check in checks])
        self.assertNotIn("token", payload)
        self.assertNotIn("secret", payload)
        self.assertIn("https://github.com/codeforester/base.git", payload)
        self.assertEqual(checks[1].details["sanitized_url"], "https://github.com/codeforester/base.git")

    def test_default_remote_checks_do_not_probe_network_reachability(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "https://example.com/team/demo.git")
            manifest = manifest_for(project_root)

            with mock.patch("base_setup.git_remote.run_git", wraps=git_remote_module.run_git) as run_git:
                checks = check_git_remote(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081"])
        self.assertFalse(any(call.args[1][0] == "ls-remote" for call in run_git.call_args_list))
        self.assertEqual(checks[1].details["network_checked"], False)

    def test_opt_in_network_check_reports_reachable_origin_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "https://example.com/team/demo.git")
            manifest = manifest_for(project_root)
            original_run_git = git_remote_module.run_git

            def run_git(
                project_root_arg: Path,
                arguments: list[str],
                timeout_seconds: int | None = None,
            ) -> subprocess.CompletedProcess[str]:
                if arguments[0] == "ls-remote":
                    self.assertIsNotNone(timeout_seconds)
                    return completed_process(arguments, 0, "abc123\tHEAD\n")
                return original_run_git(project_root_arg, arguments)

            with mock.patch("base_setup.git_remote.run_git", side_effect=run_git) as run_git_mock:
                checks = check_git_remote(manifest, check_network=True)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081", "BASE-P083"])
        self.assertTrue(checks[2].ok)
        self.assertEqual(doctor_status(checks[2]), "ok")
        self.assertEqual(checks[2].details["network_checked"], True)
        self.assertEqual(checks[2].details["reachable"], True)
        self.assertEqual(checks[2].details["remote"], "origin")
        self.assertEqual(checks[2].details["provider"], "other")
        self.assertEqual(checks[2].details["transport"], "https")
        self.assertEqual(checks[2].details["sanitized_url"], "https://example.com/team/demo.git")
        self.assertTrue(
            any(
                call.args[1] == ["ls-remote", "--exit-code", "origin", "HEAD"]
                for call in run_git_mock.call_args_list
            )
        )

    def test_opt_in_network_check_reports_unreachable_origin_remote_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "https://example.com/team/missing.git")
            manifest = manifest_for(project_root)
            original_run_git = git_remote_module.run_git

            def run_git(
                project_root_arg: Path,
                arguments: list[str],
                timeout_seconds: int | None = None,
            ) -> subprocess.CompletedProcess[str]:
                if arguments[0] == "ls-remote":
                    self.assertIsNotNone(timeout_seconds)
                    return completed_process(arguments, 128, stderr="fatal: repository not found\n")
                return original_run_git(project_root_arg, arguments)

            with mock.patch("base_setup.git_remote.run_git", side_effect=run_git):
                checks = check_git_remote(manifest, check_network=True)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081", "BASE-P083"])
        self.assertFalse(checks[2].ok)
        self.assertEqual(doctor_status(checks[2]), "warn")
        self.assertIn("could not be reached", checks[2].message)
        self.assertEqual(checks[2].details["network_checked"], True)
        self.assertEqual(checks[2].details["reachable"], False)
        self.assertEqual(checks[2].details["failure_category"], "unreachable")

    def test_opt_in_network_check_reports_timeout_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "git@example.com:team/demo.git")
            manifest = manifest_for(project_root)
            original_run_git = git_remote_module.run_git

            def run_git(
                project_root_arg: Path,
                arguments: list[str],
                timeout_seconds: int | None = None,
            ) -> subprocess.CompletedProcess[str]:
                if arguments[0] == "ls-remote":
                    self.assertIsNotNone(timeout_seconds)
                    raise subprocess.TimeoutExpired(["git", *arguments], 5)
                return original_run_git(project_root_arg, arguments)

            with mock.patch("base_setup.git_remote.run_git", side_effect=run_git):
                checks = check_git_remote(manifest, check_network=True)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P080", "BASE-P081", "BASE-P083"])
        self.assertFalse(checks[2].ok)
        self.assertEqual(doctor_status(checks[2]), "warn")
        self.assertIn("timed out", checks[2].message)
        self.assertEqual(checks[2].details["network_checked"], True)
        self.assertEqual(checks[2].details["reachable"], False)
        self.assertEqual(checks[2].details["failure_category"], "timeout")

    def test_network_check_json_does_not_expose_credential_bearing_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            git(project_root, "init")
            git(project_root, "remote", "add", "origin", "https://token:secret@example.com/team/demo.git")
            manifest = manifest_for(project_root)
            original_run_git = git_remote_module.run_git

            def run_git(
                project_root_arg: Path,
                arguments: list[str],
                timeout_seconds: int | None = None,
            ) -> subprocess.CompletedProcess[str]:
                if arguments[0] == "ls-remote":
                    self.assertIsNotNone(timeout_seconds)
                    return completed_process(arguments, 128, stderr="fatal: authentication failed\n")
                return original_run_git(project_root_arg, arguments)

            with mock.patch("base_setup.git_remote.run_git", side_effect=run_git):
                checks = check_git_remote(manifest, check_network=True)

        payload = json.dumps([check_to_json(check) for check in checks])
        self.assertNotIn("token", payload)
        self.assertNotIn("secret", payload)
        self.assertIn("https://example.com/team/demo.git", payload)
        self.assertEqual(checks[2].details["sanitized_url"], "https://example.com/team/demo.git")
