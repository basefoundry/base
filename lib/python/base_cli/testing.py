from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any


def invoke(app: Any, args: list[str] | None = None, home: Path | None = None):
    try:
        from click.testing import CliRunner
    except ImportError as exc:
        raise RuntimeError("Click is required for base_cli.testing. Run 'basectl setup' to install it.") from exc

    env = {}
    if home is not None:
        env["HOME"] = str(home)
    runner_kwargs = {}
    if "mix_stderr" in inspect.signature(CliRunner).parameters:
        runner_kwargs["mix_stderr"] = False
    runner = CliRunner(**runner_kwargs)
    return runner.invoke(app.click_command, args or [], env=env)
