"""Shared invocation helpers for workspace CLI tests."""

from __future__ import annotations

import io
import os
from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


# Keep per-test overrides explicit instead of hiding them in a configuration object.
def invoke_engine(  # pylint: disable=too-many-arguments
    args: list[str],
    base_home: Path,
    home: Path,
    user_config: str | None = None,
    *,
    stdout_stream: io.StringIO | None = None,
    stderr_stream: io.StringIO | None = None,
    env_overrides: Mapping[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run the project engine with explicit temporary HOME and stream controls."""
    stdout = stdout_stream if stdout_stream is not None else TerminalStringIO()
    stderr = stderr_stream if stderr_stream is not None else io.StringIO()
    if user_config is not None:
        config_path = home / ".base.d" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(user_config, encoding="utf-8")

    env = {
        "HOME": str(home),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_MANIFEST": "",
    }
    if env_overrides is not None:
        env.update(env_overrides)

    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()
