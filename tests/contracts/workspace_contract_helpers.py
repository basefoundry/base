from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
from referencing import Registry, Resource


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_MANIFEST_SCHEMA = REPO_ROOT / "docs/schemas/workspace-manifest.json"


def validate_workspace_payload(payload: object, schema_path: Path) -> dict[str, object]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest_schema = json.loads(WORKSPACE_MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator.check_schema(manifest_schema)
    registry = Registry().with_resource(
        manifest_schema["$id"],
        Resource.from_contents(manifest_schema),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(payload)
    return schema


def run_workspace_command(args: list[str], base_home: Path, home: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "BASE_HOME": str(base_home),
            "BASE_PROJECT": "",
            "BASE_PROJECT_MANIFEST": "",
            "HOME": str(home),
            "PYTHONPATH": os.pathsep.join(
                [str(REPO_ROOT / "lib/python"), str(REPO_ROOT / "cli/python"), environment.get("PYTHONPATH", "")]
            ),
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "base_projects", *args],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
