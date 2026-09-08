from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def test_base_release_bom_row_emits_the_base_release_contract(tmp_path: Path) -> None:
    output = tmp_path / "base-row.json"
    commit = "a" * 40
    subprocess.run(
        [
            str(ROOT / "bin" / "base-release-bom-row"),
            "--version",
            "1.9.0",
            "--commit",
            commit,
            "--evidence",
            "run://base/123",
            "--platform",
            "ubuntu-24.04",
            "--platform",
            "macos-14",
            "--output",
            str(output),
        ],
        check=True,
    )

    assert json.loads(output.read_text(encoding="utf-8")) == {
        "api_schema_version": "manifest-1",
        "commit": commit,
        "evidence": "run://base/123",
        "platforms": ["macos-14", "ubuntu-24.04"],
        "repository": "basefoundry/base",
        "required": True,
        "result": "passed",
        "source_mode": "release",
        "tag": "v1.9.0",
        "version": "1.9.0",
    }
