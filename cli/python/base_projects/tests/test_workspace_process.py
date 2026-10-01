from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from base_projects.workspace_process import run_workspace_subprocess


class WorkspaceProcessTests(unittest.TestCase):
    def test_timeout_terminates_descendants_before_returning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "spawn-child.py"
            sentinel = root / "descendant-was-not-terminated"
            child_code = (
                "import os, pathlib, time; "
                "time.sleep(0.4); "
                "pathlib.Path(os.environ['TREE_SENTINEL']).write_text('leaked', encoding='utf-8')"
            )
            script.write_text(
                "import os, subprocess, sys, time\n"
                f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )

            environment = os.environ.copy()
            environment["TREE_SENTINEL"] = str(sentinel)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_workspace_subprocess(
                    [sys.executable, str(script)],
                    cwd=root,
                    env=environment,
                    timeout=0.05,
                )

            time.sleep(0.6)
            self.assertFalse(sentinel.exists())
