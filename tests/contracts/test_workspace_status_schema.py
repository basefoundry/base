from __future__ import annotations

import json
from pathlib import Path

from tests.contracts.workspace_contract_helpers import run_workspace_command
from tests.contracts.workspace_contract_helpers import validate_workspace_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs/schemas/workspace-status.json"


def test_workspace_status_command_matches_published_schema(tmp_path: Path) -> None:
    home = tmp_path / "home"
    base_home = tmp_path / "base"
    workspace = tmp_path / "workspace"
    manifest_path = tmp_path / "workspace.yaml"
    home.mkdir()
    base_home.mkdir()
    workspace.mkdir()

    for args, manifest_backed, expected_project_count in (
        (["status", "--workspace", str(workspace), "--format", "json"], False, 0),
        (
            ["status", "--workspace", str(workspace), "--manifest", str(manifest_path), "--format", "json"],
            True,
            1,
        ),
    ):
        if manifest_backed:
            manifest_path.write_text(
                "schema_version: 1\nworkspace:\n  name: status-suite\nrepos:\n  - name: demo\n",
                encoding="utf-8",
            )
            (workspace / "demo").mkdir()
            (workspace / "demo" / "base_manifest.yaml").write_text(
                "project:\n  name: demo\nartifacts: []\n", encoding="utf-8"
            )

        result = run_workspace_command(args, base_home, home)

        assert result.returncode == 0
        assert result.stderr == ""
        payload = json.loads(result.stdout)
        validate_workspace_payload(payload, SCHEMA_PATH)
        assert payload["schema_version"] == 1
        assert payload["project_count"] == expected_project_count
        if manifest_backed:
            assert payload["workspace_manifest"]["name"] == "status-suite"
            assert payload["repository_count"] == 1

    discovery_workspace = tmp_path / "discovery-workspace"
    discovery_workspace.mkdir()
    (discovery_workspace / "discovered").mkdir()
    (discovery_workspace / "discovered" / "base_manifest.yaml").write_text(
        "project:\n  name: discovered\nartifacts: []\n", encoding="utf-8"
    )
    result = run_workspace_command(
        ["status", "--workspace", str(discovery_workspace), "--format", "json"],
        base_home,
        home,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    validate_workspace_payload(payload, SCHEMA_PATH)
    assert payload["schema_version"] == 1
    assert payload["project_count"] == 1
    assert payload["projects"][0]["name"] == "discovered"
