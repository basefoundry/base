from __future__ import annotations

import unittest
from unittest import mock

from base_dev import linux_profile
from base_setup.errors import ArtifactError
from base_setup.manifest_model import ArtifactRequest


class LinuxProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = mock.Mock()

    def test_github_cli_check_requires_latest_and_reports_installed_or_missing(self) -> None:
        artifact = ArtifactRequest("tool", "gh", "latest")
        with mock.patch.object(linux_profile, "current_base_platform", return_value="linux-debian"):
            with mock.patch.object(linux_profile, "command_exists", return_value=True):
                installed = linux_profile.check_linux_debian_github_cli_artifact(artifact)
            with mock.patch.object(linux_profile, "command_exists", return_value=False):
                missing = linux_profile.check_linux_debian_github_cli_artifact(artifact)

        self.assertTrue(installed.ok)
        self.assertEqual(installed.finding_id, "BASE-D011")
        self.assertFalse(missing.ok)
        self.assertEqual(missing.fix, "basectl setup --profile dev")

    def test_github_cli_check_rejects_non_latest(self) -> None:
        check = linux_profile.check_linux_debian_github_cli_artifact(
            ArtifactRequest("tool", "gh", "2.0.0")
        )

        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-D102")

    def test_apt_check_reports_installed_or_missing(self) -> None:
        artifact = ArtifactRequest("tool", "bats-core", "latest")
        tool = linux_profile.LINUX_DEBIAN_DEV_TOOLS["bats-core"]
        with mock.patch.object(linux_profile, "command_exists", return_value=True):
            installed = linux_profile.check_linux_debian_apt_artifact(artifact, tool)
        with mock.patch.object(linux_profile, "command_exists", return_value=False):
            missing = linux_profile.check_linux_debian_apt_artifact(artifact, tool)

        self.assertTrue(installed.ok)
        self.assertIn("apt package 'bats'", installed.message)
        self.assertFalse(missing.ok)
        self.assertEqual(missing.finding_id, "BASE-D104")

    def test_github_cli_reconcile_logs_existing_or_install_guidance(self) -> None:
        artifact = ArtifactRequest("tool", "gh", "latest")
        with mock.patch.object(linux_profile, "command_exists", return_value=True):
            linux_profile.reconcile_linux_debian_github_cli_artifact(self.ctx, artifact)
        self.ctx.log.info.assert_called_once()
        self.assertIn("already installed", self.ctx.log.info.call_args.args[0])

        self.ctx.reset_mock()
        with mock.patch.object(linux_profile, "command_exists", return_value=False):
            linux_profile.reconcile_linux_debian_github_cli_artifact(self.ctx, artifact)
        self.assertIn("official Debian/Ubuntu apt repository", self.ctx.log.info.call_args.args[0])

    def test_github_cli_reconcile_rejects_non_latest(self) -> None:
        with self.assertRaisesRegex(ArtifactError, "only supports GitHub CLI"):
            linux_profile.reconcile_linux_debian_github_cli_artifact(
                self.ctx, ArtifactRequest("tool", "gh", "2.0.0")
            )

    def test_apt_reconcile_dry_run_and_apply(self) -> None:
        artifact = ArtifactRequest("tool", "bats-core", "latest")
        tool = linux_profile.LINUX_DEBIAN_DEV_TOOLS["bats-core"]
        with mock.patch.object(linux_profile, "command_exists", return_value=False), mock.patch.object(
            linux_profile.process, "dry_run_command"
        ) as dry_run:
            linux_profile.reconcile_linux_debian_apt_artifact(self.ctx, artifact, tool, "dev", True)
        dry_run.assert_called_once_with(self.ctx, ["sudo", "apt-get", "install", "-y", "bats"])

        with mock.patch.object(linux_profile, "command_exists", side_effect=[False, True]), mock.patch.object(
            linux_profile.process, "run_command"
        ) as run_command:
            linux_profile.reconcile_linux_debian_apt_artifact(self.ctx, artifact, tool, "dev", False)
        run_command.assert_called_once_with(self.ctx, ["sudo", "apt-get", "install", "-y", "bats"])

    def test_apt_reconcile_requires_apt_get_when_not_dry_run(self) -> None:
        artifact = ArtifactRequest("tool", "bats-core", "latest")
        tool = linux_profile.LINUX_DEBIAN_DEV_TOOLS["bats-core"]
        with mock.patch.object(linux_profile, "command_exists", side_effect=[False, False]):
            with self.assertRaisesRegex(ArtifactError, "apt-get is required"):
                linux_profile.reconcile_linux_debian_apt_artifact(self.ctx, artifact, tool, "dev", False)


if __name__ == "__main__":
    unittest.main()
