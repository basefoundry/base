from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
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
