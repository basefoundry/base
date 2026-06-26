from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checks import ArtifactCheck
from .manifest import BaseManifest
from .project_routing import route_for_manifest
from .pyproject import read_pyproject
from .python_policy import inspect_python_interpreter
from .python_policy import version_label

PYTHON_RUNTIME_FINDING_ID = "BASE-P172"


@dataclass(frozen=True)
class ProjectPythonRuntime:
    manager: str
    venv: Path
    python: Path
    version: str
    requires_python: str | None = None
    pyproject_requires_python: str | None = None

    def to_json(self) -> dict[str, str]:
        payload = {
            "manager": self.manager,
            "venv": str(self.venv),
            "python": str(self.python),
            "version": self.version,
        }
        if self.requires_python is not None:
            payload["requires_python"] = self.requires_python
        if self.pyproject_requires_python is not None:
            payload["pyproject_requires_python"] = self.pyproject_requires_python
        return payload

    def to_check_details(self) -> dict[str, str]:
        payload = self.to_json()
        payload["python_version"] = payload["version"]
        return payload


def project_python_runtime(manifest: BaseManifest, venv_dir: Path | None = None) -> ProjectPythonRuntime | None:
    if venv_dir is None:
        venv_dir = route_for_manifest(manifest).project_venv_dir
    python_bin = venv_dir / "bin" / "python"
    interpreter = inspect_python_interpreter(python_bin)
    if interpreter is None:
        return None
    return ProjectPythonRuntime(
        manager=manifest.python.manager or "base",
        venv=venv_dir,
        python=interpreter.path,
        version=version_label(interpreter.version),
        requires_python=manifest.python.requires_python,
        pyproject_requires_python=pyproject_requires_python(manifest.path.parent / "pyproject.toml"),
    )


def project_python_runtime_check(manifest: BaseManifest) -> tuple[ArtifactCheck, ...]:
    runtime = project_python_runtime(manifest)
    if runtime is None:
        return ()
    return (
        ArtifactCheck(
            name="project_python_runtime",
            ok=True,
            message=f"Project Python runtime uses Python {runtime.version} at '{runtime.python}'.",
            fix="",
            finding_id=PYTHON_RUNTIME_FINDING_ID,
            details=runtime.to_check_details(),
        ),
    )


def pyproject_requires_python(path: Path) -> str | None:
    data, error = read_pyproject(path)
    if error is not None:
        return None
    project_data: Any = data.get("project")
    if not isinstance(project_data, dict):
        return None
    requires_python = project_data.get("requires-python")
    return requires_python if isinstance(requires_python, str) and requires_python else None
