from __future__ import annotations

import json
import subprocess
from typing import Any

from .project_errors import ProjectAuthError, ProjectError, ProjectTransportError


ISSUE_FIELDS_API_VERSION = "2026-03-10"
ISSUE_FIELDS_API_HEADER = f"X-GitHub-Api-Version: {ISSUE_FIELDS_API_VERSION}"
ISSUE_FIELDS_API_TIMEOUT_SECONDS = 60


def run_issue_fields_api(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    """Call an issue-field REST endpoint with Base's pinned API version."""
    command = ["gh", "api", "-H", ISSUE_FIELDS_API_HEADER]
    if method != "GET":
        command.extend(["--method", method])
    command.append(path)
    input_payload = None
    if payload is not None:
        command.extend(["--input", "-"])
        input_payload = json.dumps(payload)
    try:
        result = subprocess.run(
            command,
            input=input_payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=ISSUE_FIELDS_API_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        timeout = exc.timeout if exc.timeout is not None else ISSUE_FIELDS_API_TIMEOUT_SECONDS
        raise ProjectTransportError(f"Timed out running issue-field REST request after {timeout} seconds.") from exc
    except OSError as exc:
        raise ProjectTransportError(f"Could not run issue-field REST request: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        lowered = message.lower()
        if any(marker in lowered for marker in ("bad credentials", "401 unauthorized", "requires authentication")):
            raise ProjectAuthError(message or "GitHub issue-field access requires authentication.")
        raise ProjectError(message or "GitHub issue-field REST request failed.")
    output = result.stdout.strip()
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise ProjectError("GitHub issue-field REST returned invalid JSON.") from exc


def issue_field_value_map(payload: Any) -> dict[str, str]:
    """Normalize the REST issue-field-value response to field-name/value pairs."""
    if isinstance(payload, dict):
        values = payload.get("issue_field_values", [])
    else:
        values = payload
    if not isinstance(values, list):
        raise ProjectError("GitHub returned an invalid issue-field-values response.")
    result: dict[str, str] = {}
    for item in values:
        if not isinstance(item, dict):
            continue
        field_name = item.get("issue_field_name") or item.get("field_name")
        value = (item.get("single_select_option") or {}).get("name")
        if value is None:
            value = item.get("value")
        if field_name and value is not None:
            result[str(field_name)] = str(value)
    return result


def organization_issue_field_ids(owner: str) -> dict[str, int]:
    payload = run_issue_fields_api(f"orgs/{owner}/issue-fields?per_page=100")
    if not isinstance(payload, list):
        raise ProjectError(f"GitHub returned an invalid issue-field list for organization '{owner}'.")
    fields: dict[str, int] = {}
    for item in payload:
        if isinstance(item, dict) and item.get("name") and item.get("id") is not None:
            fields[str(item["name"])] = int(item["id"])
    return fields


def write_issue_field_values(
    owner: str,
    repository: str,
    issue_number: int,
    values: dict[str, str],
    *,
    field_ids: dict[str, int] | None = None,
) -> None:
    if not values:
        return
    ids = field_ids if field_ids is not None else organization_issue_field_ids(owner)
    missing = sorted(set(values) - set(ids))
    if missing:
        raise ProjectError("Organization issue field(s) not found: " + ", ".join(missing) + ".")
    payload = {
        "issue_field_values": [
            {"field_id": ids[name], "value": value}
            for name, value in sorted(values.items())
        ]
    }
    run_issue_fields_api(
        f"repos/{repository}/issues/{issue_number}/issue-field-values",
        method="POST",
        payload=payload,
    )


def read_issue_field_values(owner: str, repo: str, issue_number: int) -> dict[str, str]:
    payload = run_issue_fields_api(f"repos/{owner}/{repo}/issues/{issue_number}/issue-field-values")
    return issue_field_value_map(payload)
