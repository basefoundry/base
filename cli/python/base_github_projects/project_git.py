from __future__ import annotations

import subprocess

from base_projects.command_helpers import ProjectUsageError, github_repo_spec

GIT_COMMAND_TIMEOUT_SECONDS = 10


def require_owner(args: object) -> str:
    owner = getattr(args, "owner")
    repo = getattr(args, "repo")
    if not owner and repo:
        owner = repo.split("/", 1)[0]
    if not owner:
        owner = infer_owner_from_git()
    if not owner:
        raise ProjectUsageError("Project owner is required. Pass --owner <login>.")
    return owner


def require_repo(args: object) -> str:
    repo = getattr(args, "repo") or infer_repo_from_git()
    if not repo:
        raise ProjectUsageError("Repository is required. Pass --repo <owner/name>.")
    return repo


def split_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ProjectUsageError(f"Repository must be in owner/name form, got '{repo}'.")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise ProjectUsageError(f"Repository must be in owner/name form, got '{repo}'.")
    return owner, name


def infer_owner_from_git() -> str | None:
    repo = infer_repo_from_git()
    return repo.split("/", 1)[0] if repo else None


def infer_repo_from_git() -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            capture_output=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return github_repo_spec(result.stdout)
