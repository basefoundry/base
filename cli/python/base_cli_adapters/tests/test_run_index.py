from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from base_cli_adapters import run_index


class RunIndexTests(unittest.TestCase):
    def test_main_refreshes_stale_bundle_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_root = Path(tmpdir)
            stale_path = runs_root / "missing-run"
            (runs_root / ".base-cli-run-index.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "bundles": [
                            {
                                "path": str(stale_path),
                                "run_id": stale_path.name,
                                "status": "running",
                                "started_at": 1,
                                "size": 1,
                                "preserve": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            status = run_index.main([str(runs_root)])
            payload = json.loads(
                (runs_root / ".base-cli-run-index.json").read_text(encoding="utf-8")
            )

        self.assertEqual(status, 0)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["bundles"], [])

        # The provider owns additive index metadata. Base consumes only version
        # and bundles; known optional summaries retain their documented meaning.
        if "complete" in payload:
            self.assertTrue(payload["complete"])
        if "omitted_bundles" in payload:
            self.assertEqual(payload["omitted_bundles"], 0)

    def test_main_rejects_invalid_arguments(self) -> None:
        self.assertEqual(run_index.main([]), 2)


def test_direct_run_index_reports_provider_incompatibility(capsys) -> None:
    from unittest.mock import patch  # pylint: disable=import-outside-toplevel
    from base_cli_adapters.provider import BaseCliCompatibilityError  # pylint: disable=import-outside-toplevel

    with patch.object(run_index, "load_run_index_runtime", side_effect=BaseCliCompatibilityError("provider missing")):
        assert run_index.main(["unused-runs-root"]) == 1
    assert "ERROR: provider missing" in capsys.readouterr().err
