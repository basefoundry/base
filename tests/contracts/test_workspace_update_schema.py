from __future__ import annotations

import json
import subprocess
from pathlib import Path

import jsonschema

from tests.contracts.workspace_contract_helpers import run_workspace_command


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "workspace-update.json"


def test_workspace_update_command_matches_published_schema(tmp_path: Path) -> None:
    home = tmp_path / "home"
    base_home = tmp_path / "base"
    workspace = tmp_path / "workspace"
    manifest_path = tmp_path / "workspace.yaml"
    home.mkdir()
    base_home.mkdir()
    workspace.mkdir()
    for name in ("first", "later"):
        repository = workspace / name
        remote = tmp_path / f"{name}.git"
        subprocess.run(
            ["git", "init", "--initial-branch=main", str(repository)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Workspace Test"], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.email", "workspace-test@example.com"],
            check=True,
        )
        (repository / "README.md").write_text(f"{name}\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(repository), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "push", "--set-upstream", "origin", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
    manifest_path.write_text(
        "schema_version: 1\n"
        "workspace:\n"
        "  name: update-suite\n"
        "repos:\n"
        "  - name: first\n"
        "    default_branch: main\n"
        "  - name: later\n"
        "    default_branch: main\n",
        encoding="utf-8",
    )

    result = run_workspace_command(
        [
            "update",
            "--workspace",
            str(workspace),
            "--manifest",
            str(manifest_path),
            "--repos",
            "later,first",
            "--dry-run",
            "--format",
            "json",
        ],
        base_home,
        home,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)
    assert payload["schema_version"] == 1
    assert payload["selected_repositories"] == ["first", "later"]
