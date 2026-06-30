from __future__ import annotations

import ast
from pathlib import Path


STANDARD_EXIT_VALUES = {0, 1, 2}
STANDARD_ERROR_EXIT_VALUES = {1, 2}
EXIT_STATUS_VARIABLES = {"exit_code", "status"}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def iter_production_python_files() -> list[Path]:
    roots = (repository_root() / "cli" / "python", repository_root() / "lib" / "python")
    return sorted(
        path
        for root in roots
        for path in root.rglob("*.py")
        if "tests" not in path.relative_to(root).parts
    )


def raw_standard_exit_returns(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        values: tuple[ast.expr | None, ...]
        if isinstance(node.value, ast.IfExp):
            values = (node.value.body, node.value.orelse)
        else:
            values = (node.value,)
        for value in values:
            if not isinstance(value, ast.Constant) or isinstance(value.value, bool):
                continue
            if isinstance(value.value, int) and value.value in STANDARD_EXIT_VALUES:
                findings.append(f"{path.relative_to(repository_root())}:{node.lineno}: return {value.value}")
    return findings


def target_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def raw_standard_exit_assignments(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[str] = []
    for node in ast.walk(tree):
        assignments: tuple[tuple[ast.expr, ast.expr | None], ...]
        if isinstance(node, ast.Assign):
            assignments = tuple((target, node.value) for target in node.targets)
        elif isinstance(node, ast.AnnAssign):
            assignments = ((node.target, node.value),)
        else:
            continue
        for target, value in assignments:
            if target_name(target) not in EXIT_STATUS_VARIABLES:
                continue
            if not isinstance(value, ast.Constant) or isinstance(value.value, bool):
                continue
            if isinstance(value.value, int) and value.value in STANDARD_ERROR_EXIT_VALUES:
                findings.append(
                    f"{path.relative_to(repository_root())}:{node.lineno}: "
                    f"{target_name(target)} = {value.value}"
                )
    return findings


def test_production_cli_code_uses_exit_code_constants_for_standard_returns() -> None:
    findings: list[str] = []
    for path in iter_production_python_files():
        findings.extend(raw_standard_exit_returns(path))

    assert not findings, "\n".join(findings)


def test_production_cli_code_uses_exit_code_constants_for_standard_status_assignments() -> None:
    findings: list[str] = []
    for path in iter_production_python_files():
        findings.extend(raw_standard_exit_assignments(path))

    assert not findings, "\n".join(findings)
