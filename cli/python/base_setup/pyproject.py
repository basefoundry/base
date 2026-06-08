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
