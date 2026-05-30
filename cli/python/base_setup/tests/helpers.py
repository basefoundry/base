from __future__ import annotations

import io
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_setup.engine import main


def run_engine(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        with mock.patch.dict(
            os.environ,
            {"HOME": home_dir, "BASE_HOME": str(Path(__file__).resolve().parents[4])},
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def fake_context() -> mock.Mock:
    ctx = mock.Mock()
    ctx.log = mock.Mock()
    return ctx
