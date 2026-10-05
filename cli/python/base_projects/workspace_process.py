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
    """Run a delegated command with bounded POSIX process-group cleanup.

    POSIX commands run in an isolated session so ordinary descendants can be
    terminated together. Windows intentionally retains the standard-library
    direct-child behavior; native process-tree cleanup requires a Job Object,
    which is outside the supported scope of this workspace lifecycle boundary.
    """

    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        start_new_session=os.name != "nt",
    ) as process:
        previous_handlers = _install_signal_forwarders(process)
        try:
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
            except BaseException:
                _terminate_process_tree(process)
                raise
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        finally:
            _restore_signal_handlers(previous_handlers)


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> tuple[bytes | None, bytes | None]:
    _signal_process_group(process, signal.SIGTERM)
    try:
        return process.communicate(timeout=PROCESS_GROUP_GRACE_SECONDS)
    except subprocess.TimeoutExpired as graceful_timeout:
        # SIGKILL is not defined by Python's Windows signal module. On Windows
        # this falls back to SIGTERM, which still terminates the direct child.
        _signal_process_group(process, getattr(signal, "SIGKILL", signal.SIGTERM))
        try:
            return process.communicate(timeout=PROCESS_GROUP_GRACE_SECONDS)
        except subprocess.TimeoutExpired as final_timeout:
            # A descendant can leave the process group while retaining an
            # inherited pipe. Never wait forever for that pipe to close.
            return (
                final_timeout.output
                if final_timeout.output is not None
                else graceful_timeout.output,
                final_timeout.stderr
                if final_timeout.stderr is not None
                else graceful_timeout.stderr,
            )


def _signal_process_group(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        if os.name == "nt":
            # Windows has no portable stdlib process-tree primitive; this
            # reliably signals the direct child only.
            process.send_signal(signum)
            return
        # start_new_session=True makes the direct child's PID its process
        # group ID, keeping killpg confined to this delegated command.
        os.killpg(process.pid, signum)
    except OSError:
        return


def _install_signal_forwarders(process: subprocess.Popen[bytes]) -> dict[int, object]:
    if os.name == "nt":
        return {}

    previous_handlers: dict[int, object] = {}

    def forward_signal(signum: int, frame: object) -> None:
        _signal_process_group(process, signum)
        previous = previous_handlers[signum]
        if previous == signal.SIG_IGN:
            return
        if previous == signal.SIG_DFL:
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
            return
        if callable(previous):
            previous(signum, frame)

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, forward_signal)
    return previous_handlers


def _restore_signal_handlers(previous_handlers: dict[int, object]) -> None:
    for signum, handler in previous_handlers.items():
        signal.signal(signum, handler)
