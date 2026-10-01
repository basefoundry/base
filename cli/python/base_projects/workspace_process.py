from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path


PROCESS_GROUP_GRACE_SECONDS = 1.0


def run_workspace_subprocess(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[bytes]:
    """Run one delegated command and clean up its process tree on timeout."""

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = _terminate_process_tree(process)
        raise subprocess.TimeoutExpired(
            command,
            timeout,
            output=stdout if stdout is not None else exc.output,
            stderr=stderr if stderr is not None else exc.stderr,
        ) from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> tuple[bytes | None, bytes | None]:
    _signal_process_group(process, signal.SIGTERM)
    try:
        return process.communicate(timeout=PROCESS_GROUP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        _signal_process_group(process, signal.SIGKILL)
        return process.communicate()


def _signal_process_group(process: subprocess.Popen[bytes], signum: signal.Signals) -> None:
    if os.name == "nt":
        process.send_signal(signum)
        return
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        return
