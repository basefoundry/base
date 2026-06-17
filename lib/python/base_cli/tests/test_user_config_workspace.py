from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_cli.config import read_user_config
from base_cli.config import user_config_path


class WorkspaceUserConfigTests(unittest.TestCase):
    def test_read_user_config_rejects_empty_workspace_manifest_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            path = user_config_path(home)
            path.parent.mkdir(parents=True)
            path.write_text("workspace:\n  manifest_source: ''\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "workspace.manifest_source must be a non-empty string"):
                read_user_config(home)


if __name__ == "__main__":
    unittest.main()
