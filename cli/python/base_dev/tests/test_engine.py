from __future__ import annotations

# pylint: disable=too-many-public-methods

import io
import importlib
import importlib.util
import json
import os
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_dev import engine
from base_dev.engine import main


def run_engine(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(os.environ, {"HOME": home_dir, "BASE_HOME": str(Path(__file__).resolve().parents[4])}):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class DevManifestTests(unittest.TestCase):
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
        self.assertEqual(engine.normalize_profiles(("dev,SRE",)), ("dev", "sre"))

    def test_normalize_profiles_rejects_unknown_profile(self) -> None:
        with self.assertRaisesRegex(engine.ProfileError, "Unsupported profile 'ai'"):
            engine.normalize_profiles(("ai",))

    def test_normalize_profiles_rejects_empty_profile_list_entries(self) -> None:
        with self.assertRaisesRegex(engine.ProfileError, "Profile list must not contain empty entries"):
            engine.normalize_profiles(("dev,,sre",))

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_profile_sre_uses_sre_manifest(self) -> None:
        status, _stdout, stderr = run_engine(["setup", "--profile", "sre", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install kubernetes-cli", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install helm", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install k9s", stderr)
        self.assertNotIn("brew install bats-core", stderr)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_profile_sre_reports_sre_fix_guidance(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            status, stdout, stderr = run_engine(["check", "--profile", "sre", "--format", "json"])

        findings = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(findings[0]["name"], "kubectl")
        self.assertEqual(findings[0]["fix"], "basectl setup --profile sre")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_multiple_profiles_combines_results_once_per_profile(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            status, stdout, stderr = run_engine(
                ["check", "--profile", "dev,sre", "--format", "json"]
            )

        findings = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        names = [finding["name"] for finding in findings]
        self.assertIn("bats-core", names)
        self.assertIn("kubectl", names)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_manifest_artifacts(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        self.assertEqual(status, 1)
        self.assertIn('"name": "bats-core"', stdout)
        self.assertIn('"ok": false', stdout)
        self.assertIn('"name": "gh"', stdout)
        self.assertIn('"name": "shellcheck"', stdout)
        self.assertEqual(stderr, "")

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_invalid_github_auth_when_gh_is_installed(self) -> None:
        def fake_run_check(command: list[str]) -> bool:
            if command == ["brew", "list", "bats-core"]:
                return True
            if command == ["brew", "list", "gh"]:
                return True
            if command == ["brew", "list", "shellcheck"]:
                return True
            if command == ["gh", "auth", "status"]:
                return False
            raise AssertionError(f"Unexpected command: {command}")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", side_effect=fake_run_check),
        ):
            status, stdout, stderr = run_engine(["check", "--format", "json"])

        findings = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertIn(
            {
                "name": "gh-auth",
                "ok": False,
                "message": "GitHub CLI authentication is not ready.",
                "fix": "gh auth login -h github.com",
            },
            findings,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_dry_run_uses_homebrew_registry_definitions(self) -> None:
        status, _stdout, stderr = run_engine(["setup", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install bats-core", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install gh", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install shellcheck", stderr)

    def test_check_homebrew_artifact_reports_installed_formula(self) -> None:
        artifact = engine.ArtifactRequest("tool", "gh", "latest")
        definition = engine.ArtifactDefinition("gh", "tool", "homebrew", "gh", "system")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=True) as run_check,
        ):
            check = engine.check_homebrew_artifact(artifact, definition)

        self.assertTrue(check.ok)
        self.assertEqual(check.name, "gh")
        self.assertEqual(check.fix, "")
        self.assertIn("is installed via Homebrew package 'gh'", check.message)
        run_check.assert_called_once_with(["brew", "list", "gh"])

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
        run_check.assert_called_once_with(["brew", "list", "bats-core"])

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

    def test_check_github_cli_auth_reports_unauthenticated_gh(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False) as run_check,
        ):
            check = engine.check_github_cli_auth()

        self.assertFalse(check.ok)
        self.assertEqual(check.message, "GitHub CLI authentication is not ready.")
        self.assertEqual(check.fix, "gh auth login -h github.com")
        run_check.assert_called_once_with(["gh", "auth", "status"])

    def test_check_github_cli_auth_reports_authenticated_gh(self) -> None:
        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=True) as run_check,
        ):
            check = engine.check_github_cli_auth()

        self.assertTrue(check.ok)
        self.assertEqual(check.message, "GitHub CLI authentication is ready.")
        self.assertEqual(check.fix, "")
        run_check.assert_called_once_with(["gh", "auth", "status"])

    def test_doctor_returns_number_of_failed_manifest_artifacts(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", return_value=False),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 3)
        self.assertIn("error", stdout.getvalue())
        self.assertIn("Fix: basectl setup --profile dev", stdout.getvalue())

    def test_doctor_reports_invalid_github_auth(self) -> None:
        manifest = engine.read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        definitions = engine.resolve_artifact_definitions(manifest.artifacts)

        def fake_run_check(command: list[str]) -> bool:
            if command == ["brew", "list", "bats-core"]:
                return True
            if command == ["brew", "list", "gh"]:
                return True
            if command == ["brew", "list", "shellcheck"]:
                return True
            if command == ["gh", "auth", "status"]:
                return False
            raise AssertionError(f"Unexpected command: {command}")

        with (
            mock.patch("base_dev.engine.command_exists", return_value=True),
            mock.patch("base_dev.engine.run_check", side_effect=fake_run_check),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 1)
        self.assertIn("gh-auth", stdout.getvalue())
        self.assertIn("GitHub CLI authentication is not ready.", stdout.getvalue())
        self.assertIn("Fix: gh auth login -h github.com", stdout.getvalue())

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
            with redirect_stdout(stdout):
                status = engine.doctor_dev_artifacts(manifest.artifacts, definitions, output_format="text")

        self.assertEqual(status, 0)
        self.assertIn("warn", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
