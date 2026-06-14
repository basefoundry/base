from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path
from typing import Any


def invoke(
    app: Any,
    args: list[str] | None = None,
    home: Path | None = None,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
):
    try:
        from click.testing import CliRunner
    except ImportError as exc:
        raise RuntimeError("Click is required for base_cli.testing. Run 'basectl setup' to install it.") from exc

    runner_env = dict(env or {})
    if home is not None:
        home = Path(home)
        runner_env.setdefault("HOME", str(home))
        runner_env.setdefault("BASE_CACHE_DIR", str(_cache_dir_for_home(home)))
    runner_kwargs = {}
    if "mix_stderr" in inspect.signature(CliRunner).parameters:
        runner_kwargs["mix_stderr"] = False
    runner = CliRunner(**runner_kwargs)
    original_cwd = Path.cwd()
    if cwd is not None:
        os.chdir(cwd)
    try:
        return runner.invoke(app.click_command, args or [], env=runner_env)
    finally:
        if cwd is not None:
            os.chdir(original_cwd)


def _cache_dir_for_home(home: Path) -> Path:
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "base"
    return home / ".cache" / "base"
