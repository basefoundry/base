from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import base_cli

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest
from .python_artifacts import create_project_virtualenv
from .python_artifacts import project_venv_recreate_enabled
from .python_artifacts import python_artifact_installed
from .project_routing import route_for_manifest
from .runtime_inspection import unverified_runtime_check
from .uv import manifest_uses_uv_project_manager


TEST_REQUIREMENTS_FILE_FINDING_ID = "BASE-P180"
TEST_REQUIREMENTS_ENVIRONMENT_FINDING_ID = "BASE-P181"
_DIRECT_REQUIREMENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"(?:(?P<operator>===|==)\s*(?P<version>[A-Za-z0-9][A-Za-z0-9.!+_-]*))?$"
)


@dataclass(frozen=True)
class RequirementSpec:
    name: str
    version: str
    raw: str


def resolve_test_requirements_path(manifest: BaseManifest) -> Path | None:
    if manifest.test is None or manifest.test.requirements is None:
        return None

    raw_path = Path(manifest.test.requirements)
    if raw_path.is_absolute():
        raise ArtifactError("test.requirements must be a repository-relative path.")

    project_root = manifest.path.parent.resolve()
    candidate = (project_root / raw_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ArtifactError("test.requirements must resolve inside the project root.") from exc
    return candidate


def requirements_file_digest(manifest: BaseManifest) -> str | None:
    try:
        path = resolve_test_requirements_path(manifest)
    except ArtifactError:
        return None
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_test_requirements(manifest: BaseManifest) -> tuple[Path, tuple[RequirementSpec, ...]] | None:
    path = resolve_test_requirements_path(manifest)
    if path is None:
        return None
    if manifest_uses_uv_project_manager(manifest):
        raise ArtifactError(
            "test.requirements is not supported for uv-managed projects. "
            "Declare test dependencies in pyproject.toml and synchronize with uv."
        )
    if not path.is_file():
        raise ArtifactError(
            f"Declared test requirements file '{path}' does not exist. "
            f"Run 'basectl setup {manifest.project_name}' after adding it or update test.requirements."
        )

    requirements: list[RequirementSpec] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ArtifactError(f"Unable to read declared test requirements file '{path}': {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        candidate = line.split(" #", 1)[0].strip()
        if not candidate or candidate.startswith("#"):
            continue
        if candidate.startswith(("-", "http://", "https://")):
            raise ArtifactError(
                f"{path}:{line_number} uses unsupported requirement syntax '{candidate}'. "
                "Base currently supports direct package names with optional == versions only; "
                "package extras are not supported."
            )
        match = _DIRECT_REQUIREMENT_RE.fullmatch(candidate)
        if match is None:
            raise ArtifactError(
                f"{path}:{line_number} uses unsupported requirement syntax '{candidate}'. "
                "Base currently supports direct package names with optional == versions only; "
                "package extras are not supported."
            )
        requirements.append(
            RequirementSpec(
                name=match.group("name"),
                version=match.group("version") or "latest",
                raw=candidate,
            )
        )
    return path, tuple(requirements)


def check_test_requirements(manifest: BaseManifest, *, verify_project_runtime: bool = True) -> ArtifactCheck | None:
    if manifest.test is None or manifest.test.requirements is None:
        return None

    try:
        parsed = read_test_requirements(manifest)
    except ArtifactError as exc:
        return ArtifactCheck(
            name="test requirements file",
            ok=False,
            message=str(exc),
            fix=f"Review test.requirements in '{manifest.path}' and rerun 'basectl setup {manifest.project_name}'.",
            finding_id=TEST_REQUIREMENTS_FILE_FINDING_ID,
        )
    if parsed is None:
        return None
    path, requirements = parsed
    return check_requirements_environment(manifest, path, requirements, verify_project_runtime=verify_project_runtime)


def check_requirements_environment(
    manifest: BaseManifest, path: Path, requirements: tuple[RequirementSpec, ...], *, verify_project_runtime: bool,
) -> ArtifactCheck:
    route = route_for_manifest(manifest)
    python_bin = route.project_venv_dir / "bin" / "python"
    if not python_bin.is_file():
        return ArtifactCheck(
            name="test requirements environment",
            ok=False,
            message=(
                f"Test requirements file '{path.relative_to(route.project_root)}' is declared, but the project "
                f"Python environment is missing at '{route.project_venv_dir}'."
            ),
            fix=f"Run 'basectl setup {manifest.project_name}' before running its tests.",
            finding_id=TEST_REQUIREMENTS_ENVIRONMENT_FINDING_ID,
        )

    if not verify_project_runtime:
        return unverified_runtime_check(
            manifest, "test requirements environment", TEST_REQUIREMENTS_ENVIRONMENT_FINDING_ID,
            details={"requirements": str(path), "sha256": requirements_file_digest(manifest) or ""},
        )

    missing = [
        requirement.raw
        for requirement in requirements
        if not python_requirement_installed(python_bin, requirement)
    ]
    if missing:
        return ArtifactCheck(
            name="test requirements environment",
            ok=False,
            message=(
                f"Test requirements file '{path.relative_to(route.project_root)}' has missing or mismatched "
                f"packages: {', '.join(missing)}."
            ),
            fix=f"Run 'basectl setup {manifest.project_name}' to install the declared test requirements.",
            finding_id=TEST_REQUIREMENTS_ENVIRONMENT_FINDING_ID,
            details={"requirements": str(path), "missing": missing},
        )
    return ArtifactCheck(
        name="test requirements environment",
        ok=True,
        message=(
            f"Test requirements file '{path.relative_to(route.project_root)}' is satisfied in "
            f"'{route.project_venv_dir}'."
        ),
        fix="",
        finding_id=TEST_REQUIREMENTS_ENVIRONMENT_FINDING_ID,
        details={"requirements": str(path), "sha256": requirements_file_digest(manifest) or ""},
    )


def python_requirement_installed(python_bin: Path, requirement: RequirementSpec) -> bool:
    if requirement.version == "latest":
        return python_artifact_installed(python_bin, requirement.name, "latest")
    return python_artifact_installed(python_bin, requirement.name, requirement.version)


def reconcile_test_requirements(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    parsed = read_test_requirements(manifest)
    if parsed is None:
        return
    path, _requirements = parsed
    route = route_for_manifest(manifest)
    python_bin = route.project_venv_dir / "bin" / "python"
    needs_venv = project_venv_recreate_enabled() or not python_bin.exists()
    command = [str(python_bin), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(path)]
    if dry_run:
        if needs_venv:
            ctx.log.info("[DRY-RUN] Would create project virtual environment at '%s'.", route.project_venv_dir)
        process.dry_run_command(ctx, command, cwd=route.project_root)
        return
    if needs_venv:
        create_project_virtualenv(ctx, route.project_venv_dir, manifest.python.requires_python)
    ctx.log.info(
        "Installing project test requirements from '%s' into '%s'.",
        path.relative_to(route.project_root),
        route.project_venv_dir,
    )
    process.run_command(
        ctx,
        command,
        cwd=route.project_root,
        env=process.python_package_environment(),
    )

    check = check_test_requirements(manifest)
    if check is not None and not check.ok:
        raise ArtifactError(
            f"Test requirements installation completed, but verification failed: {check.message} "
            f"Fix: {check.fix}"
        )


__all__ = [
    "TEST_REQUIREMENTS_ENVIRONMENT_FINDING_ID",
    "TEST_REQUIREMENTS_FILE_FINDING_ID",
    "RequirementSpec",
    "check_test_requirements",
    "read_test_requirements",
    "reconcile_test_requirements",
    "resolve_test_requirements_path",
    "requirements_file_digest",
]
