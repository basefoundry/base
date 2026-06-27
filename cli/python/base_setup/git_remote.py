from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlunparse
from urllib.parse import urlparse

from . import process
from .checks import ArtifactCheck
from .manifest import BaseManifest


GITHUB_HOST = "github.com"
REMOTE_REACHABILITY_TIMEOUT_SECONDS = 5
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


def check_git_remote(manifest: BaseManifest, check_network: bool = False) -> tuple[ArtifactCheck, ...]:
    if not manifest.path.is_absolute() or not manifest.path.is_file():
        return ()

    project_root = manifest.path.parent.resolve()
    repository_check, _git_root = check_git_repository(project_root)
    checks = [repository_check]
    if not repository_check.ok:
        if repository_check.details.get("inside_work_tree") is False:
            return ()
        return tuple(checks)

    origin_check, remote_info = check_origin_remote(project_root)
    checks.append(origin_check)
    if not origin_check.ok or remote_info is None:
        return tuple(checks)

    if check_network:
        checks.append(check_origin_reachability(project_root, remote_info))

    if remote_info.provider == "github":
        checks.append(check_github_cli_auth(remote_info))
    return tuple(checks)


def check_git_repository(project_root: Path) -> tuple[ArtifactCheck, Path | None]:
    if not process.command_exists("git"):
        return (
            ArtifactCheck(
                name="git_repository",
                ok=False,
                message="Git was not found, so project repository diagnostics could not run.",
                fix="Install Git or Xcode Command Line Tools.",
                finding_id="BASE-P080",
                details={"project_root": str(project_root), "git_available": False},
            ),
            None,
        )

    inside = run_git(project_root, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return (
            ArtifactCheck(
                name="git_repository",
                ok=False,
                message=f"Project directory '{project_root}' is not inside a Git repository.",
                fix="Clone the project repository or initialize Git before using project Git remote workflows.",
                finding_id="BASE-P080",
                details={
                    "project_root": str(project_root),
                    "git_available": True,
                    "inside_work_tree": False,
                },
            ),
            None,
        )

    top_level = run_git(project_root, ["rev-parse", "--show-toplevel"])
    git_root = Path(top_level.stdout.strip()).resolve() if top_level.returncode == 0 else project_root
    return (
        ArtifactCheck(
            name="git_repository",
            ok=True,
            message=f"Project is inside a Git repository at '{git_root}'.",
            fix="",
            finding_id="BASE-P080",
            details={
                "project_root": str(project_root),
                "git_root": str(git_root),
                "git_available": True,
                "inside_work_tree": True,
            },
        ),
        git_root,
    )


def check_origin_remote(project_root: Path) -> tuple[ArtifactCheck, RemoteInfo | None]:
    completed = run_git(project_root, ["remote", "get-url", "origin"])
    if completed.returncode != 0:
        return (
            ArtifactCheck(
                name="git_origin_remote",
                ok=False,
                message="Project Git repository does not have an 'origin' remote.",
                fix="Add an origin remote with Git, for example: git remote add origin <url>",
                finding_id="BASE-P081",
                details={
                    "remote": "origin",
                    "present": False,
                    "network_checked": False,
                },
            ),
            None,
        )

    remote_url = completed.stdout.strip()
    remote_info = parse_origin_remote(remote_url, project_root)
    if not remote_info.valid:
        return (
            ArtifactCheck(
                name="git_origin_remote",
                ok=False,
                message=f"Project Git origin remote is malformed: {remote_info.error}",
                fix="Update origin with a valid Git remote URL.",
                finding_id="BASE-P081",
                details=remote_details(remote_info),
            ),
            remote_info,
        )

    if remote_info.provider == "local" and remote_info.reachable is False:
        return (
            ArtifactCheck(
                name="git_origin_remote",
                ok=False,
                message=f"Project Git origin remote path does not exist: {remote_info.sanitized_url}",
                fix="Update origin to an existing local repository path.",
                finding_id="BASE-P081",
                details=remote_details(remote_info),
            ),
            remote_info,
        )

    return (
        ArtifactCheck(
            name="git_origin_remote",
            ok=True,
            message=origin_remote_message(remote_info),
            fix="",
            finding_id="BASE-P081",
            details=remote_details(remote_info),
        ),
        remote_info,
    )


def check_github_cli_auth(remote_info: RemoteInfo) -> ArtifactCheck:
    details = {
        "remote": "origin",
        "provider": "github",
        "host": remote_info.host,
        "repository": remote_info.repository,
        "gh_auth_checked": True,
    }
    if not process.command_exists("gh"):
        return ArtifactCheck(
            name="github_cli_auth",
            ok=False,
            message="GitHub CLI 'gh' was not found; GitHub authentication for origin was not checked.",
            fix="Install GitHub CLI or run 'basectl setup --profile dev'.",
            finding_id="BASE-P082",
            status="warn",
            details=details | {"gh_available": False},
        )

    try:
        authenticated = process.run_check(
            ["gh", "auth", "status", "-h", GITHUB_HOST],
            timeout_seconds=REMOTE_REACHABILITY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ArtifactCheck(
            name="github_cli_auth",
            ok=False,
            message=(
                "GitHub CLI authentication check timed out after "
                f"{REMOTE_REACHABILITY_TIMEOUT_SECONDS} seconds."
            ),
            fix="Check network access and GitHub CLI authentication, then retry the Base check.",
            finding_id="BASE-P082",
            status="warn",
            details=details | {"gh_available": True, "authenticated": False, "failure_category": "timeout"},
        )

    if authenticated:
        return ArtifactCheck(
            name="github_cli_auth",
            ok=True,
            message="GitHub CLI authentication is ready for github.com.",
            fix="",
            finding_id="BASE-P082",
            details=details | {"gh_available": True, "authenticated": True},
        )

    return ArtifactCheck(
        name="github_cli_auth",
        ok=False,
        message="GitHub CLI authentication is not ready for github.com.",
        fix="gh auth login -h github.com",
        finding_id="BASE-P082",
        status="warn",
        details=details | {"gh_available": True, "authenticated": False},
    )


def check_origin_reachability(project_root: Path, remote_info: RemoteInfo) -> ArtifactCheck:
    details = remote_details(remote_info) | {
        "network_checked": True,
        "remote": "origin",
    }
    try:
        completed = run_git(
            project_root,
            ["ls-remote", "--exit-code", "origin", "HEAD"],
            timeout_seconds=REMOTE_REACHABILITY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ArtifactCheck(
            name="git_origin_reachability",
            ok=False,
            message=(
                "Project Git origin remote reachability check timed out after "
                f"{REMOTE_REACHABILITY_TIMEOUT_SECONDS} seconds."
            ),
            fix="Check network access and Git credentials, then rerun with '--remote-network'.",
            finding_id="BASE-P083",
            status="warn",
            details=details | {"reachable": False, "failure_category": "timeout"},
        )

    if completed.returncode == 0:
        return ArtifactCheck(
            name="git_origin_reachability",
            ok=True,
            message="Project Git origin remote is reachable.",
            fix="",
            finding_id="BASE-P083",
            details=details | {"reachable": True},
        )

    return ArtifactCheck(
        name="git_origin_reachability",
        ok=False,
        message="Project Git origin remote could not be reached with 'git ls-remote'.",
        fix="Check network access and Git credentials, then rerun with '--remote-network'.",
        finding_id="BASE-P083",
        status="warn",
        details=details
        | {
            "reachable": False,
            "failure_category": reachability_failure_category(completed.stderr),
        },
    )


def reachability_failure_category(stderr: str | None) -> str:
    message = (stderr or "").lower()
    if "auth" in message or "permission denied" in message:
        return "authentication"
    return "unreachable"


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


def run_git(
    project_root: Path,
    arguments: list[str],
    timeout_seconds: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
