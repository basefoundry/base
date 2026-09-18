from __future__ import annotations


PROJECT_TRANSPORT_ERROR_MARKERS = (
    "rate limit",
    "secondary rate limit",
    "abuse detection",
    "retry-after",
    "x-ratelimit-reset",
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

GRAPHQL_ONLY_TRANSPORT_ERROR_MARKERS = ("unknown owner type",)


def is_project_transport_error(message: str, *, extra_markers: tuple[str, ...] = ()) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered for marker in (*PROJECT_TRANSPORT_ERROR_MARKERS, *extra_markers)
    )
