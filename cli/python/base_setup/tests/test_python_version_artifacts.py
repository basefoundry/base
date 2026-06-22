from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import artifacts
from base_setup.artifacts import ProjectRuntimeConfig
from base_setup.errors import ArtifactError
from base_setup.python_policy import PythonInterpreter
from base_setup.registry import get_artifact_definition
from base_setup.tests.helpers import fake_context


class PythonVersionArtifactTests(unittest.TestCase):

    def test_python_artifact_creates_requested_python_version_venv(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "demo" / ".venv"
            python_bin = Path(tmpdir) / "python3.12"
            with mock.patch("base_setup.artifacts.project_venv_dir", return_value=venv_dir), mock.patch(
                "base_setup.artifacts.python_artifact_installed",
                return_value=False,
            ), mock.patch(
                "base_setup.artifacts.resolve_python_interpreter",
                return_value=PythonInterpreter(path=python_bin, version=(3, 12)),
            ), mock.patch(
                "base_setup.process.run_command"
            ) as run_command:
                artifacts.reconcile_python_artifact(
                    ctx,
                    definition,
                    "latest",
                    ProjectRuntimeConfig(name="demo", python_requirement="3.12"),
                    dry_run=False,
                )

        self.assertEqual(
            run_command.call_args_list,
            [
                mock.call(ctx, [str(python_bin), "-m", "venv", str(venv_dir)]),
                mock.call(
                    ctx,
                    [
                        str(venv_dir / "bin" / "python"),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "requests",
                    ],
                ),
            ],
        )

    def test_python_artifact_rejects_existing_venv_with_wrong_python_version(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "demo" / ".venv"
            python_bin = venv_dir / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/bin/sh\nprintf '3.13\\n'\n", encoding="utf-8")
            python_bin.chmod(0o755)

            with mock.patch("base_setup.artifacts.project_venv_dir", return_value=venv_dir), mock.patch(
                "base_setup.artifacts.python_artifact_installed",
                return_value=False,
            ), mock.patch("base_setup.process.run_command") as run_command:
                with self.assertRaisesRegex(ArtifactError, "uses Python 3.13"):
                    artifacts.reconcile_python_artifact(
                        ctx,
                        definition,
                        "latest",
                        ProjectRuntimeConfig(name="demo", python_requirement="3.12"),
                        dry_run=False,
                    )

        run_command.assert_not_called()

