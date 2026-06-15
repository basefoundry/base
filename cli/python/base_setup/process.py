from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, TextIO

import base_cli

from .errors import ArtifactError


COMMAND_OUTPUT_TAIL_CHARS = 4000
SECRET_VALUE_RE = re.compile(
    r"(?i)(?P<name>[A-Za-z0-9_.:-]*(?:token|password|secret|api[-_]?key)[A-Za-z0-9_.:-]*)=\S+"
)
URL_CREDENTIALS_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)[^/\s:@]+:[^@\s/]+@")
HOMEBREW_LINK_FAILURE = "The `brew link` step did not complete successfully"
HOMEBREW_LINK_DRY_RUN_RE = re.compile(r"(?m)^\s*(brew link --overwrite [^\r\n]+ --dry-run)\s*$")


@dataclass
class CommandOutputRecorder:
    limit: int = COMMAND_OUTPUT_TAIL_CHARS
    _chunks: deque[str] = field(default_factory=deque)
    _length: int = 0

    def append(self, text: str) -> None:
        if not text:
            return
        redacted = redact_command_output(text)
        self._chunks.append(redacted)
        self._length += len(redacted)
        while self._length > self.limit and len(self._chunks) > 1:
            removed = self._chunks.popleft()
            self._length -= len(removed)
        if self._length > self.limit and self._chunks:
            self._chunks[0] = self._chunks[0][-self.limit :]
            self._length = self.limit

    def text(self) -> str:
        value = "".join(self._chunks)
        if len(value) <= self.limit:
            return value.strip()
        return value[-self.limit:].strip()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_check(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def run_capture(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    stdout_recorder = CommandOutputRecorder()
    stderr_recorder = CommandOutputRecorder()
    with subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        assert process.stdout is not None
        assert process.stderr is not None
        threads = (
            threading.Thread(
                target=_tee_stream,
                args=(ctx, process.stdout, sys.stdout, "stdout", stdout_recorder),
                daemon=True,
            ),
            threading.Thread(
                target=_tee_stream,
                args=(ctx, process.stderr, sys.stderr, "stderr", stderr_recorder),
                daemon=True,
            ),
        )
        for thread in threads:
            thread.start()
        returncode = process.wait()
        for thread in threads:
            thread.join()
    if returncode:
        message = f"Command failed with exit {returncode}: {redact_command_output(format_command(command))}"
        stdout_tail = stdout_recorder.text()
        stderr_tail = stderr_recorder.text()
        if stdout_tail:
            message = f"{message}\nstdout:\n{stdout_tail}"
        if stderr_tail:
            message = f"{message}\nstderr:\n{stderr_tail}"
        guidance = command_failure_guidance(stdout_tail, stderr_tail)
        if guidance:
            message = f"{message}\n\n{guidance}"
        raise ArtifactError(message)
    if cwd is not None:
        ctx.log.debug("Command succeeded in '%s': %s", cwd, format_command(command))
    else:
        ctx.log.debug("Command succeeded: %s", format_command(command))


def dry_run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    if cwd is not None:
        ctx.log.info("[DRY-RUN] Would run in '%s': %s", cwd, format_command(command))
        return
    ctx.log.info("[DRY-RUN] Would run: %s", format_command(command))


def format_command(command: list[str]) -> str:
    return shlex.join(command)


def redact_command_output(text: str) -> str:
    text = URL_CREDENTIALS_RE.sub(r"\1[REDACTED]@", text)
    return SECRET_VALUE_RE.sub(lambda match: f"{match.group('name')}=[REDACTED]", text)


def command_failure_guidance(stdout_tail: str, stderr_tail: str) -> str:
    output = "\n".join(part for part in (stdout_tail, stderr_tail) if part)
    return homebrew_link_failure_guidance(output)


def homebrew_link_failure_guidance(output: str) -> str:
    if HOMEBREW_LINK_FAILURE not in output:
        return ""

    match = HOMEBREW_LINK_DRY_RUN_RE.search(output)
    if match is None:
        return (
            "Homebrew reported a link conflict while installing a dependency. "
            "Review Homebrew's conflicting-file list, repair the link conflict, "
            "then rerun the Base command."
        )

    dry_run_command_text = match.group(1)
    repair_command_text = dry_run_command_text.removesuffix(" --dry-run")
    return (
        "Homebrew reported a link conflict while installing a dependency. "
        "Review the files Homebrew would overwrite before repairing it:\n"
        f"  {dry_run_command_text}\n"
        "If the dry-run only lists stale files you are comfortable replacing, run:\n"
        f"  {repair_command_text}\n"
        "Then rerun the Base command."
    )


def _write_bytes(target: TextIO, chunk: bytes) -> None:
    buffer = getattr(target, "buffer", None)
    if buffer is not None:
        buffer.write(chunk)
    else:
        target.write(chunk.decode(errors="replace"))
    target.flush()


def _log_lines(ctx: base_cli.Context, label: str, text: str, pending: str) -> str:
    pending += text
    lines = pending.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        pending = lines.pop()
    else:
        pending = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            ctx.log.debug("Command %s: %s", label, redact_command_output(stripped))
    return pending


def _tee_stream(
    ctx: base_cli.Context,
    stream: BinaryIO,
    target: TextIO,
    label: str,
    recorder: CommandOutputRecorder,
) -> None:
    pending = ""
    try:
        while True:
            chunk = os.read(stream.fileno(), 4096)
            if not chunk:
                break
            _write_bytes(target, chunk)
            text = chunk.decode(errors="replace")
            recorder.append(text)
            pending = _log_lines(ctx, label, text, pending)
        if pending.strip():
            ctx.log.debug("Command %s: %s", label, redact_command_output(pending.strip()))
    finally:
        stream.close()
