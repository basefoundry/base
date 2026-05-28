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

from base_setup import engine
from base_setup.engine import ArtifactError, format_command, main, merge_artifacts
from base_setup.manifest import ArtifactRequest, BaseManifest, ManifestError
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
                {"BASE_PROJECT": "demo", "BASE_PROJECT_VENV_DIR": str(venv_dir)},
            ), mock.patch("base_setup.engine.python_artifact_installed", return_value=False):
                engine.reconcile_python_artifact(ctx, definition, "latest", dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            f"[DRY-RUN] Would create project virtual environment at '{venv_dir}'.",
            info_messages,
        )
        self.assertIn(
            f"[DRY-RUN] Would run: {venv_dir}/bin/python -m pip install requests",
            info_messages,
        )

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


if __name__ == "__main__":
    unittest.main()
