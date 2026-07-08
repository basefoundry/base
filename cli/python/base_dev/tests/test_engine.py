from __future__ import annotations

# pylint: disable=too-many-lines,too-many-public-methods

import io
import importlib
import importlib.util
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_dev import ai_tools
from base_dev import engine
from base_dev import profile_output
from base_dev.engine import main
from base_setup.prerequisites import PrerequisiteCheck


def run_engine(args: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        env = {"HOME": home_dir, "BASE_HOME": str(Path(__file__).resolve().parents[4]), "BASE_PLATFORM": ""}
        if extra_env:
            env.update(extra_env)
        with mock.patch.dict(os.environ, env):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


class DevManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.platform_patcher = mock.patch.dict(os.environ, {"BASE_PLATFORM": ""})
        self.platform_patcher.start()
        self.addCleanup(self.platform_patcher.stop)

    def test_importing_main_module_does_not_execute_main(self) -> None:
        sys.modules.pop("base_dev.__main__", None)

        with mock.patch("base_dev.engine.main", side_effect=AssertionError("main should not run on import")):
            module = importlib.import_module("base_dev.__main__")

        self.assertEqual(module.__name__, "base_dev.__main__")

    def test_running_module_dispatches_to_main(self) -> None:
        sys.modules.pop("base_dev.__main__", None)

        with mock.patch("base_dev.engine.main", return_value=7) as main_mock:
            with self.assertRaises(SystemExit) as exc:
                runpy.run_module("base_dev", run_name="__main__", alter_sys=True)

        self.assertEqual(exc.exception.code, 7)
        main_mock.assert_called_once_with()

    def test_main_reports_missing_action_without_traceback(self) -> None:
        status, _stdout, stderr = run_engine([])

        self.assertEqual(status, 2)
        self.assertIn("Missing argument", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_engine_reexports_profile_helpers(self) -> None:
        from base_dev import profiles

        expected_names = (
            "ProfileError",
            "ProfileManifest",
            "ProfileRuntime",
            "SUPPORTED_PROFILES",
            "dev_manifest_path",
            "normalize_profiles",
            "profile_manifest_path",
            "read_dev_manifest",
            "read_profile_manifest",
            "read_profile_manifests",
        )

        for name in expected_names:
            with self.subTest(name=name):
                self.assertIs(getattr(engine, name), getattr(profiles, name))

    def test_dev_manifest_declares_supported_developer_tools(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        artifacts = {(artifact.artifact_type, artifact.name, artifact.version) for artifact in manifest.artifacts}

        self.assertIn(("tool", "bats-core", "latest"), artifacts)
        self.assertIn(("tool", "gh", "latest"), artifacts)
        self.assertIn(("tool", "shellcheck", "latest"), artifacts)

    def test_sre_manifest_declares_initial_sre_tools(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "sre_manifest.yaml")
        artifacts = {(artifact.artifact_type, artifact.name, artifact.version) for artifact in manifest.artifacts}

        self.assertIn(("tool", "kubectl", "latest"), artifacts)
        self.assertIn(("tool", "helm", "latest"), artifacts)
        self.assertIn(("tool", "k9s", "latest"), artifacts)
        self.assertIn(("tool", "httpie", "latest"), artifacts)
        self.assertIn(("tool", "grpcurl", "latest"), artifacts)
        self.assertIn(("tool", "jq", "latest"), artifacts)
        self.assertIn(("tool", "yq", "latest"), artifacts)
        self.assertIn(("tool", "nmap", "latest"), artifacts)
        self.assertIn(("tool", "mtr", "latest"), artifacts)

    def test_normalize_profiles_defaults_to_dev_and_deduplicates(self) -> None:
        self.assertEqual(engine.normalize_profiles(()), ("dev",))
        self.assertEqual(engine.normalize_profiles(("dev", "sre", "dev")), ("dev", "sre"))
        self.assertEqual(engine.normalize_profiles(("dev,SRE,AI",)), ("dev", "sre", "ai"))
        self.assertEqual(
            engine.normalize_profiles(("dev,LINUX-LAB,ai",)),
            ("dev", "linux-lab", "ai"),
        )

    def test_normalize_profiles_rejects_unknown_profile(self) -> None:
        with self.assertRaisesRegex(engine.ProfileError, "Unsupported profile 'ops'"):
            engine.normalize_profiles(("ops",))

    def test_normalize_profiles_rejects_empty_profile_list_entries(self) -> None:
        with self.assertRaisesRegex(engine.ProfileError, "Profile list must not contain empty entries"):
            engine.normalize_profiles(("dev,,sre",))

    def test_ai_remote_installer_urls_are_allowlisted(self) -> None:
        self.assertEqual(
            ai_tools.ai_remote_installer_urls(),
            (
                "https://chatgpt.com/codex/install.sh",
                "https://claude.ai/install.sh",
            ),
        )
        self.assertEqual(
            [ai_tools.ai_tool_installer_command(tool) for tool in ai_tools.AI_TOOLS],
            [
                (
                    "sh",
                    "-c",
                    'curl -fsSL "$1" | "$2"',
                    "--",
                    "https://chatgpt.com/codex/install.sh",
                    "sh",
                ),
                (
                    "sh",
                    "-c",
                    'curl -fsSL "$1" | "$2"',
                    "--",
                    "https://claude.ai/install.sh",
                    "bash",
                ),
            ],
        )

    def test_ai_installer_command_does_not_interpolate_url_into_shell_source(self) -> None:
        command = ai_tools.ai_tool_installer_command(ai_tools.AI_TOOLS[0])

        self.assertNotIn(ai_tools.AI_TOOLS[0].installer_url, command[2])
        self.assertEqual(command[3:], ("--", ai_tools.AI_TOOLS[0].installer_url, "sh"))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_profile_sre_uses_sre_manifest(self) -> None:
        with mock.patch("base_setup.process.command_exists", return_value=False):
            status, _stdout, stderr = run_engine(["setup", "--profile", "sre", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install kubernetes-cli", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install helm", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install k9s", stderr)
        self.assertNotIn("brew install bats-core", stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_profile_ai_dry_run_prints_official_installers(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "ai", "--dry-run"],
                extra_env={"PATH": bin_dir},
            )

        self.assertEqual(status, 0)
        self.assertIn(
            "Remote installer policy: Codex CLI uses allowlisted installer "
            "https://chatgpt.com/codex/install.sh; execution requires explicit --profile ai.",
            stderr,
        )
        self.assertIn(
            "Remote installer policy: Claude Code uses allowlisted installer "
            "https://claude.ai/install.sh; execution requires explicit --profile ai.",
            stderr,
        )
        self.assertIn(
            "[DRY-RUN] Would run: sh -c 'curl -fsSL \"$1\" | \"$2\"' -- "
            "https://chatgpt.com/codex/install.sh sh",
            stderr,
        )
        self.assertIn(
            "[DRY-RUN] Would run: sh -c 'curl -fsSL \"$1\" | \"$2\"' -- "
            "https://claude.ai/install.sh bash",
            stderr,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_profile_ai_skips_installed_tools(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            bin_path = Path(bin_dir)
            write_executable(bin_path / "codex", "#!/bin/sh\nprintf 'codex 1.2.3\\n'\n")
            write_executable(bin_path / "claude", "#!/bin/sh\nprintf '1.0.0 (Claude Code)\\n'\n")

            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "ai", "--dry-run"],
                extra_env={"PATH": bin_dir},
            )

        self.assertEqual(status, 0)
        self.assertIn("Codex CLI is already installed", stderr)
        self.assertIn("Claude Code is already installed", stderr)
        self.assertNotIn("chatgpt.com/codex/install.sh", stderr)
        self.assertNotIn("claude.ai/install.sh", stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_default_dry_run_does_not_include_ai_remote_installers(self) -> None:
        with mock.patch("base_setup.process.command_exists", return_value=False):
            status, _stdout, stderr = run_engine(["setup", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertNotIn("chatgpt.com/codex/install.sh", stderr)
        self.assertNotIn("claude.ai/install.sh", stderr)

    def test_setup_ai_tools_rejects_unallowlisted_remote_installer(self) -> None:
        tool = ai_tools.AITool(
            name="bad-ai",
            display_name="Bad AI",
            version_args=("--version",),
            installer_url="https://example.invalid/install.sh",
            installer_shell="sh",
        )
        ctx = mock.Mock()

        with (
            mock.patch("base_dev.ai_tools.AI_TOOLS", (tool,)),
            mock.patch("base_dev.ai_tools.check_ai_tool", return_value=engine.DevCheck("bad-ai", False, "missing", "")),
            mock.patch("base_dev.ai_tools.run_command") as run_command,
        ):
            status = ai_tools.setup_ai_tools(ctx, dry_run=False)

        self.assertEqual(status, 1)
        self.assertIn("Remote installer URL is not allowlisted", ctx.log.error.call_args.args[0])
        run_command.assert_not_called()

    def test_setup_ai_tools_noninteractive_explicit_profile_runs_allowlisted_installers(self) -> None:
        ctx = mock.Mock()

        with (
            mock.patch.dict(os.environ, {"CI": "true"}),
            mock.patch("base_dev.ai_tools.check_ai_tool", return_value=engine.DevCheck("tool", False, "missing", "")),
            mock.patch("base_dev.ai_tools.run_command") as run_command,
        ):
            status = ai_tools.setup_ai_tools(ctx, dry_run=False)

        self.assertEqual(status, 0)
        self.assertEqual(
            [call.args[1] for call in run_command.call_args_list],
            [
                ["sh", "-c", 'curl -fsSL "$1" | "$2"', "--", "https://chatgpt.com/codex/install.sh", "sh"],
                ["sh", "-c", 'curl -fsSL "$1" | "$2"', "--", "https://claude.ai/install.sh", "bash"],
            ],
        )

    def test_check_ai_tool_warns_when_version_probe_times_out(self) -> None:
        tool = ai_tools.AITool(
            name="codex",
            display_name="Codex CLI",
            version_args=("--version",),
            installer_url="https://chatgpt.com/codex/install.sh",
            installer_shell="sh",
        )

        with (
            mock.patch("base_dev.ai_tools.shutil.which", return_value="/tmp/bin/codex"),
            mock.patch(
                "base_dev.ai_tools.subprocess.run",
                side_effect=subprocess.TimeoutExpired(
                    ["/tmp/bin/codex", "--version"],
                    ai_tools.DIAGNOSTIC_TIMEOUT_SECONDS,
                ),
            ) as run,
        ):
            check = ai_tools.check_ai_tool(tool)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, "Retry 'codex --version' or run 'basectl setup --profile ai'.")
        run.assert_called_once_with(
            ["/tmp/bin/codex", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=ai_tools.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_sre_reports_sre_fix_guidance(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            status, stdout, stderr = run_engine(["check", "--profile", "sre", "--format", "json"])

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["sre"])
        self.assertEqual(findings[0]["name"], "kubectl")
        self.assertEqual(findings[0]["id"], "BASE-D104")
        self.assertEqual(findings[0]["status"], "error")
        self.assertNotIn("ok", findings[0])
        self.assertEqual(findings[0]["fix"], "basectl setup --profile sre")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_ai_reports_missing_tools(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["check", "--profile", "ai", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["ai"])
        self.assertEqual([finding["name"] for finding in findings], ["codex", "claude"])
        self.assertEqual(findings[0]["fix"], "basectl setup --profile ai")
        self.assertEqual(findings[1]["fix"], "basectl setup --profile ai")
        self.assertIn("Codex CLI 'codex' was not found", findings[0]["message"])
        self.assertIn("Claude Code 'claude' was not found", findings[1]["message"])

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_ai_reports_installed_tool_versions(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            bin_path = Path(bin_dir)
            write_executable(bin_path / "codex", "#!/bin/sh\nprintf 'codex 1.2.3\\n'\n")
            write_executable(
                bin_path / "claude",
                "#!/bin/sh\nprintf 'Warning: update available\\n' >&2\nprintf '1.0.0 (Claude Code)\\n'\n",
            )

            status, stdout, stderr = run_engine(
                ["check", "--profile", "ai", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["profiles"], ["ai"])
        self.assertTrue(all(finding["status"] == "ok" for finding in findings))
        self.assertTrue(all("ok" not in finding for finding in findings))
        self.assertIn(str(bin_path / "codex"), findings[0]["message"])
        self.assertIn("codex 1.2.3", findings[0]["message"])
        self.assertIn(str(bin_path / "claude"), findings[1]["message"])
        self.assertIn("1.0.0 (Claude Code)", findings[1]["message"])
        self.assertNotIn("Warning: update available", findings[1]["message"])

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_ai_reports_version_failures(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            bin_path = Path(bin_dir)
            write_executable(bin_path / "codex", "#!/bin/sh\nprintf 'codex crashed\\n' >&2\nexit 7\n")
            write_executable(bin_path / "claude", "#!/bin/sh\nprintf '1.0.0 (Claude Code)\\n'\n")

            status, stdout, stderr = run_engine(
                ["check", "--profile", "ai", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["ai"])
        self.assertEqual(findings[0]["name"], "codex")
        self.assertEqual(findings[0]["status"], "error")
        self.assertNotIn("ok", findings[0])
        self.assertEqual(findings[0]["fix"], "basectl setup --profile ai")
        self.assertIn("Codex CLI version check failed with exit 7", findings[0]["message"])
        self.assertIn("codex crashed", findings[0]["message"])
        self.assertEqual(findings[1]["status"], "ok")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_multiple_profiles_combines_results_once_per_profile(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            status, stdout, stderr = run_engine(
                ["check", "--profile", "dev,sre", "--format", "json"]
            )

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["dev", "sre"])
        names = [finding["name"] for finding in findings]
        self.assertIn("bats-core", names)
        self.assertIn("kubectl", names)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_doctor_profile_ai_json_uses_stable_finding_ids(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["doctor", "--profile", "ai", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        findings = json.loads(stdout)
        self.assertEqual(status, 2)
        self.assertEqual(stderr, "")
        self.assertEqual([finding["id"] for finding in findings], ["BASE-D107", "BASE-D107"])
        self.assertEqual([finding["status"] for finding in findings], ["error", "error"])
        self.assertEqual(
            [finding["fix"] for finding in findings],
            ["basectl setup --profile ai", "basectl setup --profile ai"],
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_manifest_artifacts(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["dev"])
        self.assertIn("bats-core", [finding["name"] for finding in findings])
        self.assertIn("gh", [finding["name"] for finding in findings])
        self.assertIn("shellcheck", [finding["name"] for finding in findings])
        self.assertTrue(all("ok" not in finding for finding in findings))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_invalid_github_auth_when_gh_is_installed(self) -> None:
        current = subprocess.CompletedProcess(
            ["brew", "outdated", "gh"],
            0,
            stdout="",
            stderr="",
        )

        def fake_run_check(command: list[str], **kwargs: object) -> bool:
            self.assertEqual(kwargs.get("timeout_seconds"), engine.DIAGNOSTIC_TIMEOUT_SECONDS)
            if command == ["brew", "list", "bats-core"]:
                return True
            if command == ["brew", "list", "gh"]:
                return True
            if command == ["brew", "list", "shellcheck"]:
                return True
            if command == ["gh", "auth", "status", "-h", "github.com"]:
                return False
            raise AssertionError(f"Unexpected command: {command}")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", side_effect=fake_run_check),
            mock.patch("base_setup.process.run_capture", return_value=current),
        ):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(
            {
                "id": "BASE-D106",
                "status": "error",
                "name": "gh-auth",
                "message": "GitHub CLI authentication is not ready.",
                "fix": "gh auth login -h github.com",
            },
            findings,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_dev_linux_debian_reports_missing_apt_tools(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["check", "--profile", "dev", "--format", "json"],
                extra_env={"BASE_PLATFORM": "linux-debian", "PATH": bin_dir},
            )

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["dev"])
        self.assertIn(
            {
                "id": "BASE-D104",
                "status": "error",
                "name": "bats-core",
                "message": "Artifact 'bats-core' is not installed via apt package 'bats'.",
                "fix": "basectl setup --profile dev",
            },
            findings,
        )
        self.assertIn(
            {
                "id": "BASE-D107",
                "status": "error",
                "name": "gh",
                "message": (
                    "GitHub CLI 'gh' is not installed; Base setup installs it from GitHub CLI's official "
                    "Debian/Ubuntu apt repository."
                ),
                "fix": "basectl setup --profile dev",
            },
            findings,
        )
        self.assertTrue(all("Homebrew" not in finding["message"] for finding in findings))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_dev_linux_debian_reports_installed_apt_tools(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            bin_path = Path(bin_dir)
            write_executable(bin_path / "bats", "#!/bin/sh\nexit 0\n")
            write_executable(bin_path / "gh", "#!/bin/sh\nexit 0\n")
            write_executable(bin_path / "shellcheck", "#!/bin/sh\nexit 0\n")

            status, stdout, stderr = run_engine(
                ["check", "--profile", "dev", "--format", "json"],
                extra_env={"BASE_PLATFORM": "linux-debian", "PATH": bin_dir},
            )

        payload = json.loads(stdout)
        findings = payload["checks"]
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["profiles"], ["dev"])
        self.assertIn("gh-auth", [finding["name"] for finding in findings])
        self.assertTrue(all(finding["status"] == "ok" for finding in findings))
        self.assertTrue(all("Homebrew" not in finding["message"] for finding in findings))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_outdated_homebrew_artifact(self) -> None:
        def fake_run_capture(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            output = "gh\n" if command == ["brew", "outdated", "gh"] else ""
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=True),
            mock.patch("base_setup.process.run_capture", side_effect=fake_run_capture),
        ):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        payload = json.loads(stdout)
        findings = payload["checks"]
        gh_finding = next(finding for finding in findings if finding["name"] == "gh")
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(gh_finding["id"], "BASE-D104")
        self.assertEqual(gh_finding["status"], "error")
        self.assertIn("outdated via Homebrew package 'gh'", gh_finding["message"])
        self.assertEqual(gh_finding["fix"], "basectl setup --profile dev")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_dry_run_uses_homebrew_registry_definitions(self) -> None:
        with mock.patch("base_setup.process.command_exists", return_value=False):
            status, _stdout, stderr = run_engine(["setup", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install bats-core", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install gh", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install shellcheck", stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_dry_run_linux_debian_delegates_github_cli_to_platform_setup(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "dev", "--dry-run"],
                extra_env={"BASE_PLATFORM": "linux-debian", "PATH": bin_dir},
            )

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: sudo apt-get install -y bats", stderr)
        self.assertIn("[DRY-RUN] Would run: sudo apt-get install -y shellcheck", stderr)
        self.assertNotIn("apt-get install -y gh", stderr)
        self.assertIn("GitHub CLI 'gh' is installed by basectl setup's Ubuntu/Debian platform layer.", stderr)
        self.assertIn("github.com/cli/cli/blob/trunk/docs/install_linux.md#debian", stderr)
        self.assertNotIn("brew install", stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_linux_debian_skips_installed_apt_tools(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            bin_path = Path(bin_dir)
            write_executable(bin_path / "bats", "#!/bin/sh\nexit 0\n")
            write_executable(bin_path / "gh", "#!/bin/sh\nexit 0\n")
            write_executable(bin_path / "shellcheck", "#!/bin/sh\nexit 0\n")

            with mock.patch("base_setup.process.run_command") as run_command:
                status, _stdout, stderr = run_engine(
                    ["setup", "--profile", "dev"],
                    extra_env={"BASE_PLATFORM": "linux-debian", "PATH": bin_dir},
                )

        self.assertEqual(status, 0)
        self.assertIn("Artifact 'bats-core' is already installed via apt package 'bats'.", stderr)
        self.assertIn("GitHub CLI 'gh' is already installed; authentication remains user-owned.", stderr)
        self.assertNotIn("Artifact 'gh' is already installed via apt package 'gh'.", stderr)
        self.assertIn("Artifact 'shellcheck' is already installed via apt package 'shellcheck'.", stderr)
        self.assertNotIn("Homebrew is required", stderr)
        run_command.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_dry_run_upgrades_outdated_homebrew_artifact(self) -> None:
        def fake_run_capture(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            output = "gh\n" if command == ["brew", "outdated", "gh"] else ""
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        with (
            mock.patch("base_setup.process.command_exists", return_value=True),
            mock.patch("base_setup.process.run_check", return_value=True),
            mock.patch("base_setup.process.run_capture", side_effect=fake_run_capture),
        ):
            status, _stdout, stderr = run_engine(["setup", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew upgrade gh", stderr)
        self.assertNotIn("[DRY-RUN] Would run: brew install gh", stderr)

    def test_check_homebrew_artifact_reports_installed_formula(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")
        current = subprocess.CompletedProcess(
            ["brew", "outdated", "gh"],
            0,
            stdout="",
            stderr="",
        )

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=True) as run_check,
            mock.patch("base_setup.process.run_capture", return_value=current),
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertTrue(check.ok)
        self.assertEqual(check.name, "gh")
        self.assertEqual(check.fix, "")
        self.assertIn("is installed via Homebrew package 'gh'", check.message)
        run_check.assert_called_once_with(
            ["brew", "list", "gh"],
            timeout_seconds=engine.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_check_homebrew_artifact_uses_shared_prerequisite_core(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")
        expected = PrerequisiteCheck(
            name="gh",
            ok=True,
            message="shared Homebrew check",
            fix="",
            finding_id="BASE-D104",
        )

        with mock.patch("base_dev.engine.check_homebrew_package", return_value=expected) as check_homebrew_package:
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertTrue(check.ok)
        self.assertEqual(check.message, "shared Homebrew check")
        self.assertEqual(check.finding_id, "BASE-D104")
        request = check_homebrew_package.call_args.args[0]
        self.assertEqual(request.name, "gh")
        self.assertEqual(request.package, "gh")
        self.assertEqual(request.version, "latest")
        self.assertEqual(request.manager, "homebrew")

    def test_check_homebrew_artifact_reports_outdated_formula(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")
        outdated = subprocess.CompletedProcess(
            ["brew", "outdated", "gh"],
            0,
            stdout="gh\n",
            stderr="",
        )

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=True),
            mock.patch("base_setup.process.run_capture", return_value=outdated),
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.name, "gh")
        self.assertEqual(check.finding_id, "BASE-D104")
        self.assertEqual(check.fix, "basectl setup --profile dev")
        self.assertIn("outdated via Homebrew package 'gh'", check.message)

    def test_check_homebrew_artifact_reports_missing_formula(self) -> None:
        artifact = engine.ArtifactRequest("tool", "bats-core", "latest")
        definition = engine.ArtifactDefinition("bats-core", "tool", "homebrew", "bats-core", "system")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False) as run_check,
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.fix, "basectl setup --profile dev")
        self.assertIn("is not installed via Homebrew package 'bats-core'", check.message)
        run_check.assert_called_once_with(
            ["brew", "list", "bats-core"],
            timeout_seconds=engine.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_check_homebrew_artifact_warns_when_probe_times_out(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch(
                "base_dev.engine.run_check",
                side_effect=subprocess.TimeoutExpired(["brew", "list", "gh"], engine.DIAGNOSTIC_TIMEOUT_SECONDS),
            ) as run_check,
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-D104")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, "Retry 'basectl doctor --profile dev' or inspect Homebrew with 'brew doctor'.")
        run_check.assert_called_once_with(
            ["brew", "list", "gh"],
            timeout_seconds=engine.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_check_homebrew_artifact_reports_missing_homebrew(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=False) as command_exists,
            mock.patch("base_dev.engine.run_check") as run_check,
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.fix, "basectl setup")
        self.assertIn("Homebrew is required", check.message)
        command_exists.assert_called_once_with("brew")
        run_check.assert_not_called()

    def test_check_homebrew_artifact_rejects_unsupported_version(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "2.0.0")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")

        with (
            mock.patch("base_dev.engine.command_exists") as command_exists,
            mock.patch("base_dev.engine.run_check") as run_check,
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertFalse(check.ok)
        self.assertIn("unsupported developer prerequisite version '2.0.0'", check.message)
        command_exists.assert_not_called()
        run_check.assert_not_called()

    def test_check_homebrew_artifact_rejects_unsupported_manager(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "manual", "gh", "system")

        with (
            mock.patch("base_dev.engine.command_exists") as command_exists,
            mock.patch("base_dev.engine.run_check") as run_check,
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertFalse(check.ok)
        self.assertIn("unsupported developer prerequisite manager 'manual'", check.message)
        command_exists.assert_not_called()
        run_check.assert_not_called()

    def test_setup_dev_artifacts_runs_installs_when_not_dry_run(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")
        manifest = engine.BaseManifest(Path("dev_manifest.yaml"), "base", None, (artifact,))
        ctx = mock.Mock()

        with mock.patch("base_dev.engine.reconcile_artifact") as reconcile_artifact:
            status = engine.setup_dev_artifacts(ctx, manifest, (definition,), dry_run=False)

        self.assertEqual(status, 0)
        reconcile_artifact.assert_called_once_with(ctx, definition, "latest", "base", dry_run=False)
        ctx.log.info.assert_any_call("Base developer prerequisite setup is complete.")

    def test_setup_dev_artifacts_reports_reconcile_failures(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")
        manifest = engine.BaseManifest(Path("dev_manifest.yaml"), "base", None, (artifact,))
        ctx = mock.Mock()

        with mock.patch("base_dev.engine.reconcile_artifact", side_effect=engine.ArtifactError("install failed")):
            status = engine.setup_dev_artifacts(ctx, manifest, (definition,), dry_run=False)

        self.assertEqual(status, 1)
        ctx.log.error.assert_called_once_with("install failed")

    def test_check_github_cli_auth_reports_missing_gh(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=False) as command_exists,
            mock.patch("base_dev.engine.run_check") as run_check,
        ):
            check = engine.check_github_cli_auth()

        self.assertFalse(check.ok)
        self.assertEqual(check.name, "gh-auth")
        self.assertIn("was not found", check.message)
        self.assertEqual(check.fix, "basectl setup --profile dev")
        command_exists.assert_called_once_with("gh")
        run_check.assert_not_called()

    def test_check_github_cli_auth_uses_shared_prerequisite_core(self) -> None:
        expected = PrerequisiteCheck(
            name="gh-auth",
            ok=True,
            message="shared GitHub auth check",
            fix="",
            finding_id="BASE-D106",
        )

        with mock.patch("base_dev.engine.check_github_cli_auth_prerequisite", return_value=expected) as check_auth:
            check = engine.check_github_cli_auth()

        self.assertTrue(check.ok)
        self.assertEqual(check.message, "shared GitHub auth check")
        self.assertEqual(check.finding_id, "BASE-D106")
        request = check_auth.call_args.args[0]
        self.assertEqual(request.timeout_seconds, engine.DIAGNOSTIC_TIMEOUT_SECONDS)
        self.assertEqual(request.command, ("gh", "auth", "status", "-h", "github.com"))

    def test_check_github_cli_auth_reports_unauthenticated_gh(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False) as run_check,
        ):
            check = engine.check_github_cli_auth()

        self.assertFalse(check.ok)
        self.assertEqual(check.message, "GitHub CLI authentication is not ready.")
        self.assertEqual(check.fix, "gh auth login -h github.com")
        run_check.assert_called_once_with(
            ["gh", "auth", "status", "-h", "github.com"],
            timeout_seconds=engine.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_check_github_cli_auth_reports_authenticated_gh(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=True) as run_check,
        ):
            check = engine.check_github_cli_auth()

        self.assertTrue(check.ok)
        self.assertEqual(check.message, "GitHub CLI authentication is ready.")
        self.assertEqual(check.fix, "")
        run_check.assert_called_once_with(
            ["gh", "auth", "status", "-h", "github.com"],
            timeout_seconds=engine.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_check_github_cli_auth_warns_when_probe_times_out(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch(
                "base_dev.engine.run_check",
                side_effect=subprocess.TimeoutExpired(
                    ["gh", "auth", "status", "-h", "github.com"],
                    engine.DIAGNOSTIC_TIMEOUT_SECONDS,
                ),
            ) as run_check,
        ):
            check = engine.check_github_cli_auth()

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, "Retry 'gh auth status -h github.com' or run 'gh auth login -h github.com'.")
        run_check.assert_called_once_with(
            ["gh", "auth", "status", "-h", "github.com"],
            timeout_seconds=engine.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_doctor_returns_number_of_failed_manifest_artifacts(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 3)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error", stderr.getvalue())
        self.assertIn("Fix: basectl setup --profile dev", stderr.getvalue())

    def test_doctor_reports_invalid_github_auth(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)
        current = subprocess.CompletedProcess(
            ["brew", "outdated", "gh"],
            0,
            stdout="",
            stderr="",
        )

        def fake_run_check(command: list[str], **kwargs: object) -> bool:
            self.assertEqual(kwargs.get("timeout_seconds"), engine.DIAGNOSTIC_TIMEOUT_SECONDS)
            if command == ["brew", "list", "bats-core"]:
                return True
            if command == ["brew", "list", "gh"]:
                return True
            if command == ["brew", "list", "shellcheck"]:
                return True
            if command == ["gh", "auth", "status", "-h", "github.com"]:
                return False
            raise AssertionError(f"Unexpected command: {command}")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", side_effect=fake_run_check),
            mock.patch("base_setup.process.run_capture", return_value=current),
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 1)
        self.assertIn("BASE-D104", stdout.getvalue())
        self.assertNotIn("gh-auth", stdout.getvalue())
        self.assertIn("gh-auth", stderr.getvalue())
        self.assertIn("GitHub CLI authentication is not ready.", stderr.getvalue())
        self.assertIn("Fix: gh auth login -h github.com", stderr.getvalue())

    def test_doctor_reports_unsupported_text_format_to_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.doctor_dev_artifacts((), (), output_format="xml")

        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Unsupported doctor output format 'xml'. Expected text or json.", stderr.getvalue())

    def test_doctor_supports_json_output(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 3)
        self.assertEqual(findings[0]["id"], "BASE-D104")
        self.assertEqual(findings[0]["status"], "error")
        self.assertEqual(findings[0]["fix"], "basectl setup --profile dev")

    def test_doctor_warning_status_does_not_fail(self) -> None:
        check = engine.DevCheck(
            name="optional-tool",
            ok=False,
            message="Optional developer tool is not installed.",
            fix="brew install optional-tool",
            status="warn",
        )

        self.assertEqual(engine.doctor_status(check), "warn")
        self.assertEqual(engine.check_to_doctor_json(check)["id"], "BASE-D100")
        self.assertEqual(engine.check_to_doctor_json(check)["status"], "warn")

        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)
        with mock.patch("base_dev.engine.check_homebrew_artifact", return_value=check):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("warn", stderr.getvalue())

    def test_engine_uses_exit_code_constants_for_status_comparisons(self) -> None:
        source = Path(engine.__file__).read_text(encoding="utf-8")

        self.assertNotIn("status != 0", source)

    def test_profile_output_rendering_lives_outside_engine(self) -> None:
        source = Path(engine.__file__).read_text(encoding="utf-8")

        self.assertIs(engine.print_check_results, profile_output.print_check_results)
        self.assertIs(engine.print_doctor_results, profile_output.print_doctor_results)
        self.assertNotIn("def print_check_results", source)
        self.assertNotIn("def print_doctor_results", source)


if __name__ == "__main__":
    unittest.main()
