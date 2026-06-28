from __future__ import annotations

import ast
from pathlib import Path


STANDARD_EXIT_VALUES = {0, 1, 2}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def iter_production_cli_python_files() -> list[Path]:
    cli_root = repository_root() / "cli" / "python"
    return sorted(
        path
        for path in cli_root.rglob("*.py")
        if "tests" not in path.relative_to(cli_root).parts
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


def test_production_cli_code_uses_exit_code_constants_for_standard_returns() -> None:
    findings: list[str] = []
    for path in iter_production_cli_python_files():
        findings.extend(raw_standard_exit_returns(path))

    assert not findings, "\n".join(findings)
