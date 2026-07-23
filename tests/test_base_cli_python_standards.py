from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARDS_DOC = REPO_ROOT / "STANDARDS.md"
PYTHON_ROOTS = (
    REPO_ROOT / "cli" / "python",
    REPO_ROOT / "lib" / "python",
)


def has_future_annotations(source: str) -> bool:
    module = ast.parse(source)
    statements = module.body
    if statements and isinstance(statements[0], ast.Expr):
        value = statements[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            statements = statements[1:]
    if not statements:
        return False
    first_statement = statements[0]
    return (
        isinstance(first_statement, ast.ImportFrom)
        and first_statement.module == "__future__"
        and any(alias.name == "annotations" for alias in first_statement.names)
    )


def test_non_empty_python_modules_use_future_annotations() -> None:
    missing = []
    for root in PYTHON_ROOTS:
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            if not source.strip():
                continue
            if not has_future_annotations(source):
                missing.append(path.relative_to(REPO_ROOT).as_posix())

    assert not missing


def test_python_standards_document_production_assertionerror_policy() -> None:
    text = STANDARDS_DOC.read_text(encoding="utf-8")

    assert "production code must not use `assert`" in text
    assert "`AssertionError`" in text
    assert "`ValueError`" in text
    assert "`RuntimeError`" in text


def test_production_python_code_avoids_assertionerror_runtime_guards() -> None:
    findings: list[str] = []
    for root in PYTHON_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "tests" in path.relative_to(root).parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative_path = path.relative_to(REPO_ROOT)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    findings.append(f"{relative_path}:{node.lineno}: assert")
                if isinstance(node, ast.Raise) and raises_assertion_error(node):
                    findings.append(f"{relative_path}:{node.lineno}: raise AssertionError")

    assert not findings, "\n".join(findings)


def raises_assertion_error(node: ast.Raise) -> bool:
    exc = node.exc
    if isinstance(exc, ast.Call):
        exc = exc.func
    return isinstance(exc, ast.Name) and exc.id == "AssertionError"
