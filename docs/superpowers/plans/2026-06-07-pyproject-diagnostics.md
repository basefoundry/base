# Pyproject Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only `pyproject.toml` diagnostics for issue #358 without changing Base setup, activation, dependency, or uv behavior.

**Architecture:** Create a focused `base_setup.pyproject` module that reads only the `pyproject.toml` file beside the active `base_manifest.yaml` and returns existing `ArtifactCheck` objects. Wire those checks into `base_setup.engine.manifest_checks()` so `basectl check`, `basectl doctor`, JSON output, and workspace project diagnostics reuse the current diagnostic pipeline.

**Tech Stack:** Python 3, stdlib `tomllib` when available, existing `base_setup` dataclasses, `pytest`/`unittest`, Markdown docs.

---

### Task 1: Add Focused Pyproject Diagnostics

**Files:**
- Create: `cli/python/base_setup/pyproject.py`
- Create: `cli/python/base_setup/tests/test_pyproject.py`

- [ ] **Step 1: Write tests for missing, valid, malformed, dependency, and `[tool.base]` pyproject cases**

Create `cli/python/base_setup/tests/test_pyproject.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_setup.manifest import BaseManifest
from base_setup.pyproject import check_pyproject


def manifest_at(path: Path) -> BaseManifest:
    return BaseManifest(
        path=path,
        project_name="demo",
        brewfile=None,
        artifacts=(),
    )


class PyprojectDiagnosticsTests(unittest.TestCase):
    def test_missing_pyproject_produces_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = manifest_at(Path(tmpdir) / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual(checks, ())

    def test_valid_project_metadata_reports_name_and_requires_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "demo-python"',
                        'requires-python = ">=3.11"',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].finding_id, "BASE-P140")
        self.assertTrue(checks[0].ok)
        self.assertEqual(checks[0].status, "")
        self.assertIn("demo-python", checks[0].message)
        self.assertIn(">=3.11", checks[0].message)

    def test_malformed_pyproject_warns_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project\n", encoding="utf-8")
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].finding_id, "BASE-P141")
        self.assertFalse(checks[0].ok)
        self.assertEqual(checks[0].status, "warn")
        self.assertIn("not readable TOML", checks[0].message)

    def test_dependency_metadata_warns_without_listing_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "demo-python"',
                        'dependencies = ["requests @ https://user:secret@example.invalid/pkg.whl"]',
                        "",
                        "[project.optional-dependencies]",
                        'dev = ["pytest"]',
                        "",
                        "[dependency-groups]",
                        'lint = ["ruff"]',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P140", "BASE-P142"])
        dependency_check = checks[1]
        self.assertFalse(dependency_check.ok)
        self.assertEqual(dependency_check.status, "warn")
        self.assertIn("dependency metadata", dependency_check.message)
        self.assertNotIn("secret", dependency_check.message)
        self.assertNotIn("example.invalid", dependency_check.message)

    def test_tool_base_warns_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "demo-python"',
                        "",
                        "[tool.base]",
                        'command = "pytest"',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = manifest_at(root / "base_manifest.yaml")

            checks = check_pyproject(manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P140", "BASE-P143"])
        tool_base_check = checks[1]
        self.assertFalse(tool_base_check.ok)
        self.assertEqual(tool_base_check.status, "warn")
        self.assertIn("[tool.base]", tool_base_check.message)
```

- [ ] **Step 2: Run the new test module to verify it fails**

Run:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_setup/tests/test_pyproject.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'base_setup.pyproject'`.

- [ ] **Step 3: Add the minimal pyproject diagnostics module**

Create `cli/python/base_setup/pyproject.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from .checks import ArtifactCheck
from .manifest import BaseManifest

try:
    import tomllib
except ImportError:  # pragma: no cover - exercised only on Python runtimes without tomllib
    tomllib = None  # type: ignore[assignment]


def check_pyproject(manifest: BaseManifest) -> tuple[ArtifactCheck, ...]:
    pyproject_path = manifest.path.parent / "pyproject.toml"
    if not pyproject_path.exists():
        return ()

    data, error = read_pyproject(pyproject_path)
    if error is not None:
        return (pyproject_readability_warning(pyproject_path, error),)

    checks: list[ArtifactCheck] = [pyproject_metadata_check(data)]
    if has_dependency_metadata(data):
        checks.append(pyproject_dependency_warning())
    if has_tool_base(data):
        checks.append(pyproject_tool_base_warning())
    return tuple(checks)


def read_pyproject(path: Path) -> tuple[dict[str, Any], str | None]:
    if tomllib is None:
        return {}, "tomllib is not available in this Python runtime"
    if not path.is_file():
        return {}, "path is not a regular file"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, str(exc)
    except tomllib.TOMLDecodeError as exc:
        return {}, str(exc)
    if not isinstance(data, dict):
        return {}, "top-level TOML document is not a mapping"
    return data, None


def pyproject_metadata_check(data: dict[str, Any]) -> ArtifactCheck:
    project_data = data.get("project")
    if project_data is None:
        message = "pyproject.toml is readable; no [project] metadata table was found."
    elif not isinstance(project_data, dict):
        return ArtifactCheck(
            name="pyproject.toml",
            ok=False,
            message="pyproject.toml has a [project] table that Base cannot read as a mapping.",
            fix="Update [project] to be a TOML table with standard Python project metadata.",
            finding_id="BASE-P140",
            status="warn",
        )
    else:
        details = pyproject_project_details(project_data)
        message = f"pyproject.toml is readable; {details}."
    return ArtifactCheck(
        name="pyproject.toml",
        ok=True,
        message=message,
        fix="",
        finding_id="BASE-P140",
    )


def pyproject_project_details(project_data: dict[str, Any]) -> str:
    details: list[str] = []
    project_name = project_data.get("name")
    requires_python = project_data.get("requires-python")
    if isinstance(project_name, str) and project_name:
        details.append(f"project name '{project_name}'")
    if isinstance(requires_python, str) and requires_python:
        details.append(f"requires-python '{requires_python}'")
    return ", ".join(details) if details else "[project] metadata was found"


def has_dependency_metadata(data: dict[str, Any]) -> bool:
    project_data = data.get("project")
    if isinstance(project_data, dict):
        if "dependencies" in project_data or "optional-dependencies" in project_data:
            return True
    return "dependency-groups" in data


def has_tool_base(data: dict[str, Any]) -> bool:
    tool_data = data.get("tool")
    return isinstance(tool_data, dict) and "base" in tool_data


def pyproject_readability_warning(path: Path, error: str) -> ArtifactCheck:
    return ArtifactCheck(
        name="pyproject.toml",
        ok=False,
        message=f"{path}: pyproject.toml is not readable TOML: {error}.",
        fix="Fix pyproject.toml syntax or remove the file if this is not a Python project.",
        finding_id="BASE-P141",
        status="warn",
    )


def pyproject_dependency_warning() -> ArtifactCheck:
    return ArtifactCheck(
        name="pyproject dependencies",
        ok=False,
        message="pyproject.toml declares Python dependency metadata that Base observes but does not reconcile yet.",
        fix="Keep Python dependencies managed by Python tooling; use base_manifest.yaml only for Base-owned artifacts.",
        finding_id="BASE-P142",
        status="warn",
    )


def pyproject_tool_base_warning() -> ArtifactCheck:
    return ArtifactCheck(
        name="pyproject [tool.base]",
        ok=False,
        message="pyproject.toml contains unsupported [tool.base] configuration.",
        fix="Move Base configuration to base_manifest.yaml; [tool.base] is not supported yet.",
        finding_id="BASE-P143",
        status="warn",
    )
```

- [ ] **Step 4: Run the new test module to verify it passes**

Run:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_setup/tests/test_pyproject.py -q
```

Expected: PASS, all tests in `test_pyproject.py` pass.

- [ ] **Step 5: Commit the focused diagnostics module**

Run:

```bash
git add cli/python/base_setup/pyproject.py cli/python/base_setup/tests/test_pyproject.py
git commit -m "Add pyproject diagnostic checks"
```

Expected: commit succeeds and contains only the new module and its focused tests.

### Task 2: Wire Pyproject Findings Into Manifest Checks

**Files:**
- Modify: `cli/python/base_setup/engine.py`
- Modify: `cli/python/base_setup/tests/test_diagnostics.py`

- [ ] **Step 1: Add integration tests for `manifest_checks()`, check JSON, and doctor warning status**

Append these tests to `ProjectCheckTests` in `cli/python/base_setup/tests/test_diagnostics.py`:

```python
    def test_manifest_checks_include_same_directory_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo-python\"\nrequires-python = \">=3.11\"\n",
                encoding="utf-8",
            )
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)

            checks = engine.manifest_checks(default_manifest, manifest)

        self.assertEqual([check.finding_id for check in checks], ["BASE-P140"])
        self.assertIn("demo-python", checks[0].message)

    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_check_json_includes_pyproject_warnings_without_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[project]\nname = \"demo-python\"\ndependencies = [\"requests\"]\n",
                encoding="utf-8",
            )

            status, stdout, _stderr = run_engine(
                ["--action", "check", "--format", "json", "--manifest", str(manifest_path), "demo"]
            )

        checks = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual([check["name"] for check in checks], ["pyproject.toml", "pyproject dependencies"])
        self.assertTrue(checks[0]["ok"])
        self.assertFalse(checks[1]["ok"])
        self.assertIn("does not reconcile yet", checks[1]["message"])

    def test_doctor_json_reports_pyproject_warnings_without_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "base_manifest.yaml"
            manifest_path.write_text("project:\n  name: demo\nartifacts: []\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[tool.base]\ncommand = \"pytest\"\n", encoding="utf-8")
            default_manifest = BaseManifest(
                path=Path("default_manifest.yaml"),
                project_name="base-defaults",
                brewfile=None,
                artifacts=(),
            )
            manifest = read_manifest(manifest_path)

            with redirect_stdout(io.StringIO()) as stdout:
                status = engine.doctor_manifest(default_manifest, manifest, output_format="json")

        findings = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual([finding["id"] for finding in findings], ["BASE-P140", "BASE-P143"])
        self.assertEqual([finding["status"] for finding in findings], ["ok", "warn"])
```

- [ ] **Step 2: Run the diagnostics tests to verify they fail**

Run:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_setup/tests/test_diagnostics.py -q
```

Expected: FAIL because `manifest_checks()` does not include pyproject findings yet.

- [ ] **Step 3: Wire `check_pyproject()` into `manifest_checks()`**

Modify `cli/python/base_setup/engine.py` imports:

```python
from .pyproject import check_pyproject
```

Add this call in `manifest_checks()` after the existing local project diagnostic groups and before artifact reconciliation checks:

```python
    checks.extend(check_pyproject(effective_manifest))
```

The surrounding block should look like:

```python
    checks.extend(check_required_env(effective_manifest))
    checks.extend(check_required_ports(effective_manifest))
    checks.extend(check_build(effective_manifest))
    checks.extend(check_demo(effective_manifest))
    checks.extend(check_ide_installs(effective_manifest))
    checks.extend(check_ide_extensions(effective_manifest))
    checks.extend(check_ide_settings(effective_manifest))
    checks.extend(check_pyproject(effective_manifest))

    for artifact, definition in zip(artifacts, definitions, strict=True):
        checks.append(check_artifact(effective_manifest.project_name, artifact, definition))
```

- [ ] **Step 4: Run focused Python tests to verify wiring passes**

Run:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest \
  cli/python/base_setup/tests/test_pyproject.py \
  cli/python/base_setup/tests/test_diagnostics.py -q
```

Expected: PASS for both test modules.

- [ ] **Step 5: Commit the manifest check integration**

Run:

```bash
git add cli/python/base_setup/engine.py cli/python/base_setup/tests/test_diagnostics.py
git commit -m "Report pyproject findings in project diagnostics"
```

Expected: commit succeeds and contains the engine wiring plus diagnostic integration tests.

### Task 3: Document Finding IDs And Source-Of-Truth Boundaries

**Files:**
- Modify: `docs/doctor-findings.md`
- Modify: `docs/python-manifest.md`

- [ ] **Step 1: Add finding ID documentation**

Modify the Project Findings table in `docs/doctor-findings.md` by adding these rows after `BASE-P132`:

```markdown
| `BASE-P140` | `pyproject.toml` presence and metadata summary |
| `BASE-P141` | `pyproject.toml` readability |
| `BASE-P142` | `pyproject.toml` dependency metadata observed but not reconciled |
| `BASE-P143` | Unsupported `[tool.base]` configuration |
```

Add this paragraph after the existing `BASE-P050` explanatory paragraph:

```markdown
`BASE-P140` through `BASE-P143` are read-only `pyproject.toml` diagnostics.
Base only inspects the `pyproject.toml` file beside the active
`base_manifest.yaml`. These findings do not make `pyproject.toml` a Base
configuration source and do not cause Base to install Python dependencies.
Warnings in this range should guide users toward a valid Python project file
without failing the Base manifest check by themselves.
```

- [ ] **Step 2: Add Python manifest boundary documentation**

Append this section to `docs/python-manifest.md` before `## Non-Goals`:

```markdown
## Relationship To `pyproject.toml`

Base observes a same-directory `pyproject.toml` during project diagnostics when
one exists beside `base_manifest.yaml`. This diagnostic support is read-only:
Base reports whether the file is readable, summarizes standard `[project]`
metadata, and warns when Python dependency metadata or unsupported `[tool.base]`
configuration is present.

`base_manifest.yaml` remains the Base source of truth. Base does not install
packages from `[project].dependencies`, does not execute build backend hooks,
and does not treat `[tool.base]` as an alternate manifest.

Future uv-managed Python support should use an explicit `python:` manifest
contract, tracked separately from the first read-only diagnostics slice.
```

- [ ] **Step 3: Run documentation whitespace validation**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Commit the documentation updates**

Run:

```bash
git add docs/doctor-findings.md docs/python-manifest.md
git commit -m "Document pyproject diagnostic boundaries"
```

Expected: commit succeeds and contains only documentation updates.

### Task 4: Run Full Verification And Prepare PR

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run focused Python verification**

Run:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest \
  cli/python/base_setup/tests/test_pyproject.py \
  cli/python/base_setup/tests/test_diagnostics.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full Base verification**

Run:

```bash
env -u BASE_HOME ./bin/base-test
```

Expected: Python tests pass and BATS reports all tests successful.

- [ ] **Step 3: Run whitespace validation**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Inspect final branch state**

Run:

```bash
git status --short --branch
git log --oneline --decorate --max-count=5
```

Expected: clean worktree on `feature/358-pyproject-diagnostics` with recent commits for the design, plan, implementation, docs, and any final fixups.

- [ ] **Step 5: Create the PR**

Run:

```bash
git push -u origin feature/358-pyproject-diagnostics
gh pr create \
  --repo codeforester/base \
  --base master \
  --head feature/358-pyproject-diagnostics \
  --title "Observe pyproject metadata in project diagnostics" \
  --body $'## Summary\n- Add read-only `pyproject.toml` diagnostics beside the active Base manifest.\n- Report pyproject metadata, dependency metadata, malformed TOML, and unsupported `[tool.base]` through existing check/doctor output.\n- Document the diagnostic finding IDs and source-of-truth boundary.\n\n## Validation\n- `PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_setup/tests/test_pyproject.py cli/python/base_setup/tests/test_diagnostics.py -q`\n- `env -u BASE_HOME ./bin/base-test`\n- `git diff --check`\n\n## Demo Impact\n- None. Diagnostics-only change.\n\nCloses #358'
```

Expected: PR opens against `master` and links issue #358.
