from __future__ import annotations

# pylint: disable=too-many-lines,too-many-public-methods

import io
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_cli.config import UserConfig, UserIdeConfig, UserIdePreference
from base_setup import engine
from base_setup.engine import ArtifactError, format_command, main, merge_artifacts
from base_setup.manifest import ArtifactRequest, BaseManifest, IdeConfig, ManifestError
from base_setup.manifest import read_manifest
from base_setup.registry import get_artifact_definition


def run_engine(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(os.environ, {"HOME": home_dir, "BASE_HOME": str(Path(__file__).resolve().parents[4])}):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def fake_context() -> mock.Mock:
    ctx = mock.Mock()
    ctx.log = mock.Mock()
    return ctx


class ManifestTests(unittest.TestCase):
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

    def test_format_command_uses_shell_quoting_for_empty_and_spaced_args(self) -> None:
        self.assertEqual(
            format_command(["tool", "", "two words", "plain"]),
            "tool '' 'two words' plain",
        )

    def test_reads_basic_manifest(self) -> None:
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
                        "    version: \"1.8.5\"",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.project_name, "demo")
        self.assertIsNone(manifest.brewfile)
        self.assertEqual(manifest.artifacts[0].artifact_type, "tool")
        self.assertEqual(manifest.artifacts[0].name, "terraform")
        self.assertEqual(manifest.artifacts[0].version, "1.8.5")
        self.assertFalse(manifest.artifacts[0].bootstrap)

    def test_reads_manifest_brewfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "brewfile: Brewfile",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.brewfile, "Brewfile")

    def test_reads_manifest_mise_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "mise: .mise.toml",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.mise, ".mise.toml")

    def test_reads_manifest_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: pytest tests/",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.test)
        self.assertEqual(manifest.test.command, "pytest tests/")
        self.assertIsNone(manifest.test.mise)

    def test_reads_manifest_test_mise_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  mise: test",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.test)
        self.assertIsNone(manifest.test.command)
        self.assertEqual(manifest.test.mise, "test")

    def test_rejects_invalid_manifest_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: \"\"",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "test.command must be a non-empty string"):
                read_manifest(manifest_path)

    def test_rejects_ambiguous_manifest_test_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: pytest",
                        "  mise: test",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "test must declare only one of command or mise"):
                read_manifest(manifest_path)

    def test_reads_ide_manifest_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    install: true",
                        "    extensions:",
                        "      - ms-python.python",
                        "      - github.copilot",
                        "    settings:",
                        "      editor.formatOnSave: true",
                        "      editor.rulers: [100]",
                        "      python.defaultInterpreterPath: auto",
                        "  cursor:",
                        "    extensions:",
                        "      - ms-python.python",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(set(manifest.ide), {"vscode", "cursor"})
        self.assertTrue(manifest.ide["vscode"].install)
        self.assertEqual(
            manifest.ide["vscode"].extensions,
            ("ms-python.python", "github.copilot"),
        )
        self.assertEqual(
            manifest.ide["vscode"].settings,
            {
                "editor.formatOnSave": True,
                "editor.rulers": [100],
                "python.defaultInterpreterPath": "auto",
            },
        )
        self.assertFalse(manifest.ide["cursor"].install)
        self.assertEqual(manifest.ide["cursor"].extensions, ("ms-python.python",))
        self.assertEqual(manifest.ide["cursor"].settings, {})

    def test_rejects_unknown_ide_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  windows-notepad:",
                        "    extensions: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "unsupported IDE names: windows-notepad"):
                read_manifest(manifest_path)

    def test_rejects_invalid_ide_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    extensions:",
                        "      - ms-python.python",
                        "      - 123",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, r"ide.vscode.extensions\[2\] must be a non-empty string"):
                read_manifest(manifest_path)

    def test_rejects_non_boolean_ide_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    install: maybe",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "ide.vscode.install must be a boolean"):
                read_manifest(manifest_path)

    def test_rejects_unsupported_auto_ide_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    settings:",
                        "      editor.defaultFormatter: auto",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "does not support the special value 'auto'"):
                read_manifest(manifest_path)

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
        self.assertIsNotNone(get_artifact_definition("tool", "bats-core"))
        self.assertIsNotNone(get_artifact_definition("tool", "gh"))

    def test_docker_and_colima_are_supported_tools(self) -> None:
        docker = get_artifact_definition("tool", "docker")
        colima = get_artifact_definition("tool", "colima")

        self.assertIsNotNone(docker)
        self.assertEqual(docker.package, "docker")
        self.assertEqual(docker.manager, "homebrew")
        self.assertIsNotNone(colima)
        self.assertEqual(colima.package, "colima")
        self.assertEqual(colima.manager, "homebrew")

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
        self.assertIn("pip install rich", stderr)

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

            status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install terraform", stderr)

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

            status, _stdout, stderr = run_engine(["--dry-run", "--manifest", str(manifest_path)])

        self.assertEqual(status, 0)
        self.assertIn("[DRY-RUN] Would run: brew install docker", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install colima", stderr)

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

    def test_homebrew_artifact_rejects_non_latest_version(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)

        with self.assertRaisesRegex(ArtifactError, "only supports Homebrew artifact version 'latest'"):
            engine.reconcile_homebrew_artifact(fake_context(), definition, "1.8.5", dry_run=True)

    def test_homebrew_artifact_latest_invokes_brew_install(self) -> None:
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.run_check",
            return_value=False,
        ), mock.patch("base_setup.engine.run_command") as run_command:
            engine.reconcile_homebrew_artifact(ctx, definition, "latest", dry_run=False)

        run_command.assert_called_once_with(ctx, ["brew", "install", "terraform"])

    def test_python_artifact_honors_project_venv_dir_override(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "custom-venv"
            with mock.patch.dict(
                os.environ,
                {"BASE_PROJECT": "wrong-project", "BASE_PROJECT_VENV_DIR": str(venv_dir)},
            ), mock.patch("base_setup.engine.python_artifact_installed", return_value=False):
                engine.reconcile_python_artifact(ctx, definition, "latest", "demo", dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            f"[DRY-RUN] Would create project virtual environment at '{venv_dir}'.",
            info_messages,
        )
        self.assertIn(
            f"[DRY-RUN] Would run: {venv_dir}/bin/python -m pip install requests",
            info_messages,
        )

    def test_python_artifact_uses_manifest_project_not_environment(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "demo" / ".venv"
            with mock.patch.dict(os.environ, {"BASE_PROJECT": "wrong-project"}), mock.patch(
                "base_setup.engine.project_venv_dir",
                return_value=venv_dir,
            ) as project_venv_dir, mock.patch("base_setup.engine.python_artifact_installed", return_value=False):
                engine.reconcile_python_artifact(ctx, definition, "latest", "demo", dry_run=True)

        project_venv_dir.assert_called_once_with("demo")

    def test_run_command_includes_stderr_on_failure(self) -> None:
        ctx = fake_context()

        with mock.patch(
            "base_setup.engine.subprocess.run",
            return_value=mock.Mock(returncode=17, stderr="installer exploded\n"),
        ):
            with self.assertRaisesRegex(ArtifactError, "installer exploded"):
                engine.run_command(ctx, ["installer", "--bad"])

    def test_run_command_logs_success_at_debug(self) -> None:
        ctx = fake_context()

        with mock.patch(
            "base_setup.engine.subprocess.run",
            return_value=mock.Mock(returncode=0, stderr=""),
        ):
            engine.run_command(ctx, ["installer", "--good", "two words"])

        ctx.log.debug.assert_called_once_with(
            "Command succeeded: %s",
            "installer --good 'two words'",
        )

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

    def test_empty_artifact_list_is_supported(self) -> None:
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

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.project_name, "demo")
        self.assertEqual(manifest.artifacts, ())

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


class BootstrapManifestTests(unittest.TestCase):
    def test_reconcile_bootstrap_artifacts_uses_only_bootstrap_defaults(self) -> None:
        ctx = fake_context()
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="__base_defaults__",
            brewfile=None,
            artifacts=(
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1", bootstrap=True),
                ArtifactRequest(artifact_type="python-package", name="pytest", version="latest"),
            ),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )

        with mock.patch("base_setup.engine.reconcile_artifact") as reconcile_artifact:
            engine.reconcile_bootstrap_artifacts(ctx, default_manifest, manifest, dry_run=True)

        self.assertEqual(reconcile_artifact.call_count, 1)
        self.assertEqual(reconcile_artifact.call_args.args[1].name, "click")
        self.assertEqual(reconcile_artifact.call_args.args[3], "demo")

    def test_merge_artifacts_preserves_default_bootstrap_marker(self) -> None:
        merged = merge_artifacts(
            (
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1", bootstrap=True),
            ),
            (
                ArtifactRequest(artifact_type="python-package", name="click", version="8.4.1"),
            ),
        )

        self.assertTrue(merged[0].bootstrap)

    def test_reads_bootstrap_artifact_marker(self) -> None:
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
                        "    name: click",
                        "    version: \"8.4.1\"",
                        "    bootstrap: true",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertTrue(manifest.artifacts[0].bootstrap)

    def test_rejects_non_boolean_bootstrap_marker(self) -> None:
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
                        "    name: click",
                        "    version: \"8.4.1\"",
                        "    bootstrap: \"yes\"",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "bootstrap must be a boolean"):
                read_manifest(manifest_path)

    def test_default_manifest_marks_python_bootstrap_packages(self) -> None:
        manifest = read_manifest(Path(__file__).resolve().parents[4] / "lib" / "base" / "default_manifest.yaml")
        bootstrap_artifacts = {
            (artifact.artifact_type, artifact.name): artifact.bootstrap for artifact in manifest.artifacts
        }

        self.assertEqual(
            bootstrap_artifacts,
            {
                ("python-package", "click"): True,
                ("python-package", "PyYAML"): True,
            },
        )


class ProjectCheckTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_reports_project_artifacts(self) -> None:
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
                        "    name: requests",
                        "    version: latest",
                    ]
                ),
                encoding="utf-8",
            )

            status, stdout, _stderr = run_engine(
                ["--action", "check", "--format", "json", "--manifest", str(manifest_path), "demo"]
            )

        self.assertEqual(status, 1)
        self.assertIn('"name": "requests"', stdout)
        self.assertIn('"ok": false', stdout)
        self.assertIn('"fix": "basectl setup demo"', stdout)

    def test_check_homebrew_artifact_reports_missing_package(self) -> None:
        artifact = ArtifactRequest(artifact_type="tool", name="terraform", version="latest")
        definition = get_artifact_definition("tool", "terraform")
        self.assertIsNotNone(definition)

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.run_check",
            return_value=False,
        ):
            check = engine.check_homebrew_artifact("demo", artifact, definition)

        self.assertFalse(check.ok)
        self.assertIn("not installed via Homebrew package 'terraform'", check.message)
        self.assertEqual(check.fix, "basectl setup demo")

    def test_doctor_manifest_counts_failed_project_artifacts(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(ArtifactRequest(artifact_type="python-package", name="requests", version="latest"),),
        )

        with redirect_stdout(io.StringIO()) as stdout:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 1)
        self.assertIn("Project doctor: demo", stdout.getvalue())
        self.assertIn("Fix: basectl setup demo", stdout.getvalue())

    def test_doctor_manifest_supports_json_output(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(ArtifactRequest(artifact_type="python-package", name="requests", version="latest"),),
        )

        with redirect_stdout(io.StringIO()) as stdout:
            status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(findings[0]["status"], "error")
        self.assertEqual(findings[0]["fix"], "basectl setup demo")

    def test_doctor_warning_status_does_not_fail(self) -> None:
        check = engine.ArtifactCheck(
            name="optional-artifact",
            ok=False,
            message="Optional project artifact is not installed.",
            fix="basectl setup demo",
            status="warn",
        )

        self.assertEqual(engine.doctor_status(check), "warn")
        self.assertEqual(engine.check_to_doctor_json(check)["status"], "warn")

        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )
        with mock.patch("base_setup.engine.manifest_checks", return_value=(check,)):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        self.assertEqual(status, 0)
        self.assertIn("warn", stdout.getvalue())


class BrewfileTests(unittest.TestCase):
    def test_brewfile_dry_run_invokes_brew_bundle(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text("brew \"jq\"\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            engine.reconcile_brewfile(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"[DRY-RUN] Would run: brew bundle --file={expected_brewfile}", info_messages)

    def test_brewfile_invokes_brew_bundle(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            brewfile = project_root / "Brewfile"
            brewfile.write_text("brew \"jq\"\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )
            expected_brewfile = brewfile.resolve()

            with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
                "base_setup.engine.run_command"
            ) as run_command:
                engine.reconcile_brewfile(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["brew", "bundle", f"--file={expected_brewfile}"])

    def test_brewfile_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="Brewfile",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "does not exist"):
                engine.resolve_brewfile_path(manifest)

    def test_brewfile_must_stay_inside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile="../Brewfile",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "must stay inside the project root"):
                engine.resolve_brewfile_path(manifest)

    def test_mise_dry_run_invokes_mise_install_in_project_root(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            engine.reconcile_mise(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"[DRY-RUN] Would run in '{project_root.resolve()}': mise install", info_messages)

    def test_mise_invokes_install_in_project_root(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
                "base_setup.engine.run_command"
            ) as run_command:
                engine.reconcile_mise(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["mise", "install"], cwd=project_root.resolve())

    def test_mise_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "mise config '.mise.toml' does not exist"):
                engine.resolve_mise_path(manifest)

    def test_mise_must_stay_inside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise="../.mise.toml",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "mise must stay inside the project root"):
                engine.resolve_mise_path(manifest)

    def test_manifest_checks_include_mise_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            default_manifest = BaseManifest(
                path=Path(tmpdir) / "default.yaml",
                project_name="base",
                brewfile=None,
                artifacts=(),
            )
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with mock.patch("base_setup.engine.command_exists", return_value=True):
                checks = engine.manifest_checks(default_manifest, manifest)

        self.assertIn("mise", [check.name for check in checks])
        mise_check = next(check for check in checks if check.name == "mise")
        self.assertFalse(mise_check.ok)
        self.assertEqual(mise_check.status, "warn")
        self.assertIn("installed mise tools are not verified", mise_check.message)
        self.assertEqual(mise_check.fix, "Run 'basectl setup demo' to install declared mise tools.")


class IdeInstallTests(unittest.TestCase):
    def test_ide_install_dry_run_invokes_homebrew_cask_install(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(install=True, extensions=(), settings={}),
                "cursor": IdeConfig(install=False, extensions=(), settings={}),
            },
        )

        engine.reconcile_ide_installs(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("[DRY-RUN] Would run: brew install --cask visual-studio-code", info_messages)
        self.assertEqual(len(info_messages), 1)

    def test_ide_install_skips_existing_cask_and_reports_available_cli(self) -> None:
        ctx = fake_context()
        definition = engine.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.run_check",
            return_value=True,
        ), mock.patch("base_setup.engine.run_command") as run_command:
            engine.reconcile_ide_install(ctx, definition, dry_run=False)

        run_command.assert_not_called()
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("VS Code is already installed via Homebrew cask 'visual-studio-code'.", info_messages)
        self.assertIn("VS Code CLI 'code' is available on PATH.", info_messages)

    def test_ide_install_installs_missing_cask(self) -> None:
        ctx = fake_context()
        definition = engine.IDE_DEFINITIONS["cursor"]

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.run_check",
            return_value=False,
        ), mock.patch("base_setup.engine.run_command") as run_command:
            engine.reconcile_ide_install(ctx, definition, dry_run=False)

        run_command.assert_called_once_with(ctx, ["brew", "install", "--cask", "cursor"])

    def test_ide_install_warns_when_cli_is_missing_after_install(self) -> None:
        ctx = fake_context()
        definition = engine.IDE_DEFINITIONS["vscode"]

        def command_exists(name: str) -> bool:
            return name == "brew"

        with mock.patch("base_setup.engine.command_exists", side_effect=command_exists), mock.patch(
            "base_setup.engine.run_check",
            return_value=True,
        ):
            engine.reconcile_ide_install(ctx, definition, dry_run=False)

        warning_messages = [call.args[0] % call.args[1:] for call in ctx.log.warning.call_args_list]
        self.assertIn(
            "VS Code is installed, but CLI 'code' is not on PATH. Enable the IDE shell command before extension setup.",
            warning_messages,
        )

    def test_check_ide_install_reports_missing_cask(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.run_check",
            return_value=False,
        ):
            check = engine.check_ide_install("demo", definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.name, "VS Code app")
        self.assertIn("Homebrew cask 'visual-studio-code'", check.message)
        self.assertEqual(check.fix, "basectl setup demo")

    def test_check_ide_install_reports_missing_cli(self) -> None:
        definition = engine.IDE_DEFINITIONS["cursor"]

        def command_exists(name: str) -> bool:
            return name == "brew"

        with mock.patch("base_setup.engine.command_exists", side_effect=command_exists), mock.patch(
            "base_setup.engine.run_check",
            return_value=True,
        ):
            check = engine.check_ide_install("demo", definition)

        self.assertFalse(check.ok)
        self.assertEqual(check.name, "Cursor CLI")
        self.assertIn("CLI 'cursor' is not on PATH", check.message)
        self.assertIn("Enable the 'cursor' shell command", check.fix)

    def test_manifest_checks_include_requested_ide_installs(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={"vscode": IdeConfig(install=True, extensions=(), settings={})},
        )

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.run_check",
            return_value=True,
        ):
            checks = engine.manifest_checks(default_manifest, manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].name, "VS Code app")
        self.assertTrue(checks[0].ok)


class IdeExtensionTests(unittest.TestCase):
    def test_ide_extensions_dry_run_prints_install_commands(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        engine.reconcile_ide_extensions(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertEqual(
            info_messages,
            [
                "[DRY-RUN] Would run: code --install-extension ms-python.python",
                "[DRY-RUN] Would run: code --install-extension github.copilot",
            ],
        )

    def test_ide_extensions_skip_installed_extensions(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.list_ide_extensions",
            return_value={"ms-python.python", "github.copilot"},
        ), mock.patch("base_setup.engine.run_command") as run_command:
            engine.reconcile_ide_extensions(ctx, manifest, dry_run=False)

        run_command.assert_not_called()

    def test_ide_extensions_install_missing_extensions(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "cursor": IdeConfig(
                    install=False,
                    extensions=("ms-python.python", "github.copilot"),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.list_ide_extensions",
            return_value={"ms-python.python"},
        ), mock.patch("base_setup.engine.run_command") as run_command:
            engine.reconcile_ide_extensions(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["cursor", "--install-extension", "github.copilot"])

    def test_ide_extensions_warn_when_cli_is_missing(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python",),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.engine.command_exists", return_value=False):
            engine.reconcile_ide_extensions(ctx, manifest, dry_run=False)

        warning_messages = [call.args[0] % call.args[1:] for call in ctx.log.warning.call_args_list]
        self.assertIn("VS Code CLI 'code' is not on PATH; skipping extension setup.", warning_messages)

    def test_list_ide_extensions_returns_installed_extension_ids(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with mock.patch(
            "base_setup.engine.subprocess.run",
            return_value=mock.Mock(returncode=0, stdout="ms-python.python\n\ngithub.copilot\n", stderr=""),
        ):
            extensions = engine.list_ide_extensions(definition)

        self.assertEqual(extensions, {"ms-python.python", "github.copilot"})

    def test_list_ide_extensions_includes_stderr_on_failure(self) -> None:
        definition = engine.IDE_DEFINITIONS["cursor"]

        with mock.patch(
            "base_setup.engine.subprocess.run",
            return_value=mock.Mock(returncode=1, stdout="", stderr="extensions unavailable\n"),
        ):
            with self.assertRaisesRegex(ArtifactError, "extensions unavailable"):
                engine.list_ide_extensions(definition)

    def test_check_ide_extension_reports_installed_extension(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.list_ide_extensions",
            return_value={"ms-python.python"},
        ):
            check = engine.check_ide_extension("demo", definition, "ms-python.python")

        self.assertTrue(check.ok)
        self.assertEqual(check.name, "ms-python.python")
        self.assertIn("is installed", check.message)

    def test_check_ide_extension_reports_missing_extension(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.list_ide_extensions",
            return_value=set(),
        ):
            check = engine.check_ide_extension("demo", definition, "ms-python.python")

        self.assertFalse(check.ok)
        self.assertEqual(check.fix, "basectl setup demo")
        self.assertIn("is not installed", check.message)

    def test_check_ide_extension_reports_missing_cli(self) -> None:
        definition = engine.IDE_DEFINITIONS["cursor"]

        with mock.patch("base_setup.engine.command_exists", return_value=False):
            check = engine.check_ide_extension("demo", definition, "github.copilot")

        self.assertFalse(check.ok)
        self.assertIn("CLI 'cursor' is not on PATH", check.message)
        self.assertIn("basectl setup demo", check.fix)

    def test_manifest_checks_include_ide_extensions(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=("ms-python.python",),
                    settings={},
                )
            },
        )

        with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
            "base_setup.engine.list_ide_extensions",
            return_value={"ms-python.python"},
        ):
            checks = engine.manifest_checks(default_manifest, manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].name, "ms-python.python")
        self.assertTrue(checks[0].ok)


class IdeSettingsTests(unittest.TestCase):
    def test_resolve_ide_settings_auto_interpreter_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "demo-venv"
            with mock.patch.dict(os.environ, {"BASE_PROJECT_VENV_DIR": str(venv_dir)}):
                settings = engine.resolve_ide_settings(
                    "demo",
                    {
                        "python.defaultInterpreterPath": "auto",
                        "editor.formatOnSave": True,
                    },
                )

        self.assertEqual(settings["python.defaultInterpreterPath"], str(venv_dir / "bin" / "python"))
        self.assertTrue(settings["editor.formatOnSave"])

    def test_ide_settings_file_uses_macos_application_support(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir}, clear=False), mock.patch(
                "base_setup.engine.sys.platform", "darwin"
            ):
                settings_file = engine.ide_settings_file(definition)

        self.assertEqual(
            settings_file,
            Path(home_dir) / "Library" / "Application Support" / "Code" / "User" / "settings.json",
        )

    def test_ide_settings_file_uses_xdg_config_home_off_macos(self) -> None:
        definition = engine.IDE_DEFINITIONS["cursor"]

        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            config_home = Path(tmpdir) / "xdg-config"
            home_dir.mkdir()
            with mock.patch.dict(
                os.environ,
                {"HOME": str(home_dir), "XDG_CONFIG_HOME": str(config_home)},
                clear=False,
            ), mock.patch("base_setup.engine.sys.platform", "linux"):
                settings_file = engine.ide_settings_file(definition)

        self.assertEqual(settings_file, config_home / "Cursor" / "User" / "settings.json")

    def test_ide_settings_file_defaults_to_home_config_off_macos(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}, clear=False), mock.patch(
                "base_setup.engine.sys.platform", "linux"
            ):
                settings_file = engine.ide_settings_file(definition)

        self.assertEqual(settings_file, Path(home_dir) / ".config" / "Code" / "User" / "settings.json")

    def test_merge_ide_settings_writes_missing_keys(self) -> None:
        ctx = fake_context()
        definition = engine.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                engine.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.formatOnSave": True},
                    dry_run=False,
                )
                settings_file = engine.ide_settings_file(definition)
                settings = json.loads(settings_file.read_text(encoding="utf-8"))

        self.assertEqual(settings, {"editor.formatOnSave": True})

    def test_merge_ide_settings_preserves_existing_user_value(self) -> None:
        ctx = fake_context()
        definition = engine.IDE_DEFINITIONS["cursor"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = engine.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(
                    json.dumps({"editor.formatOnSave": False}),
                    encoding="utf-8",
                )

                engine.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.formatOnSave": True, "editor.rulers": [100]},
                    dry_run=False,
                )
                settings = json.loads(settings_file.read_text(encoding="utf-8"))

        self.assertEqual(settings["editor.formatOnSave"], False)
        self.assertEqual(settings["editor.rulers"], [100])
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn("Cursor setting 'editor.formatOnSave' already set by user; leaving intact.", info_messages)

    def test_merge_ide_settings_dry_run_does_not_write(self) -> None:
        ctx = fake_context()
        definition = engine.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                engine.merge_ide_settings(
                    ctx,
                    definition,
                    {"editor.formatOnSave": True},
                    dry_run=True,
                )
                settings_file = engine.ide_settings_file(definition)

        self.assertFalse(settings_file.exists())
        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            "[DRY-RUN] Would set VS Code user setting 'editor.formatOnSave' to true.",
            info_messages,
        )

    def test_reconcile_ide_settings_uses_manifest_settings(self) -> None:
        ctx = fake_context()
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with mock.patch("base_setup.engine.merge_ide_settings") as merge_settings:
            engine.reconcile_ide_settings(ctx, manifest, dry_run=True)

        merge_settings.assert_called_once_with(
            ctx,
            engine.IDE_DEFINITIONS["vscode"],
            {"editor.formatOnSave": True},
            dry_run=True,
        )

    def test_check_ide_setting_reports_absent_key(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                check = engine.check_ide_setting("demo", definition, "editor.formatOnSave", True)

        self.assertFalse(check.ok)
        self.assertIn("is absent", check.message)
        self.assertEqual(check.fix, "basectl setup demo")

    def test_check_ide_setting_reports_matching_key(self) -> None:
        definition = engine.IDE_DEFINITIONS["vscode"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = engine.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                check = engine.check_ide_setting("demo", definition, "editor.formatOnSave", True)

        self.assertTrue(check.ok)
        self.assertIn("matches", check.message)

    def test_check_ide_setting_reports_divergent_key(self) -> None:
        definition = engine.IDE_DEFINITIONS["cursor"]

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = engine.ide_settings_file(definition)
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": False}), encoding="utf-8")
                check = engine.check_ide_setting("demo", definition, "editor.formatOnSave", True)

        self.assertFalse(check.ok)
        self.assertIn("Base will not overwrite user settings", check.message)
        self.assertIn("remove the key", check.fix)

    def test_check_ide_settings_includes_manifest_settings(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = engine.ide_settings_file(engine.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                checks = engine.check_ide_settings(manifest)

        self.assertEqual(len(checks), 1)
        self.assertTrue(checks[0].ok)


class UserIdePreferenceMergeTests(unittest.TestCase):
    def test_effective_ide_config_adds_user_extensions_and_settings(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=True,
                    extensions=("ms-python.python",),
                    settings={"python.defaultInterpreterPath": "auto"},
                )
            },
        )
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=True,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=True,
                        install=None,
                        extra_extensions=("eamodio.gitlens", "ms-python.python"),
                        settings={"editor.fontSize": 14},
                    )
                },
            ),
        )

        effective = engine.effective_manifest_with_user_config(manifest, user_config)

        vscode = effective.ide["vscode"]
        self.assertTrue(vscode.install)
        self.assertEqual(vscode.extensions, ("ms-python.python", "eamodio.gitlens"))
        self.assertEqual(
            vscode.settings,
            {
                "editor.fontSize": 14,
                "python.defaultInterpreterPath": "auto",
            },
        )

    def test_effective_ide_config_project_setting_wins_over_user_setting(self) -> None:
        project_ide = {
            "vscode": IdeConfig(
                install=False,
                extensions=(),
                settings={"editor.formatOnSave": True},
            )
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=None,
                        install=None,
                        extra_extensions=(),
                        settings={"editor.formatOnSave": False, "editor.fontSize": 14},
                    )
                },
            ),
        )

        effective = engine.effective_ide_config(project_ide, user_config)

        self.assertEqual(
            effective["vscode"].settings,
            {"editor.formatOnSave": True, "editor.fontSize": 14},
        )

    def test_effective_ide_config_user_install_preference_overrides_project_install(self) -> None:
        project_ide = {
            "cursor": IdeConfig(
                install=True,
                extensions=("github.copilot",),
                settings={},
            )
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "cursor": UserIdePreference(
                        enabled=None,
                        install=False,
                        extra_extensions=(),
                        settings={},
                    )
                },
            ),
        )

        effective = engine.effective_ide_config(project_ide, user_config)

        self.assertFalse(effective["cursor"].install)
        self.assertEqual(effective["cursor"].extensions, ("github.copilot",))

    def test_effective_ide_config_can_disable_all_ide_work(self) -> None:
        project_ide = {
            "vscode": IdeConfig(
                install=True,
                extensions=("ms-python.python",),
                settings={"editor.formatOnSave": True},
            )
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(enabled=False, preferences={}),
        )

        self.assertEqual(engine.effective_ide_config(project_ide, user_config), {})

    def test_effective_ide_config_can_disable_one_ide(self) -> None:
        project_ide = {
            "vscode": IdeConfig(install=True, extensions=(), settings={}),
            "cursor": IdeConfig(install=True, extensions=(), settings={}),
        }
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "cursor": UserIdePreference(
                        enabled=False,
                        install=None,
                        extra_extensions=(),
                        settings={},
                    )
                },
            ),
        )

        effective = engine.effective_ide_config(project_ide, user_config)

        self.assertEqual(set(effective), {"vscode"})

    def test_effective_ide_config_includes_user_only_ide_preferences(self) -> None:
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=None,
                        install=False,
                        extra_extensions=("eamodio.gitlens",),
                        settings={"editor.fontSize": 14},
                    )
                },
            ),
        )

        effective = engine.effective_ide_config({}, user_config)

        self.assertEqual(set(effective), {"vscode"})
        self.assertFalse(effective["vscode"].install)
        self.assertEqual(effective["vscode"].extensions, ("eamodio.gitlens",))

    def test_ide_preference_warning_checks_report_setting_conflicts(self) -> None:
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )
        user_config = UserConfig(
            raw={},
            ide=UserIdeConfig(
                enabled=None,
                preferences={
                    "vscode": UserIdePreference(
                        enabled=None,
                        install=None,
                        extra_extensions=(),
                        settings={"editor.formatOnSave": False},
                    )
                },
            ),
        )

        checks = engine.ide_preference_warning_checks(manifest, user_config)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].status, "warn")
        self.assertIn("is ignored", checks[0].message)

    def test_check_manifest_warns_but_succeeds_for_setting_conflict_only(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "vscode": IdeConfig(
                    install=False,
                    extensions=(),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir:
            config_path = Path(home_dir) / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "ide:\n  vscode:\n    settings:\n      editor.formatOnSave: false\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}):
                settings_file = engine.ide_settings_file(engine.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="text")

        self.assertEqual(status, 0)


class IdeDiagnosticsTests(unittest.TestCase):
    def test_check_json_reports_ide_app_extension_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    install: true",
                        "    extensions:",
                        "      - ms-python.python",
                        "    settings:",
                        "      editor.formatOnSave: true",
                    ]
                ),
                encoding="utf-8",
            )

            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)
            with mock.patch("base_setup.engine.command_exists", return_value=True), mock.patch(
                "base_setup.engine.run_check",
                return_value=True,
            ), mock.patch(
                "base_setup.engine.list_ide_extensions",
                return_value={"ms-python.python"},
            ), mock.patch.dict(os.environ, {"HOME": tmpdir, "XDG_CONFIG_HOME": ""}):
                settings_file = engine.ide_settings_file(engine.IDE_DEFINITIONS["vscode"])
                settings_file.parent.mkdir(parents=True)
                settings_file.write_text(json.dumps({"editor.formatOnSave": True}), encoding="utf-8")
                stdout_buffer = io.StringIO()
                with redirect_stdout(stdout_buffer):
                    status = engine.check_manifest(fake_context(), default_manifest, manifest, output_format="json")

        checks = json.loads(stdout_buffer.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(
            [check["name"] for check in checks],
            ["VS Code app", "ms-python.python", "VS Code setting: editor.formatOnSave"],
        )
        self.assertTrue(all(check["ok"] for check in checks))

    def test_doctor_text_reports_ide_fix_guidance(self) -> None:
        default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
            ide={
                "cursor": IdeConfig(
                    install=True,
                    extensions=("github.copilot",),
                    settings={"editor.formatOnSave": True},
                )
            },
        )

        with tempfile.TemporaryDirectory() as home_dir:
            with mock.patch.dict(os.environ, {"HOME": home_dir, "XDG_CONFIG_HOME": ""}), mock.patch(
                "base_setup.engine.command_exists",
                return_value=False,
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    status = engine.doctor_manifest(default_manifest, manifest, output_format="text")

        output = stdout.getvalue()
        self.assertGreater(status, 0)
        self.assertIn("Project doctor: demo", output)
        self.assertIn("Cursor app", output)
        self.assertIn("github.copilot", output)
        self.assertIn("Cursor setting: editor.formatOnSave", output)
        self.assertIn("Fix:", output)


if __name__ == "__main__":
    unittest.main()
