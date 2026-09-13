from __future__ import annotations

import json
import subprocess

from .project_errors import ProjectAuthError, ProjectError, ProjectTransportError

GITHUB_GRAPHQL_TIMEOUT_SECONDS = 60


def run_graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
    payload = json.dumps({"query": query, "variables": variables})
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "--input", "-"],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=GITHUB_GRAPHQL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        timeout = exc.timeout if exc.timeout is not None else GITHUB_GRAPHQL_TIMEOUT_SECONDS
        raise ProjectTransportError(f"Timed out running GitHub GraphQL request after {timeout} seconds.") from exc
    except OSError as exc:
        raise ProjectTransportError(f"Could not run GitHub GraphQL request: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        if is_project_scope_error(message):
            raise ProjectAuthError(message or "GitHub Project access requires the project scope.")
        if is_project_transport_error(message):
            raise ProjectTransportError(message or "GitHub GraphQL transport failed.")
        raise ProjectError(message or "GitHub GraphQL request failed.")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProjectError("GitHub GraphQL returned invalid JSON.") from exc
    if data.get("errors"):
        message = "; ".join(str(error.get("message", error)) for error in data["errors"])
        if is_project_scope_error(message):
            raise ProjectAuthError(message)
        if is_project_transport_error(message):
            raise ProjectTransportError(message)
        raise ProjectError(message)
    return data


def is_project_scope_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "project" in lowered
        and ("scope" in lowered or "resource not accessible" in lowered or "forbidden" in lowered)
    ) or "projectv2" in lowered and "not accessible" in lowered


def is_project_transport_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in (
            "rate limit",
            "secondary rate limit",
            "abuse detection",
            "retry-after",
            "x-ratelimit-reset",
            "unknown owner type",
            "could not resolve host",
            "connection reset",
            "connection refused",
            "timed out",
            "timeout",
            "502 bad gateway",
            "503 service unavailable",
            "504 gateway timeout",
            "http 5",
        )
    )
