from __future__ import annotations

import io
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_dev.engine import main


def run_engine(args: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        env = {
            "HOME": home_dir,
            "BASE_HOME": str(Path(__file__).resolve().parents[4]),
            "BASE_PLATFORM": "",
        }
        if extra_env:
            env.update(extra_env)
        with mock.patch.dict(os.environ, env):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class LinuxLabProfileTests(unittest.TestCase):
    def test_check_profile_linux_lab_reports_missing_multipass(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["check", "--profile", "linux-lab", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["linux-lab"])
        self.assertEqual(
            payload["checks"],
            [
                {
                    "id": "BASE-D108",
                    "status": "error",
                    "name": "multipass",
                    "message": "Multipass 'multipass' was not found.",
                    "fix": "basectl setup --profile linux-lab",
                }
            ],
        )

    def test_setup_profile_linux_lab_dry_run_prints_multipass_install_plan(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab", "--dry-run"],
                extra_env={"BASE_PLATFORM": "macos", "PATH": bin_dir},
            )

        self.assertEqual(status, 0)
        self.assertIn("Setting up Base 'linux-lab' prerequisites.", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install --cask multipass", stderr)
        self.assertIn("Base 'linux-lab' prerequisite setup dry-run is complete.", stderr)
        self.assertIn(
            "Multipass creates host-managed Ubuntu VMs; Base does not create VM instances during setup.",
            stderr,
        )

    def test_setup_profile_linux_lab_missing_multipass_is_macos_homebrew_only(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab"],
                extra_env={"BASE_PLATFORM": "linux-debian", "PATH": bin_dir},
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "The 'linux-lab' setup profile installs Multipass via Homebrew cask "
            "and is supported only on macOS hosts.",
            stderr,
        )

    def test_doctor_profile_linux_lab_json_uses_stable_finding_id(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["doctor", "--profile", "linux-lab", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        findings = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(findings[0]["id"], "BASE-D108")
        self.assertEqual(findings[0]["fix"], "basectl setup --profile linux-lab")


if __name__ == "__main__":
    unittest.main()
