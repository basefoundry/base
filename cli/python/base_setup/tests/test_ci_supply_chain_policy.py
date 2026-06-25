from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
FULL_SHA_RE = re.compile(r"[a-f0-9]{40}")
FIRST_PARTY_ACTION_REF_RE = re.compile(r"v\d+|[a-f0-9]{40}")


def load_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def workflow_steps(path: Path) -> list[dict[str, Any]]:
    workflow = load_workflow(path)
    steps: list[dict[str, Any]] = []
    for job in workflow["jobs"].values():
        steps.extend(job.get("steps", ()))
    return steps


def test_github_actions_references_follow_supply_chain_policy() -> None:
    workflow_paths = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))

    for path in workflow_paths:
        for step in workflow_steps(path):
            uses = step.get("uses")
            if not uses:
                continue

            action, separator, ref = uses.partition("@")
            assert separator, f"{path}: action reference '{uses}' must include an explicit ref."
            owner = action.split("/", 1)[0]
            if owner == "actions":
                assert FIRST_PARTY_ACTION_REF_RE.fullmatch(ref), (
                    f"{path}: first-party action '{uses}' must use a maintained major tag or full SHA."
                )
            else:
                assert FULL_SHA_RE.fullmatch(ref), f"{path}: third-party action '{uses}' must be pinned to a full SHA."


def test_security_workflow_runs_python_dependency_audit() -> None:
    requirements = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert re.search(r"^pip-audit==", requirements, re.MULTILINE)

    security_steps = workflow_steps(REPO_ROOT / ".github" / "workflows" / "tests.yml")
    audit_steps = [step for step in security_steps if step.get("name") == "Run pip-audit"]

    assert audit_steps, "tests.yml security job must run pip-audit."
    audit_command = audit_steps[0].get("run", "")
    assert "--cache-dir" in audit_command
    assert "python -m pip_audit" in audit_command
    assert "-r requirements-dev.txt" in audit_command
