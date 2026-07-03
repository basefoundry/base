from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import artifacts
from base_setup.registry import get_artifact_definition
from base_setup.tests.helpers import fake_context


class ProjectEnvironmentTests(unittest.TestCase):
    def test_python_artifact_ignores_different_active_project_venv_override(self) -> None:
        definition = get_artifact_definition("python-package", "requests")
        self.assertIsNotNone(definition)
        ctx = fake_context()

        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            inherited_venv = Path(tmpdir) / "base" / ".venv"
            expected_venv = home_dir / ".base.d" / "demo" / ".venv"
            with (
                mock.patch.dict(
                    os.environ,
                    {"BASE_PROJECT": "base", "BASE_PROJECT_VENV_DIR": str(inherited_venv)},
                ),
                mock.patch("base_setup.artifacts.Path.home", return_value=home_dir),
                mock.patch("base_setup.artifacts.python_artifact_installed", return_value=False),
            ):
                artifacts.reconcile_python_artifact(ctx, definition, "latest", "demo", dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(
            f"[DRY-RUN] Would create project virtual environment at '{expected_venv}'.",
            info_messages,
        )
        self.assertIn(
            f"[DRY-RUN] Would run: {expected_venv}/bin/python -m pip install --disable-pip-version-check requests",
            info_messages,
        )
        self.assertNotIn(
            f"[DRY-RUN] Would create project virtual environment at '{inherited_venv}'.",
            info_messages,
        )


if __name__ == "__main__":
    unittest.main()
