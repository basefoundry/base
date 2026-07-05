from __future__ import annotations

# pylint: disable=too-many-lines

import io
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup import artifacts, process, python_artifacts
from base_setup.artifacts import merge_artifacts
from base_setup.errors import ArtifactError
from base_setup.manifest import ArtifactRequest, read_manifest
from base_setup.process import format_command
from base_setup.prerequisites import PrerequisiteCheck
from base_setup.registry import get_artifact_definition, load_artifact_definitions
from base_setup.tests.helpers import fake_context, run_engine


class ArtifactFacadeTests(unittest.TestCase):
    def test_artifacts_declares_python_artifact_compatibility_exports(self) -> None:
        expected_names = {
            "PIP_INSTALL_COMMAND_PREFIX",
            "ProjectRuntimeConfig",
            "PYTHON_ARTIFACT_PROBE_TIMEOUT_SECONDS",
            "backup_existing_project_venv",
            "create_project_virtualenv",
            "ensure_existing_project_venv_matches_requirement",
            "pip_install_command",
            "project_python_interpreter",
            "project_runtime_config",
            "project_venv_dir",
            "project_venv_recreate_enabled",
            "python_artifact_installed",
            "python_package_requirement",
            "reconcile_python_artifact",
            "reconcile_python_artifacts",
            "reconcile_python_artifacts_sequential",
        }

        self.assertLessEqual(expected_names, set(artifacts.__all__))
        for name in expected_names:
            with self.subTest(name=name):
                self.assertIs(getattr(artifacts, name), getattr(python_artifacts, name))


class BaseSetupMainTests(unittest.TestCase):
    def test_main_reports_unknown_option_without_traceback(self) -> None:
        status, _stdout, stderr = run_engine(["--bad-option"])

        self.assertEqual(status, 2)
        self.assertIn("No such option", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_main_reports_missing_manifest_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"

            status, stdout, stderr = run_engine(["--manifest", str(manifest_path)])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("unable to read manifest", stderr)
        self.assertNotIn("Traceback", stderr)


class ArtifactMergeTests(unittest.TestCase):

    def test_merge_artifacts_keeps_defaults_and_manifest_artifacts(self) -> None:
        merged = merge_artifacts(
            (
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1"),
            ),
            (
                ArtifactRequest(artifact_type="tool", name="terraform", version="1.8.5"),
            ),
        )

        self.assertEqual(
            [(artifact.artifact_type, artifact.name, artifact.version, artifact.bootstrap) for artifact in merged],
            [
                ("python-package", "click", "8.4.1", False),
                ("tool", "terraform", "1.8.5", False),
            ],
        )



    def test_merge_artifacts_rejects_conflicting_default_versions(self) -> None:
        with self.assertRaises(ArtifactError):
            merge_artifacts(
                (
                    ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1"),
                ),
                (
                    ArtifactRequest(artifact_type="python-package", name="click", version="1.0.0"),
                ),
            )



class ArtifactRegistryTests(unittest.TestCase):

    def write_registry(self, root: Path, body: str) -> Path:
        path = root / "artifact-registry.yaml"
        path.write_text(body, encoding="utf-8")
        return path

    def test_base_manifest_declares_python_dev_tools(self) -> None:
        manifest = read_manifest(Path(__file__).resolve().parents[4] / "base_manifest.yaml")
        tools = {(artifact.artifact_type, artifact.name) for artifact in manifest.artifacts}

        self.assertIn(("python-package", "pylint"), tools)
        self.assertIn(("python-package", "pytest"), tools)
        self.assertIsNotNone(get_artifact_definition("python-package", "pylint"))
        self.assertIsNotNone(get_artifact_definition("python-package", "pytest"))



    def test_python_package_artifacts_are_pass_through_pip_packages(self) -> None:
        definition = get_artifact_definition("python-package", "rich")

        self.assertIsNotNone(definition)
        self.assertEqual(definition.name, "rich")
        self.assertEqual(definition.artifact_type, "python-package")
        self.assertEqual(definition.manager, "pip")
        self.assertEqual(definition.package, "rich")
        self.assertEqual(definition.target, "project-venv")



    def test_unknown_tool_artifacts_remain_unsupported(self) -> None:
        self.assertIsNone(get_artifact_definition("tool", "not-a-real-tool"))



    def test_base_dev_manifest_declares_supported_tools(self) -> None:
        manifest = read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "dev_manifest.yaml")
        tools = {(artifact.artifact_type, artifact.name) for artifact in manifest.artifacts}

        self.assertIn(("tool", "bats-core"), tools)
        self.assertIn(("tool", "gh"), tools)
        self.assertIn(("tool", "shellcheck"), tools)
        self.assertIsNotNone(get_artifact_definition("tool", "bats-core"))
        self.assertIsNotNone(get_artifact_definition("tool", "gh"))
        self.assertIsNotNone(get_artifact_definition("tool", "shellcheck"))

    def test_bats_core_uses_system_package_on_linux_debian(self) -> None:
        artifact = ArtifactRequest("tool", "bats-core", "latest")

        with mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}):
            definition = artifacts.resolve_artifact_definitions((artifact,))[0]

        self.assertEqual(definition.name, "bats-core")
        self.assertEqual(definition.manager, "system-package")
        self.assertEqual(definition.package, "bats")
        self.assertEqual(definition.target, "system")
        self.assertEqual(definition.check_kind, "system_command")



    def test_docker_and_colima_are_supported_tools(self) -> None:
        docker = get_artifact_definition("tool", "docker")
        colima = get_artifact_definition("tool", "colima")

        self.assertIsNotNone(docker)
        self.assertEqual(docker.package, "docker")
        self.assertEqual(docker.manager, "homebrew")
        self.assertIsNotNone(colima)
        self.assertEqual(colima.package, "colima")
        self.assertEqual(colima.manager, "homebrew")

    def test_builtin_artifact_definition_reports_registry_metadata(self) -> None:
        definition = get_artifact_definition("tool", "kubectl")

        self.assertIsNotNone(definition)
        self.assertEqual(definition.package, "kubernetes-cli")
        self.assertEqual(definition.version_policy, "latest-only")
        self.assertEqual(definition.check_kind, "homebrew_package")
        self.assertTrue(definition.registry_source.endswith("lib/base/artifact-registry.yaml"))

    def test_registry_validation_rejects_bad_entries(self) -> None:
        cases = {
            "unknown_field": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    unexpected: true\n"
                "    check:\n"
                "      kind: homebrew_package\n",
                "unsupported keys: unexpected",
            ),
            "missing_required": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check:\n"
                "      kind: homebrew_package\n",
                "missing required keys: package",
            ),
            "duplicate": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check:\n"
                "      kind: homebrew_package\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check:\n"
                "      kind: homebrew_package\n",
                "duplicate artifact definition: tool/terraform",
            ),
            "unsupported_manager": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: apt\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check:\n"
                "      kind: homebrew_package\n",
                "unsupported manager 'apt'",
            ),
            "unsupported_check_kind": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check:\n"
                "      kind: shell_command\n",
                "unsupported check kind 'shell_command'",
            ),
            "malformed_check": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check: []\n",
                "check must be a mapping",
            ),
            "missing_check_kind": (
                "version: 1\n"
                "artifacts:\n"
                "  - type: tool\n"
                "    name: terraform\n"
                "    manager: homebrew\n"
                "    package: terraform\n"
                "    target: system\n"
                "    version_policy: latest-only\n"
                "    check: {}\n",
                "check is missing required keys: kind",
            ),
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for name, (body, message) in cases.items():
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ArtifactError, message):
                        load_artifact_definitions(self.write_registry(root, body))



class ArtifactReconcileTests(unittest.TestCase):

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_unknown_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: not-a-real-artifact",
                        "    version: \"1.0\"",
                    ]
                ),
                encoding="utf-8",
            )

            status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 1)
        self.assertIn("Unsupported artifact 'not-a-real-artifact' of type 'tool'", stderr)



    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_unknown_python_package_artifact_dry_run_uses_pip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: python-package",
                        "    name: rich",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn(
            "pip install --disable-pip-version-check click==8.4.1 PyYAML==6.0.3 tomli==2.4.1 rich",
            stderr,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_dry_run_ignores_inherited_project_runtime_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(__file__).resolve().parents[4]
            inherited_venv_dir = Path(tmpdir) / "inherited-base-venv"
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: python-package",
                        "    name: rich",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {
                    "BASE_PROJECT": "base",
                    "BASE_PROJECT_ROOT": str(repo_root),
                    "BASE_PROJECT_MANIFEST": str(repo_root / "base_manifest.yaml"),
                    "BASE_PROJECT_VENV_DIR": str(inherited_venv_dir),
                },
            ):
                status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertNotIn(str(inherited_venv_dir), stderr)
        self.assertIn(
            "pip install --disable-pip-version-check click==8.4.1 PyYAML==6.0.3 tomli==2.4.1 rich",
            stderr,
        )

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_known_homebrew_artifact_dry_run_does_not_require_brew(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            with (
                mock.patch("base_setup.process.command_exists", return_value=False),
                mock.patch("base_setup.process.run_check") as run_check,
            ):
                status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install terraform", stderr)
        run_check.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_bats_core_artifact_dry_run_uses_system_package_on_linux_debian(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: bats-core",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}),
                mock.patch("base_setup.process.command_exists", return_value=False),
                mock.patch("base_setup.process.run_check") as run_check,
            ):
                status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertNotIn("brew install bats-core", stderr)
        self.assertIn("system package 'bats'", stderr)
        run_check.assert_not_called()



    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_docker_and_colima_artifacts_dry_run_through_homebrew(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: docker",
                        "    version: latest",
                        "  - type: tool",
                        "    name: colima",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            with (
                mock.patch("base_setup.process.command_exists", return_value=False),
                mock.patch("base_setup.process.run_check") as run_check,
            ):
                status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install docker", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install colima", stderr)
        run_check.assert_not_called()


    def test_bats_core_artifact_setup_accepts_installed_system_command_on_linux_debian(self) -> None:
        artifact = ArtifactRequest("tool", "bats-core", "latest")
        ctx = fake_context()

        with (
            mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}),
            mock.patch("base_setup.process.command_exists", return_value=True),
            mock.patch("base_setup.process.run_command") as run_command,
        ):
            definition = artifacts.resolve_artifact_definitions((artifact,))[0]
            artifacts.reconcile_artifact(ctx, definition, artifact.version, "demo", dry_run=False)

        run_command.assert_not_called()
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            "Artifact 'bats-core' is already available through system package 'bats'.",
            info_messages,
        )

    def test_bats_core_artifact_check_reports_missing_system_package_on_linux_debian(self) -> None:
        artifact = ArtifactRequest("tool", "bats-core", "latest")

        with (
            mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}),
            mock.patch("base_setup.process.command_exists", return_value=False),
        ):
            definition = artifacts.resolve_artifact_definitions((artifact,))[0]
            check = artifacts.check_artifact("demo", artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P034")
        self.assertIn("system package 'bats'", check.message)
        self.assertEqual(check.fix, "Run 'basectl setup --yes' or install Ubuntu/Debian package 'bats'.")


    def test_homebrew_artifact_rejects_non_latest_version(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)

        with self.assertRaisesRegex(ArtifactError, "only supports Homebrew artifact version 'latest'"):
            artifacts.reconcile_homebrew_artifact(fake_context(), definition, "1.8.5", dry_run=True)



    def test_homebrew_artifact_latest_invokes_brew_install(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
            "base_setup.process.run_check",
            return_value=False,
        ), mock.patch("base_setup.process.run_command") as run_command:
            artifacts.reconcile_homebrew_artifact(ctx, definition, "latest", dry_run=False)

        run_command.assert_called_once_with(ctx, ["brew", "install", "terraform"])


    def test_homebrew_artifact_latest_dry_run_upgrades_outdated_package(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)
        ctx = fake_context()
        outdated = subprocess.CompletedProcess(
            ["brew", "outdated", "terraform"],
            0,
            stdout="terraform\n",
            stderr="",
        )

        with (
            mock.patch("base_setup.process.command_exists", return_value=True),
            mock.patch("base_setup.process.run_check", return_value=True),
            mock.patch("base_setup.process.run_capture", return_value=outdated),
        ):
            artifacts.reconcile_homebrew_artifact(ctx, definition, "latest", dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("[DRY-RUN] Would run: brew upgrade terraform", info_messages)

    def test_homebrew_artifact_latest_upgrades_outdated_package(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)
        ctx = fake_context()
        outdated = subprocess.CompletedProcess(
            ["brew", "outdated", "terraform"],
            0,
            stdout="terraform\n",
            stderr="",
        )

        with (
            mock.patch("base_setup.process.command_exists", return_value=True),
            mock.patch("base_setup.process.run_check", return_value=True),
            mock.patch("base_setup.process.run_capture", return_value=outdated),
            mock.patch("base_setup.process.run_command") as run_command,
        ):
            artifacts.reconcile_homebrew_artifact(ctx, definition, "latest", dry_run=False)

        run_command.assert_called_once_with(ctx, ["brew", "upgrade", "terraform"])

    def test_homebrew_package_outdated_disables_homebrew_auto_update(self) -> None:
        completed = subprocess.CompletedProcess(
            ["brew", "outdated", "terraform"],
            0,
            stdout="terraform\n",
            stderr="",
        )

        with (
            mock.patch.dict(os.environ, {"HOMEBREW_NO_AUTO_UPDATE": "0"}),
            mock.patch("base_setup.process.run_capture", return_value=completed) as run_capture,
        ):
            self.assertTrue(artifacts.homebrew_package_outdated("terraform"))
            self.assertEqual(os.environ["HOMEBREW_NO_AUTO_UPDATE"], "0")

        run_capture.assert_called_once()
        self.assertEqual(
            run_capture.call_args.args[0],
            ["brew", "outdated", "terraform"],
        )
        self.assertEqual(run_capture.call_args.kwargs["env"]["HOMEBREW_NO_AUTO_UPDATE"], "1")

    def test_check_homebrew_artifact_uses_shared_prerequisite_core(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)
        artifact = ArtifactRequest("tool", "terraform", "latest")
        expected = PrerequisiteCheck(
            name="terraform",
            ok=True,
            message="shared Homebrew check",
            fix="",
            finding_id="BASE-P033",
            details={"source": "shared"},
        )

        with mock.patch("base_setup.artifacts.check_homebrew_package", return_value=expected) as check_homebrew_package:
            check = artifacts.check_homebrew_artifact("demo", artifact, definition)

        self.assertTrue(check.ok)
        self.assertEqual(check.message, "shared Homebrew check")
        self.assertEqual(check.finding_id, "BASE-P033")
        self.assertEqual(check.details, {"source": "shared"})
        request = check_homebrew_package.call_args.args[0]
        self.assertEqual(request.name, "terraform")
        self.assertEqual(request.package, "terraform")
        self.assertEqual(request.version, "latest")
        self.assertEqual(request.manager, "homebrew")

    def test_check_homebrew_artifact_warns_when_probe_times_out(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)
        artifact = ArtifactRequest("tool", "terraform", "latest")

        with (
            mock.patch("base_setup.process.command_exists", return_value=True),
            mock.patch(
                "base_setup.process.run_check",
                side_effect=subprocess.TimeoutExpired(
                    ["brew", "list", "terraform"],
                    process.DIAGNOSTIC_TIMEOUT_SECONDS,
                ),
            ) as run_check,
        ):
            check = artifacts.check_homebrew_artifact("demo", artifact, definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-P033")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, "Retry 'basectl doctor demo' or inspect Homebrew with 'brew doctor'.")
        run_check.assert_called_once_with(
            ["brew", "list", "terraform"],
            timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )

    def test_python_artifact_honors_project_venv_dir_override(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "custom-venv"
            with mock.patch.dict(
                os.environ,
                {"BASE_PROJECT": "demo", "BASE_PROJECT_VENV_DIR": str(venv_dir)},
            ), mock.patch("base_setup.python_artifacts.python_artifact_installed", return_value=False):
                artifacts.reconcile_python_artifact(ctx, definition, "latest", "demo", dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            f"[DRY-RUN] Would create project virtual environment at '{venv_dir}'.",
            info_messages,
        )
        self.assertIn(
            f"[DRY-RUN] Would run: {venv_dir}/bin/python -m pip install --disable-pip-version-check requests",
            info_messages,
        )

    def test_python_artifact_uses_manifest_project_not_environment(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "demo" / ".venv"
            with mock.patch.dict(os.environ, {"BASE_PROJECT": "wrong-project"}), mock.patch(
                "base_setup.python_artifacts.project_venv_dir",
                return_value=venv_dir,
            ) as project_venv_dir, mock.patch(
                "base_setup.python_artifacts.python_artifact_installed",
                return_value=False,
            ):
                artifacts.reconcile_python_artifact(ctx, definition, "latest", "demo", dry_run=True)

        project_venv_dir.assert_called_once_with("demo")

    def test_recreate_project_venv_backs_up_stale_venv_before_install(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            marker = root / "stale-python-ran"
            venv_dir = root / "demo" / ".venv"
            python_bin = venv_dir / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            (venv_dir / "pyvenv.cfg").write_text("home = /missing/python\n", encoding="utf-8")
            (venv_dir / "old.txt").write_text("old venv\n", encoding="utf-8")
            python_bin.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n", encoding="utf-8")
            python_bin.chmod(0o755)

            with (
                mock.patch.dict(os.environ, {"BASE_SETUP_RECREATE_PROJECT_VENV": "true"}),
                mock.patch("base_setup.python_artifacts.project_venv_dir", return_value=venv_dir),
                mock.patch("base_setup.python_artifacts.venv.create") as create_venv,
                mock.patch("base_setup.process.run_command") as run_command,
            ):
                artifacts.reconcile_python_artifact(ctx, definition, "latest", "demo", dry_run=False)

            backups = list((root / "demo").glob(".venv.backup.*"))

            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "old.txt").is_file())
            self.assertFalse((venv_dir / "old.txt").exists())
            self.assertFalse(marker.exists())
        create_venv.assert_called_once_with(venv_dir, with_pip=True)
        run_command.assert_called_once_with(
            ctx,
            [
                str(venv_dir / "bin" / "python"),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "requests",
            ],
        )

    def test_reconcile_artifacts_batches_python_installs(self) -> None:
        click = get_artifact_definition("python-package", "click")
        requests = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(click)
        self.assertIsNotNone(requests)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "venv"
            python_bin = venv_dir / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.touch()
            with mock.patch(
                "base_setup.python_artifacts.project_venv_dir",
                return_value=venv_dir,
            ), mock.patch("base_setup.python_artifacts.python_artifact_installed", return_value=False), mock.patch(
                "base_setup.process.run_command"
            ) as run_command:
                artifacts.reconcile_artifacts(
                    ctx,
                    (
                        ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1"),
                        ArtifactRequest(artifact_type="python-package", name="requests", version="latest"),
                    ),
                    (click, requests),
                    "demo",
                    dry_run=False,
                )

        run_command.assert_called_once_with(
            ctx,
            [
                str(python_bin),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "click==8.4.1",
                "requests",
            ],
        )

    def test_reconcile_artifacts_retries_python_installs_sequentially_after_batch_failure(self) -> None:
        click = get_artifact_definition("python-package", "click")
        requests = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(click)
        self.assertIsNotNone(requests)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "venv"
            python_bin = venv_dir / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.touch()
            with mock.patch(
                "base_setup.python_artifacts.project_venv_dir",
                return_value=venv_dir,
            ), mock.patch("base_setup.python_artifacts.python_artifact_installed", return_value=False), mock.patch(
                "base_setup.process.run_command",
                side_effect=[ArtifactError("batch failed"), None, None],
            ) as run_command:
                artifacts.reconcile_artifacts(
                    ctx,
                    (
                        ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1"),
                        ArtifactRequest(artifact_type="python-package", name="requests", version="latest"),
                    ),
                    (click, requests),
                    "demo",
                    dry_run=False,
                )

        self.assertEqual(
            run_command.call_args_list,
            [
                mock.call(
                    ctx,
                    [
                        str(python_bin),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "click==8.4.1",
                        "requests",
                    ],
                ),
                mock.call(
                    ctx,
                    [
                        str(python_bin),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "click==8.4.1",
                    ],
                ),
                mock.call(
                    ctx,
                    [
                        str(python_bin),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "requests",
                    ],
                ),
            ],
        )
        ctx.log.warning.assert_called_once_with(
            "Batch Python artifact install failed; retrying one artifact at a time."
        )



class EngineArtifactTests(unittest.TestCase):

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_discovers_manifest_from_start_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "nested"
            nested.mkdir()
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            status, _stdout, stderr = run_engine(["--dry-run", "--start-dir", str(nested)])

        self.assertEqual(status, 0)
        self.assertIn(f"Reading Base manifest at '{manifest_path.resolve()}'.", stderr)



    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_project_argument_validates_manifest_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                    ]
                ),
                encoding="utf-8",
            )

            status, _stdout, stderr = run_engine(["--manifest", str(manifest_path), "other"])

        self.assertEqual(status, 1)
        self.assertIn("project.name is 'demo', expected 'other'", stderr)



    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_empty_artifact_list_logs_that_base_defaults_are_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("Project 'demo' declares no artifacts; installing Base default artifacts only.", stderr)



class ProcessTests(unittest.TestCase):

    def test_format_command_uses_shell_quoting_for_empty_and_spaced_args(self) -> None:
        self.assertEqual(
            format_command(["tool", "", "two words", "plain"]),
            "tool '' 'two words' plain",
        )



    def test_run_command_includes_stderr_on_failure(self) -> None:
        ctx = fake_context()
        command = [
            sys.executable,
            "-c",
            "import sys; print('installer exploded', file=sys.stderr); raise SystemExit(17)",
        ]
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            with self.assertRaisesRegex(ArtifactError, "installer exploded"):
                process.run_command(ctx, command)

    def test_run_command_streams_and_logs_stdout_and_stderr(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        stderr = io.StringIO()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('install stdout'); "
                "print('install stderr', file=sys.stderr)"
            ),
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            process.run_command(ctx, command)

        self.assertIn("install stdout", stdout.getvalue())
        self.assertIn("install stderr", stderr.getvalue())
        debug_messages = [call.args[0] % call.args[1:] for call in ctx.log.debug.call_args_list]
        self.assertIn("Command stdout: install stdout", debug_messages)
        self.assertIn("Command stderr: install stderr", debug_messages)


    def test_run_command_failure_includes_bounded_stdout_and_stderr_tail(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        stderr = io.StringIO()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('stdout before failure'); "
                "print('stderr before failure', file=sys.stderr); "
                "raise SystemExit(17)"
            ),
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(ArtifactError) as exc:
                process.run_command(ctx, command)

        message = str(exc.exception)
        self.assertIn("Command failed with exit 17", message)
        self.assertIn("stdout:", message)
        self.assertIn("stdout before failure", message)
        self.assertIn("stderr:", message)
        self.assertIn("stderr before failure", message)

    def test_run_command_failure_adds_homebrew_link_conflict_guidance(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        stderr = io.StringIO()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('Error: The `brew link` step did not complete successfully', file=sys.stderr); "
                "print('To list all files that would be deleted:', file=sys.stderr); "
                "print('  brew link --overwrite python@3.14 --dry-run', file=sys.stderr); "
                "raise SystemExit(1)"
            ),
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(ArtifactError) as exc:
                process.run_command(ctx, command)

        message = str(exc.exception)
        self.assertIn("Homebrew reported a link conflict while installing a dependency.", message)
        self.assertIn("brew link --overwrite python@3.14 --dry-run", message)
        self.assertIn("brew link --overwrite python@3.14", message)
        self.assertIn("Then rerun the Base command.", message)

    def test_run_command_redacts_sensitive_output_from_logs_and_failure(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        stderr = io.StringIO()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('url=https://user:secret@example.invalid/pkg.whl'); "
                "print('token=super-secret', file=sys.stderr); "
                "raise SystemExit(9)"
            ),
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(ArtifactError) as exc:
                process.run_command(ctx, command)

        message = str(exc.exception)
        debug_text = "\n".join(str(call.args) for call in ctx.log.debug.call_args_list)
        self.assertNotIn("super-secret", message)
        self.assertNotIn("super-secret", debug_text)
        self.assertNotIn("user:secret", message)
        self.assertNotIn("user:secret", debug_text)
        self.assertIn("[REDACTED]", message)
        self.assertIn("[REDACTED]", debug_text)

    def test_redact_command_output_redacts_compound_secret_assignments(self) -> None:
        output = "\n".join(
            [
                "token=ghp_short",
                "--github-token=ghp_flag",
                "GITHUB_TOKEN=ghp_compound",
                "DB_PASSWORD=db-secret",
                "SOME_SECRET=value-secret",
                "API_KEY=api-secret",
                "AWS_SECRET_ACCESS_KEY=aws-secret",
                "authorization=auth-secret",
                "AUTHORIZATION=auth-token",
            ]
        )

        redacted = process.redact_command_output(output)

        self.assertNotIn("ghp_short", redacted)
        self.assertNotIn("ghp_flag", redacted)
        self.assertNotIn("ghp_compound", redacted)
        self.assertNotIn("db-secret", redacted)
        self.assertNotIn("value-secret", redacted)
        self.assertNotIn("api-secret", redacted)
        self.assertNotIn("aws-secret", redacted)
        self.assertNotIn("auth-secret", redacted)
        self.assertNotIn("auth-token", redacted)
        self.assertIn("token=[REDACTED]", redacted)
        self.assertIn("--github-token=[REDACTED]", redacted)
        self.assertIn("GITHUB_TOKEN=[REDACTED]", redacted)
        self.assertIn("DB_PASSWORD=[REDACTED]", redacted)
        self.assertIn("SOME_SECRET=[REDACTED]", redacted)
        self.assertIn("API_KEY=[REDACTED]", redacted)
        self.assertIn("AWS_SECRET_ACCESS_KEY=[REDACTED]", redacted)
        self.assertIn("authorization=[REDACTED]", redacted)
        self.assertIn("AUTHORIZATION=[REDACTED]", redacted)

    def test_run_command_failure_truncates_large_single_chunk_tail(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.write('x' * 5000 + 'tail-marker'); "
                "raise SystemExit(17)"
            ),
        ]

        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            with self.assertRaises(ArtifactError) as exc:
                process.run_command(ctx, command)

        message = str(exc.exception)
        self.assertLessEqual(
            len(message.split("stdout:\n", 1)[1]),
            process.COMMAND_OUTPUT_TAIL_CHARS,
        )
        self.assertIn("tail-marker", message)

    def test_run_command_logs_success_at_debug(self) -> None:
        ctx = fake_context()
        command = [sys.executable, "-c", ""]

        process.run_command(ctx, command)

        ctx.log.debug.assert_called_once_with(
            "Command succeeded: %s",
            format_command(command),
        )
