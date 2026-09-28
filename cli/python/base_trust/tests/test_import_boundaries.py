from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CLI_PYTHON = REPO_ROOT / "cli" / "python"
PRODUCTION_PACKAGE_ROOTS = (
    REPO_ROOT / "cli" / "python" / "base_setup",
    REPO_ROOT / "cli" / "python" / "base_trust",
)

# `workspace_errors` contains exception definitions only and has no project or
# trust dependencies. Keep this one documented exception explicit while making
# every other production module-scope base_projects import fail the test.
ALLOWED_MODULE_SCOPE_PROJECT_IMPORTS = {
    ("cli/python/base_trust/engine.py", "base_projects.workspace_errors"),
}


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


def production_python_files() -> list[Path]:
    return sorted(
        path
        for package_root in PRODUCTION_PACKAGE_ROOTS
        for path in package_root.rglob("*.py")
        if "tests" not in path.parts
    )


def module_scope_project_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.update(
                alias.name
                for alias in node.names
                if alias.name == "base_projects" or alias.name.startswith("base_projects.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "base_projects" or module.startswith("base_projects."):
                imports.add(module)
    return imports


class ImportBoundaryTests(unittest.TestCase):
    def test_production_module_scope_project_imports_are_explicit(self) -> None:
        actual = {
            (path.relative_to(REPO_ROOT).as_posix(), module)
            for path in production_python_files()
            for module in module_scope_project_imports(path)
        }
        self.assertEqual(actual, ALLOWED_MODULE_SCOPE_PROJECT_IMPORTS)

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
