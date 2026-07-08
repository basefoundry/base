from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import process
from .checks import ArtifactCheck
from .git_commands import run_git
from .git_remote_parse import GITHUB_HOST
from .git_remote_parse import SCP_REMOTE_RE
from .git_remote_parse import RemoteInfo
from .git_remote_parse import github_repository
from .git_remote_parse import malformed_remote
from .git_remote_parse import origin_remote_message
from .git_remote_parse import parse_local_remote
from .git_remote_parse import parse_origin_remote
from .git_remote_parse import parse_scp_remote
from .git_remote_parse import parse_url_remote
from .git_remote_parse import remote_details
from .manifest import BaseManifest


GITHUB_CLI_LINUX_INSTALL_URL = "https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian"
REMOTE_REACHABILITY_TIMEOUT_SECONDS = 5

# Compatibility exports for callers that imported remote parsing helpers from
# this diagnostics module before git_remote_parse existed.
__all__ = (
    "GITHUB_CLI_LINUX_INSTALL_URL",
    "GITHUB_HOST",
    "REMOTE_REACHABILITY_TIMEOUT_SECONDS",
    "RemoteInfo",
    "SCP_REMOTE_RE",
    "check_git_remote",
    "check_git_repository",
    "check_github_cli_auth",
    "check_origin_reachability",
    "check_origin_remote",
    "github_repository",
    "malformed_remote",
    "origin_remote_message",
    "parse_local_remote",
    "parse_origin_remote",
    "parse_scp_remote",
    "parse_url_remote",
    "reachability_failure_category",
    "remote_details",
    "run_git",
)


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
        fix = "Install GitHub CLI or run 'basectl setup --profile dev'."
        if os.environ.get("BASE_PLATFORM") == "linux-debian":
            fix = (
                "Install GitHub CLI from GitHub CLI's official Debian/Ubuntu apt repository: "
                f"{GITHUB_CLI_LINUX_INSTALL_URL}."
            )
        return ArtifactCheck(
            name="github_cli_auth",
            ok=False,
            message="GitHub CLI 'gh' was not found; GitHub authentication for origin was not checked.",
            fix=fix,
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
