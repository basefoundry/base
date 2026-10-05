from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from base_projects import workspace_process
from base_projects.workspace_process import run_workspace_subprocess


class WorkspaceProcessTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "process groups are POSIX-only")
    def test_timeout_terminates_descendants_before_returning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "spawn-child.py"
            started = root / "descendant-started"
            sentinel = root / "descendant-was-not-terminated"
            child_code = (
                "import os, pathlib, time; "
                "pathlib.Path(os.environ['TREE_STARTED']).write_text(str(os.getpgid(0)), encoding='utf-8'); "
                "time.sleep(5); "
                "pathlib.Path(os.environ['TREE_SENTINEL']).write_text('leaked', encoding='utf-8')"
            )
            script.write_text(
                "import os, pathlib, subprocess, sys, time\n"
                f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                "deadline = time.monotonic() + 5\n"
                "while not pathlib.Path(os.environ['TREE_STARTED']).exists() and time.monotonic() < deadline:\n"
                "    time.sleep(0.01)\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )

            environment = os.environ.copy()
            environment["TREE_STARTED"] = str(started)
            environment["TREE_SENTINEL"] = str(sentinel)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_workspace_subprocess(
                    [sys.executable, str(script)],
                    cwd=root,
                    env=environment,
                    timeout=2.0,
                )

            self.assertTrue(started.exists(), "grandchild never started; test would pass vacuously")
            time.sleep(0.6)
            self.assertFalse(sentinel.exists())
            process_group = int(started.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.killpg(process_group, 0)

    def test_timeout_escalation_does_not_require_sigkill_on_windows(self) -> None:
        class FakeProcess:
            pid = 123

            def __init__(self) -> None:
                self.signals: list[int] = []

            def send_signal(self, signum: int) -> None:
                self.signals.append(signum)

            def communicate(self, *, timeout: float) -> tuple[bytes, bytes]:
                raise subprocess.TimeoutExpired(
                    ["fake"], timeout, output=b"partial stdout", stderr=b"partial stderr"
                )

        process = FakeProcess()
        signal_without_sigkill = SimpleNamespace(SIGTERM=15, SIGINT=2, SIG_DFL=0, SIG_IGN=1)
        with (
            mock.patch.object(workspace_process.os, "name", "nt"),
            mock.patch.object(workspace_process, "signal", signal_without_sigkill),
        ):
            stdout, stderr = workspace_process._terminate_process_tree(process)  # pylint: disable=protected-access

        self.assertEqual(process.signals, [15, 15])
        self.assertEqual(stdout, b"partial stdout")
        self.assertEqual(stderr, b"partial stderr")
