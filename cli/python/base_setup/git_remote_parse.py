from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse
from urllib.parse import urlunparse

GITHUB_HOST = "github.com"
SCP_REMOTE_RE = re.compile(r"^(?:(?P<user>[^@\s]+)@)?(?P<host>[^:\s/]+):(?P<path>.+)$")


@dataclass(frozen=True)
class RemoteInfo:
    valid: bool
    provider: str
    transport: str
    sanitized_url: str
    host: str = ""
    repository: str = ""
    local_path: Path | None = None
    reachable: bool | None = None
    error: str = ""


def parse_origin_remote(remote_url: str, project_root: Path) -> RemoteInfo:
    remote_url = remote_url.strip()
    if not remote_url:
        return malformed_remote("Origin remote URL is empty.")

    if "://" in remote_url:
        return parse_url_remote(remote_url)

    scp_match = SCP_REMOTE_RE.match(remote_url)
    if scp_match and not remote_url.startswith(("/", "./", "../", "~")):
        return parse_scp_remote(scp_match)

    return parse_local_remote(remote_url, project_root)


def parse_url_remote(remote_url: str) -> RemoteInfo:
    parsed = urlparse(remote_url)
    scheme = parsed.scheme.lower()
    if not scheme:
        return malformed_remote("Remote URL is missing a scheme.")

    if scheme == "file":
        path = unquote(parsed.path)
        if not path:
            return malformed_remote("file remote is missing a path.")
        local_path = Path(path)
        return RemoteInfo(
            valid=True,
            provider="local",
            transport="file",
            sanitized_url=urlunparse(("file", "", parsed.path, "", "", "")),
            local_path=local_path,
            reachable=local_path.exists(),
        )

    host = (parsed.hostname or "").lower()
    if not host or not parsed.path or parsed.path == "/":
        return malformed_remote("Remote URL is missing a host or repository path.")

    sanitized_netloc = host
    if parsed.port is not None:
        sanitized_netloc = f"{sanitized_netloc}:{parsed.port}"
    sanitized_url = urlunparse((scheme, sanitized_netloc, parsed.path, "", "", ""))
    provider = "github" if host == GITHUB_HOST else "other"
    repository = ""
    error = ""
    valid = True
    if provider == "github":
        repository = github_repository(parsed.path)
        if not repository:
            valid = False
            error = "GitHub remote must include owner and repository."

    return RemoteInfo(
        valid=valid,
        provider=provider,
        transport=scheme,
        sanitized_url=sanitized_url,
        host=host,
        repository=repository,
        error=error,
    )


def parse_scp_remote(match: re.Match[str]) -> RemoteInfo:
    host = match.group("host").lower()
    path = match.group("path").strip()
    if not host or not path:
        return malformed_remote("SSH remote is missing a host or repository path.")

    sanitized_url = f"{host}:{path}"
    provider = "github" if host == GITHUB_HOST else "other"
    repository = ""
    error = ""
    valid = True
    if provider == "github":
        repository = github_repository(path)
        if not repository:
            valid = False
            error = "GitHub remote must include owner and repository."

    return RemoteInfo(
        valid=valid,
        provider=provider,
        transport="ssh",
        sanitized_url=sanitized_url,
        host=host,
        repository=repository,
        error=error,
    )


def parse_local_remote(remote_url: str, project_root: Path) -> RemoteInfo:
    local_path = Path(remote_url).expanduser()
    resolved_path = local_path if local_path.is_absolute() else (project_root / local_path).resolve()
    return RemoteInfo(
        valid=True,
        provider="local",
        transport="local_path",
        sanitized_url=remote_url,
        local_path=resolved_path,
        reachable=resolved_path.exists(),
    )


def malformed_remote(error: str) -> RemoteInfo:
    return RemoteInfo(
        valid=False,
        provider="unknown",
        transport="unknown",
        sanitized_url="",
        error=error,
    )


def github_repository(path: str) -> str:
    normalized = path.strip("/")
    if normalized.endswith(".git"):
        normalized = normalized.removesuffix(".git")
    parts = normalized.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return ""
    return f"{parts[0]}/{parts[1]}"


def origin_remote_message(remote_info: RemoteInfo) -> str:
    if remote_info.provider == "github":
        return (
            "Project Git origin remote points to GitHub repository "
            f"'{remote_info.repository}' over {remote_info.transport}."
        )
    if remote_info.provider == "local":
        return f"Project Git origin remote points to local repository path '{remote_info.sanitized_url}'."
    if remote_info.host:
        return f"Project Git origin remote points to host '{remote_info.host}' over {remote_info.transport}."
    return "Project Git origin remote is configured."


def remote_details(remote_info: RemoteInfo) -> dict[str, object]:
    details: dict[str, object] = {
        "remote": "origin",
        "provider": remote_info.provider,
        "transport": remote_info.transport,
        "network_checked": False,
    }
    if remote_info.sanitized_url:
        details["sanitized_url"] = remote_info.sanitized_url
    if remote_info.host:
        details["host"] = remote_info.host
    if remote_info.repository:
        details["repository"] = remote_info.repository
    if remote_info.reachable is not None:
        details["reachable"] = remote_info.reachable
    if remote_info.error:
        details["error"] = remote_info.error
    return details

