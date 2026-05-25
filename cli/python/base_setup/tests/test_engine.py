from __future__ import annotations

import io
import importlib.util
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup import engine
from base_setup.engine import ArtifactError, main, merge_artifacts
from base_setup.manifest import ArtifactRequest
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
            [(artifact.artifact_type, artifact.name, artifact.version) for artifact in merged],
            [
                ("python-package", "click", "8.4.1"),
                ("tool", "terraform", "1.8.5"),
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
        self.assertEqual(manifest.artifacts[0].artifact_type, "tool")
        self.assertEqual(manifest.artifacts[0].name, "terraform")
        self.assertEqual(manifest.artifacts[0].version, "1.8.5")

    def test_base_manifest_declares_python_dev_tools(self) -> None:
        manifest = read_manifest(Path(__file__).resolve().parents[4] / "base_manifest.yaml")
        tools = {(artifact.artifact_type, artifact.name) for artifact in manifest.artifacts}

        self.assertIn(("python-package", "pylint"), tools)
        self.assertIn(("python-package", "pytest"), tools)
        self.assertIsNotNone(get_artifact_definition("python-package", "pylint"))
        self.assertIsNotNone(get_artifact_definition("python-package", "pytest"))

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

        ctx.log.error.assert_called_once_with("Command stderr: %s", "installer exploded")

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


if __name__ == "__main__":
    unittest.main()
