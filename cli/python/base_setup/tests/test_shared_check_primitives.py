from __future__ import annotations

import io
import os
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from base_dev import checks as dev_checks
from base_dev.checks import DevCheck
from base_setup import checks as setup_checks


def test_check_adapters_share_status_and_serialization_primitives() -> None:
    dev_check = DevCheck(name="dev", ok=True, message="ready", fix="")
    setup_check = setup_checks.ArtifactCheck(
        name="setup",
        ok=True,
        message="ready",
        fix="",
        finding_id="BASE-P040",
        details={"source": "test"},
    )

    assert dev_checks.checks_status(()) == setup_checks.checks_status(()) == "ok"
    assert dev_checks.checks_status((dev_check,)) == setup_checks.checks_status((setup_check,)) == "ok"
    assert dev_checks.check_to_json(dev_check) == {
        "id": "BASE-D100",
        "status": "ok",
        "name": "dev",
        "message": "ready",
        "fix": "",
    }
    assert setup_checks.check_to_json(setup_check)["details"] == {"source": "test"}

    warning_dev = DevCheck(name="dev", ok=False, message="warning", fix="", status="warn")
    error_setup = setup_checks.ArtifactCheck(
        name="setup", ok=False, message="error", fix="", finding_id="BASE-P041"
    )
    error_dev = DevCheck(name="dev", ok=False, message="error", fix="")
    assert dev_checks.checks_status((warning_dev,)) == "warn"
    assert dev_checks.checks_status((warning_dev, error_dev)) == "error"
    assert setup_checks.checks_status((setup_check, error_setup)) == "error"
    assert setup_checks.merge_statuses("ok", "warn") == "warn"
    assert setup_checks.merge_statuses("warn", "error") == "error"


def test_doctor_adapters_preserve_plain_and_visual_tty_styles() -> None:
    class TtyBuffer(io.StringIO):
        def isatty(self) -> bool:
            return True

    dev_stderr, setup_stderr = TtyBuffer(), TtyBuffer()
    with (
        mock.patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True),
        redirect_stderr(dev_stderr),
    ):
        dev_checks.print_doctor_finding("warn", "BASE-D100", "dev", "warning", "fix dev")
    with (
        mock.patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True),
        redirect_stderr(setup_stderr),
    ):
        setup_checks.print_doctor_finding("warn", "BASE-P040", "setup", "warning", "fix setup")

    assert "\033[" not in dev_stderr.getvalue()
    assert dev_stderr.getvalue().endswith("Fix: fix dev\n")
    assert "\033[0;33m! warn\033[0m" in setup_stderr.getvalue()
    assert setup_stderr.getvalue().endswith("Fix: fix setup\n")


def test_setup_color_controls_and_stream_routing_are_preserved() -> None:
    class TtyBuffer(io.StringIO):
        def isatty(self) -> bool:
            return True

    stdout, stderr = TtyBuffer(), TtyBuffer()
    with (
        mock.patch.dict(
            os.environ,
            {"TERM": "xterm-256color", "BASE_SETUP_DOCTOR_NO_COLOR": "true"},
            clear=True,
        ),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        setup_checks.print_doctor_finding("ok", "BASE-P040", "setup", "ready")
        setup_checks.print_doctor_finding("error", "BASE-P041", "setup", "broken", "fix it")

    assert "BASE-P040" in stdout.getvalue()
    assert "\033[" not in stdout.getvalue()
    assert not stderr.getvalue().startswith("ok")
    assert stderr.getvalue().startswith("error")
    assert stderr.getvalue().endswith("Fix: fix it\n")
