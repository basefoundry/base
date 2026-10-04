from __future__ import annotations

import json
from pathlib import Path

from tests.contracts.workspace_contract_helpers import run_workspace_command
from tests.contracts.workspace_contract_helpers import validate_workspace_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs/schemas/workspace-test.json"


def test_workspace_test_command_matches_published_schema(tmp_path: Path) -> None:
    home = tmp_path / "home"
    base_home = tmp_path / "base"
    workspace = tmp_path / "workspace"
    manifest_path = tmp_path / "workspace.yaml"
    home.mkdir()
    (base_home / "bin").mkdir(parents=True)
    workspace.mkdir()

    fake_basectl = base_home / "bin" / "basectl"
    fake_basectl.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ -x ./run-tests.sh ]]; then exec ./run-tests.sh; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_basectl.chmod(0o755)

    (workspace / "pass").mkdir()
    (workspace / "pass" / "base_manifest.yaml").write_text(
        "project:\n  name: pass\ntest:\n  command: ./run-tests.sh\nartifacts: []\n",
        encoding="utf-8",
    )
    (workspace / "pass" / "run-tests.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'token=masked\n'\n", encoding="utf-8"
    )
    (workspace / "pass" / "run-tests.sh").chmod(0o755)
    (workspace / "fail").mkdir()
    (workspace / "fail" / "base_manifest.yaml").write_text(
        "project:\n  name: fail\ntest:\n  command: ./run-tests.sh\nartifacts: []\n",
        encoding="utf-8",
    )
    (workspace / "fail" / "run-tests.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'failed\n' >&2\nexit 3\n", encoding="utf-8"
    )
    (workspace / "fail" / "run-tests.sh").chmod(0o755)
    (workspace / "skipped").mkdir()
    (workspace / "skipped" / "base_manifest.yaml").write_text(
        "project:\n  name: skipped\nartifacts: []\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        "schema_version: 1\nworkspace:\n  name: test-suite\nrepos:\n"
        "  - name: pass\n  - name: fail\n  - name: skipped\n  - name: missing\n",
        encoding="utf-8",
    )

    result = run_workspace_command(
        [
            "test",
            "--workspace",
            str(workspace),
            "--manifest",
            str(manifest_path),
            "--format",
            "json",
        ],
        base_home,
        home,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    validate_workspace_payload(payload, SCHEMA_PATH)
    assert payload["counts"] == {"passed": 1, "failed": 2, "skipped": 1}
    assert payload["projects"][1]["exit_code"] == 3
    assert payload["projects"][1]["stderr"] == "failed\n"
    assert payload["projects"][3]["project"] is None
    assert payload["projects"][3]["status"] == "failed"
