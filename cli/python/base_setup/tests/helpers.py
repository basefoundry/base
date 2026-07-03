from __future__ import annotations

import io
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_cli.config import UserConfig, UserIdeConfig
from base_setup.engine import main


PROJECT_RUNTIME_ENV_VARS = (
    "BASE_PROJECT",
    "BASE_PROJECT_ROOT",
    "BASE_PROJECT_MANIFEST",
    "BASE_PROJECT_VENV_DIR",
)


def run_engine(args: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        env = {"HOME": home_dir, "BASE_HOME": str(Path(__file__).resolve().parents[4])}
        if extra_env:
            env.update(extra_env)
        with mock.patch.dict(
            os.environ,
            env,
        ):
            for name in PROJECT_RUNTIME_ENV_VARS:
                if extra_env is None or name not in extra_env:
                    os.environ.pop(name, None)
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def fake_context() -> mock.Mock:
    ctx = mock.Mock()
    ctx.log = mock.Mock()
    ctx.user_config = UserConfig(raw={}, ide=UserIdeConfig(enabled=None, preferences={}))
    return ctx
