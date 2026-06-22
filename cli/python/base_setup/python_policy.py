from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .checks import ArtifactCheck
from .manifest import BaseManifest


SUPPORTED_PYTHON_MIN = (3, 10)
SUPPORTED_PYTHON_MAX = (3, 13)
SUPPORTED_PYTHON_MINORS = tuple((3, minor) for minor in range(10, 14))
PYTHON_REQUIREMENT_FINDING_ID = "BASE-P170"
PYTHON_INTERPRETER_FINDING_ID = "BASE-P171"

_EXACT_VERSION_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.\d+)?$")
_SPECIFIER_RE = re.compile(r"^(?P<operator>==|>=|<=|>|<)\s*(?P<version>\d+(?:\.\d+){1,2})$")


@dataclass(frozen=True)
class PythonRequirementPolicy:
    requested: str
    selected_version: tuple[int, int] | None
    reason: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.selected_version is not None and not self.error


@dataclass(frozen=True)
class PythonSpecifier:
    operator: str
    version: tuple[int, int, int]


@dataclass(frozen=True)
class PythonInterpreter:
    path: Path
    version: tuple[int, int]


ResolvePythonInterpreter = Callable[[tuple[int, int]], PythonInterpreter | None]


def python_requirement_checks(
    manifest: BaseManifest,
    resolve_interpreter: ResolvePythonInterpreter = None,
) -> tuple[ArtifactCheck, ...]:
    policy_check = python_requirement_policy_check(manifest)
    if policy_check is None:
        return ()
    checks = [policy_check]
    if policy_check.ok:
        interpreter_check = python_interpreter_availability_check(manifest, resolve_interpreter=resolve_interpreter)
        if interpreter_check is not None:
            checks.append(interpreter_check)
    return tuple(checks)


def python_requirement_policy_check(manifest: BaseManifest) -> ArtifactCheck | None:
    requested = manifest.python.requires_python
    if requested is None:
        return None

    policy = evaluate_python_requirement(requested)
    details = {
        "requested": requested,
        "supported_min": version_label(SUPPORTED_PYTHON_MIN),
        "supported_max": version_label(SUPPORTED_PYTHON_MAX),
    }
    if policy.selected_version is not None:
        details["selected_version"] = version_label(policy.selected_version)
    if policy.ok:
        selected = version_label(policy.selected_version)
        return ArtifactCheck(
            name="python.requires_python",
            ok=True,
            message=f"Project Python requirement '{requested}' selects supported Python {selected}.",
            fix="",
            finding_id=PYTHON_REQUIREMENT_FINDING_ID,
            details=details,
        )

    return ArtifactCheck(
        name="python.requires_python",
        ok=False,
        message=f"Project Python requirement '{requested}' {policy.error}.",
        fix=(
            "Set python.requires_python to a Python version or range within "
            f"{version_label(SUPPORTED_PYTHON_MIN)} through {version_label(SUPPORTED_PYTHON_MAX)}."
        ),
        finding_id=PYTHON_REQUIREMENT_FINDING_ID,
        details=details,
    )


def python_interpreter_availability_check(
    manifest: BaseManifest,
    resolve_interpreter: ResolvePythonInterpreter = None,
) -> ArtifactCheck | None:
    requested = manifest.python.requires_python
    if requested is None:
        return None

    policy = evaluate_python_requirement(requested)
    if not policy.ok:
        return None

    selected_version = policy.selected_version
    assert selected_version is not None
    selected_label = version_label(selected_version)
    if resolve_interpreter is None:
        resolve_interpreter = resolve_python_interpreter
    interpreter = resolve_interpreter(selected_version)
    details = {
        "requested": requested,
        "selected_version": selected_label,
    }
    if interpreter is None:
        return ArtifactCheck(
            name="python.interpreter",
            ok=False,
            message=(
                f"Project Python requirement '{requested}' selects supported Python {selected_label}, "
                f"but Python {selected_label} is not available."
            ),
            fix=f"Install Python {selected_label} or update python.requires_python in base_manifest.yaml.",
            finding_id=PYTHON_INTERPRETER_FINDING_ID,
            details=details,
        )

    details["python"] = str(interpreter.path)
    if interpreter.version != selected_version:
        actual_label = version_label(interpreter.version)
        return ArtifactCheck(
            name="python.interpreter",
            ok=False,
            message=(
                f"Project Python requirement '{requested}' selects Python {selected_label}, "
                f"but '{interpreter.path}' reports Python {actual_label}."
            ),
            fix=f"Install Python {selected_label} or update python.requires_python in base_manifest.yaml.",
            finding_id=PYTHON_INTERPRETER_FINDING_ID,
            details=details | {"actual_version": actual_label},
        )

    return ArtifactCheck(
        name="python.interpreter",
        ok=True,
        message=f"Python {selected_label} is available at '{interpreter.path}'.",
        fix="",
        finding_id=PYTHON_INTERPRETER_FINDING_ID,
        details=details,
    )


def evaluate_python_requirement(requirement: str) -> PythonRequirementPolicy:
    requirement = requirement.strip()
    exact = parse_exact_minor(requirement)
    if exact is not None:
        if exact in SUPPORTED_PYTHON_MINORS:
            return PythonRequirementPolicy(requirement, exact, "exact")
        return PythonRequirementPolicy(requirement, None, "exact", unsupported_reason((exact,)))

    specifiers = parse_specifiers(requirement)
    if specifiers is None:
        return PythonRequirementPolicy(requirement, None, "invalid", "cannot parse this Python requirement")

    supported_matches = tuple(
        version for version in SUPPORTED_PYTHON_MINORS if specifiers_allow_minor(specifiers, version)
    )
    if supported_matches:
        return PythonRequirementPolicy(requirement, supported_matches[-1], "range")

    requested_matches = tuple(
        version for version in candidate_python_minors() if specifiers_allow_minor(specifiers, version)
    )
    return PythonRequirementPolicy(requirement, None, "range", unsupported_reason(requested_matches))


def parse_exact_minor(value: str) -> tuple[int, int] | None:
    match = _EXACT_VERSION_RE.fullmatch(value)
    if match is None:
        return None
    return int(match.group("major")), int(match.group("minor"))


def parse_specifiers(value: str) -> tuple[PythonSpecifier, ...] | None:
    specifiers: list[PythonSpecifier] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            return None
        match = _SPECIFIER_RE.fullmatch(part)
        if match is None:
            return None
        specifiers.append(
            PythonSpecifier(
                operator=match.group("operator"),
                version=parse_version(match.group("version")),
            )
        )
    return tuple(specifiers)


def parse_version(value: str) -> tuple[int, int, int]:
    parts = [int(part) for part in value.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def specifiers_allow_minor(specifiers: tuple[PythonSpecifier, ...], version: tuple[int, int]) -> bool:
    candidate = version[0], version[1], 0
    return all(specifier_allows_version(specifier, candidate) for specifier in specifiers)


def specifier_allows_version(specifier: PythonSpecifier, candidate: tuple[int, int, int]) -> bool:
    if specifier.operator == "==":
        return candidate[:2] == specifier.version[:2]
    if specifier.operator == ">=":
        return candidate >= specifier.version
    if specifier.operator == ">":
        return candidate > specifier.version
    if specifier.operator == "<=":
        return candidate <= specifier.version
    if specifier.operator == "<":
        return candidate < specifier.version
    raise AssertionError(f"unsupported Python specifier operator: {specifier.operator}")


def candidate_python_minors() -> tuple[tuple[int, int], ...]:
    return tuple((3, minor) for minor in range(0, 21))


def unsupported_reason(matches: tuple[tuple[int, int], ...]) -> str:
    if matches:
        if max(matches) < SUPPORTED_PYTHON_MIN:
            return "asks for Python older than Base supports"
        if min(matches) > SUPPORTED_PYTHON_MAX:
            return "asks for Python newer than Base supports"
    return "does not select a Python version supported by Base"


def version_label(version: tuple[int, int] | None) -> str:
    if version is None:
        return ""
    return f"{version[0]}.{version[1]}"


def resolve_python_interpreter(selected_version: tuple[int, int]) -> PythonInterpreter | None:
    seen: set[Path] = set()
    for candidate in python_interpreter_candidates(selected_version):
        candidate = candidate.expanduser()
        if candidate in seen:
            continue
        seen.add(candidate)
        interpreter = inspect_python_interpreter(candidate)
        if interpreter is not None and interpreter.version == selected_version:
            return interpreter
    return None


def python_interpreter_candidates(selected_version: tuple[int, int]) -> tuple[Path, ...]:
    label = version_label(selected_version)
    formula = f"python@{label}"
    candidates: list[Path] = []

    override = os.environ.get("BASE_PROJECT_PYTHON_BIN")
    if override:
        candidates.append(Path(override))

    for prefix in ("/opt/homebrew", "/usr/local"):
        candidates.append(Path(prefix) / "opt" / formula / "bin" / "python3")
        candidates.append(Path(prefix) / "opt" / formula / "bin" / f"python{label}")
        candidates.append(Path(prefix) / "opt" / formula / "libexec" / "bin" / "python3")
        candidates.append(Path(prefix) / "opt" / formula / "libexec" / "bin" / f"python{label}")

    brew = shutil.which("brew")
    if brew:
        brew_prefix = homebrew_formula_prefix(brew, formula)
        if brew_prefix is not None:
            candidates.append(brew_prefix / "bin" / "python3")
            candidates.append(brew_prefix / "bin" / f"python{label}")
            candidates.append(brew_prefix / "libexec" / "bin" / "python3")
            candidates.append(brew_prefix / "libexec" / "bin" / f"python{label}")

    for command in (f"python{label}", "python3"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))

    candidates.append(Path(sys.executable))
    return tuple(candidates)


def homebrew_formula_prefix(brew: str, formula: str) -> Path | None:
    try:
        completed = subprocess.run(
            [brew, "--prefix", formula],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    prefix = completed.stdout.strip()
    if completed.returncode or not prefix:
        return None
    return Path(prefix)


def inspect_python_interpreter(candidate: Path) -> PythonInterpreter | None:
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return None
    try:
        completed = subprocess.run(
            [
                str(candidate),
                "-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode:
        return None
    version = parse_exact_minor(completed.stdout.strip())
    if version is None:
        return None
    return PythonInterpreter(path=candidate, version=version)
