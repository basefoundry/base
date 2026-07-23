from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COMMAND_ROOT = REPO_ROOT / "cli" / "python"


def test_public_python_command_engines_use_base_cli_app_or_declared_exemption() -> None:
    bypasses = []
    for engine_path in sorted(PUBLIC_COMMAND_ROOT.glob("base_*/engine.py")):
        source = engine_path.read_text(encoding="utf-8")
        if "base_cli.App(" not in source:
            bypasses.append(engine_path.parent.name)

    assert not bypasses
