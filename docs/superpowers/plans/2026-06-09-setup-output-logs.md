# Setup Output Logs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist useful external setup command stdout/stderr in Base logs while keeping live terminal progress.

**Architecture:** Keep the behavior centralized in `cli/python/base_setup/process.py`, because project artifacts, Brewfile/mise delegates, IDE setup, and prerequisite profiles already use `run_command()`. Add a tee-style subprocess helper that streams stdout/stderr live, logs redacted chunks, and retains bounded redacted tails for failure summaries.

**Tech Stack:** Python standard library `subprocess`, `threading`, `os`, `sys`, `re`, and existing `base_cli.Context` logging.

---

## File Structure

- Modify `cli/python/base_setup/process.py`: subprocess tee helper, redaction, bounded tails, updated `run_command()`.
- Modify `cli/python/base_setup/tests/test_artifacts.py`: focused process tests for streaming, logging, failure tails, and redaction.
- Add `docs/superpowers/specs/2026-06-09-setup-output-logs-design.md`: design record.
- Add `docs/superpowers/plans/2026-06-09-setup-output-logs.md`: this implementation plan.

## Task 1: Failing Process Tests

**Files:**
- Modify: `cli/python/base_setup/tests/test_artifacts.py`

- [ ] **Step 1: Add tests for streamed and logged command output**

Add imports near the top:

```python
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
```

Add these tests to `ProcessTests`:

```python
    def test_run_command_streams_and_logs_stdout_and_stderr(self) -> None:
        ctx = fake_context()
        stdout = io.StringIO()
        stderr = io.StringIO()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('install stdout'); "
                "print('install stderr', file=sys.stderr)"
            ),
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            process.run_command(ctx, command)

        self.assertIn("install stdout", stdout.getvalue())
        self.assertIn("install stderr", stderr.getvalue())
        debug_messages = [call.args[0] % call.args[1:] for call in ctx.log.debug.call_args_list]
        self.assertIn("Command stdout: install stdout", debug_messages)
        self.assertIn("Command stderr: install stderr", debug_messages)
```

- [ ] **Step 2: Add failure-tail and redaction tests**

Add these tests to `ProcessTests`:

```python
    def test_run_command_failure_includes_bounded_stdout_and_stderr_tail(self) -> None:
        ctx = fake_context()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('stdout before failure'); "
                "print('stderr before failure', file=sys.stderr); "
                "raise SystemExit(17)"
            ),
        ]

        with self.assertRaises(ArtifactError) as exc:
            process.run_command(ctx, command)

        message = str(exc.exception)
        self.assertIn("Command failed with exit 17", message)
        self.assertIn("stdout:", message)
        self.assertIn("stdout before failure", message)
        self.assertIn("stderr:", message)
        self.assertIn("stderr before failure", message)

    def test_run_command_redacts_sensitive_output_from_logs_and_failure(self) -> None:
        ctx = fake_context()
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('url=https://user:secret@example.invalid/pkg.whl'); "
                "print('token=super-secret', file=sys.stderr); "
                "raise SystemExit(9)"
            ),
        ]

        with self.assertRaises(ArtifactError) as exc:
            process.run_command(ctx, command)

        message = str(exc.exception)
        debug_text = "\n".join(str(call.args) for call in ctx.log.debug.call_args_list)
        self.assertNotIn("super-secret", message)
        self.assertNotIn("super-secret", debug_text)
        self.assertNotIn("user:secret", message)
        self.assertNotIn("user:secret", debug_text)
        self.assertIn("[REDACTED]", message)
        self.assertIn("[REDACTED]", debug_text)
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_setup/tests/test_artifacts.py
```

Expected: FAIL because current `run_command()` does not log stdout, does not capture stdout tails, and has no output redaction.

## Task 2: Tee Executor Implementation

**Files:**
- Modify: `cli/python/base_setup/process.py`

- [ ] **Step 1: Add imports and constants**

Add:

```python
import os
import re
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import BinaryIO, TextIO
```

Add constants:

```python
COMMAND_OUTPUT_TAIL_CHARS = 4000
SECRET_VALUE_RE = re.compile(r"(?i)\b(token|password|secret|api[-_]?key)=\S+")
URL_CREDENTIALS_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)[^/\s:@]+:[^@\s/]+@")
```

- [ ] **Step 2: Add bounded output recorder**

Add:

```python
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
        while self._length > self.limit and self._chunks:
            removed = self._chunks.popleft()
            self._length -= len(removed)

    def text(self) -> str:
        value = "".join(self._chunks)
        if len(value) <= self.limit:
            return value.strip()
        return value[-self.limit:].strip()
```

- [ ] **Step 3: Add output redaction**

Add:

```python
def redact_command_output(text: str) -> str:
    text = URL_CREDENTIALS_RE.sub(r"\1[REDACTED]@", text)
    return SECRET_VALUE_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
```

- [ ] **Step 4: Add stream helpers**

Add:

```python
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
```

Add:

```python
def _tee_stream(
    ctx: base_cli.Context,
    stream: BinaryIO,
    target: TextIO,
    label: str,
    recorder: CommandOutputRecorder,
) -> None:
    pending = ""
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
```

- [ ] **Step 5: Replace `run_command()` subprocess call**

Replace the current implementation with:

```python
def run_command(ctx: base_cli.Context, command: list[str], cwd: Path | None = None) -> None:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout_recorder = CommandOutputRecorder()
    stderr_recorder = CommandOutputRecorder()
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
        message = f"Command failed with exit {returncode}: {format_command(command)}"
        stdout_tail = stdout_recorder.text()
        stderr_tail = stderr_recorder.text()
        if stdout_tail:
            message = f"{message}\nstdout:\n{stdout_tail}"
        if stderr_tail:
            message = f"{message}\nstderr:\n{stderr_tail}"
        raise ArtifactError(message)
    if cwd is not None:
        ctx.log.debug("Command succeeded in '%s': %s", cwd, format_command(command))
    else:
        ctx.log.debug("Command succeeded: %s", format_command(command))
```

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_setup/tests/test_artifacts.py
```

Expected: PASS.

## Task 3: Validation and Commit

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_setup/tests/test_artifacts.py
```

Expected: PASS.

- [ ] **Step 2: Run full validation**

Run:

```bash
env -u BASE_HOME ./bin/base-test
git diff --check
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
git add cli/python/base_setup/process.py cli/python/base_setup/tests/test_artifacts.py docs/superpowers/specs/2026-06-09-setup-output-logs-design.md docs/superpowers/plans/2026-06-09-setup-output-logs.md
git commit -m "Persist setup command output in logs"
```
