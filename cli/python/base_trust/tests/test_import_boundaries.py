from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CLI_PYTHON = REPO_ROOT / "cli" / "python"


def run_import_probe(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    existing_pythonpath = environment.get("PYTHONPATH")
    pythonpath = str(CLI_PYTHON)
    if existing_pythonpath:
        pythonpath = f"{pythonpath}{os.pathsep}{existing_pythonpath}"
    environment["PYTHONPATH"] = pythonpath
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )


class ImportBoundaryTests(unittest.TestCase):
    def test_trust_engine_does_not_import_project_engine_or_onboarding(self) -> None:
        result = run_import_probe(
            "import sys; import base_trust.engine; "
            "assert not any(module_name in sys.modules for module_name in ("
            "'base_projects.engine', 'base_projects.project_discovery', "
            "'base_projects.workspace_onboarding', 'base_projects.workspace_context', "
            "'base_projects.workspace_scanner'))"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_project_engine_does_not_import_trust_engine(self) -> None:
        result = run_import_probe(
            "import sys; import base_projects.engine; "
            "assert 'base_trust.engine' not in sys.modules"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shared_trust_modules_do_not_import_project_modules(self) -> None:
        result = run_import_probe(
            "import sys; import base_setup.manifest_trust; import base_setup.manifest_trust_guidance; "
            "assert not any(name == 'base_projects' or name.startswith('base_projects.') for name in sys.modules)"
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
