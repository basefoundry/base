from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from .release_model import ReleaseContext, ReleaseError, ReleaseFinding

CHANGELOG_HEADER_RE = re.compile(r"^##\s+(?:\[(?P<bracket>[^\]]+)\]|(?P<plain>\S+))(?:\s+-.*)?$")
GIT_INSPECTION_TIMEOUT_SECONDS = 10


def release_findings(
    ctx: ReleaseContext,
    *,
    gh_cli_finding_func: Callable[[], ReleaseFinding] | None = None,
) -> tuple[ReleaseFinding, ...]:
    gh_check = gh_cli_finding_func or gh_cli_finding
    findings: list[ReleaseFinding] = [
        ReleaseFinding("ok", "manifest", f"Release metadata found in {ctx.manifest_path}."),
        version_file_finding(ctx),
        changelog_finding(ctx),
        git_worktree_finding(ctx.manifest_path.parent),
        git_branch_finding(ctx.manifest_path.parent),
        gh_check(),
        local_tag_finding(ctx.manifest_path.parent, ctx.tag_name),
        remote_tag_finding(ctx.manifest_path.parent, ctx.tag_name),
    ]
    return tuple(findings)


def version_file_finding(ctx: ReleaseContext) -> ReleaseFinding:
    version = read_version_file(ctx.version_file)
    if version is None:
        return ReleaseFinding("error", "version_file", f"{ctx.release.version_file} is missing or empty.")
    if version != ctx.version:
        return ReleaseFinding(
            "error",
            "version_file",
            f"{ctx.release.version_file} contains {version}, expected {ctx.version}.",
        )
    return ReleaseFinding("ok", "version_file", f"{ctx.release.version_file} matches {ctx.version}.")


def changelog_finding(ctx: ReleaseContext) -> ReleaseFinding:
    try:
        extract_changelog_section(ctx.changelog, ctx.version)
    except ReleaseError as exc:
        return ReleaseFinding("error", "changelog", str(exc))
    return ReleaseFinding("ok", "changelog", f"{ctx.release.changelog} has a section for {ctx.version}.")


def git_worktree_finding(root: Path) -> ReleaseFinding:
    status = git_status(root)
    if status is None:
        return ReleaseFinding("warn", "git", "Unable to inspect Git worktree status.")
    if status:
        return ReleaseFinding("error", "git", "Git worktree has tracked or untracked changes.")
    return ReleaseFinding("ok", "git", "Git worktree is clean.")


def git_branch_finding(root: Path) -> ReleaseFinding:
    branch = current_git_branch(root)
    if branch is None:
        return ReleaseFinding("warn", "branch", "Unable to inspect current Git branch.")
    if not branch:
        return ReleaseFinding("warn", "branch", "Git worktree is detached from a branch.")
    return ReleaseFinding("ok", "branch", f"Current branch is {branch}.")


def local_tag_finding(root: Path, tag_name: str) -> ReleaseFinding:
    exists = local_tag_exists(root, tag_name)
    if exists is None:
        return ReleaseFinding("warn", "local_tag", f"Unable to inspect local tag {tag_name}.")
    if exists:
        return ReleaseFinding("error", "local_tag", f"Local tag {tag_name} already exists.")
    return ReleaseFinding("ok", "local_tag", f"Local tag {tag_name} is available.")


def read_version_file(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if value:
                return value
    except OSError:
        return None
    return None


def extract_changelog_section(path: Path, version: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ReleaseError(f"{path.name} could not be read: {exc}") from exc

    start: int | None = None
    for index, line in enumerate(lines):
        match = CHANGELOG_HEADER_RE.match(line)
        if match and version in (match.group("bracket"), match.group("plain")):
            start = index + 1
            break
    if start is None:
        raise ReleaseError(f"{path.name} has no section for {version}.")

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    section_lines = lines[start:end]
    while section_lines and not section_lines[0].strip():
        section_lines.pop(0)
    while section_lines and not section_lines[-1].strip():
        section_lines.pop()
    if not section_lines:
        raise ReleaseError(f"{path.name} section for {version} is empty.")
    return "\n".join(section_lines)


def git_status(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_git_branch(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def gh_cli_finding() -> ReleaseFinding:
    if shutil.which("gh") is None:
        return ReleaseFinding("error", "gh", "GitHub CLI 'gh' was not found.")

    try:
        result = subprocess.run(
            ["gh", "auth", "status", "-h", "github.com"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ReleaseFinding("error", "gh", f"Unable to run GitHub CLI auth check: {exc}.")
    if result.returncode == 0:
        return ReleaseFinding("ok", "gh", "GitHub CLI is authenticated for github.com.")

    detail = last_non_empty_line(result.stdout)
    if detail:
        return ReleaseFinding("error", "gh", f"GitHub CLI auth check failed: {detail}")
    return ReleaseFinding("error", "gh", "GitHub CLI is not authenticated for github.com.")


def github_release_finding(ctx: ReleaseContext) -> ReleaseFinding:
    try:
        result = subprocess.run(
            ["gh", "release", "view", ctx.tag_name, "--repo", ctx.release.github.repository],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ReleaseFinding("error", "github_release", f"Unable to inspect GitHub Release {ctx.tag_name}: {exc}.")

    if result.returncode == 0:
        return ReleaseFinding("error", "github_release", f"GitHub Release {ctx.tag_name} already exists.")

    detail = result.stdout.lower()
    if "release not found" in detail or "could not resolve to a release" in detail:
        return ReleaseFinding("ok", "github_release", f"GitHub Release {ctx.tag_name} is available.")

    error_detail = last_non_empty_line(result.stdout)
    if error_detail:
        return ReleaseFinding(
            "error",
            "github_release",
            f"Unable to inspect GitHub Release {ctx.tag_name}: {error_detail}",
        )
    return ReleaseFinding("error", "github_release", f"Unable to inspect GitHub Release {ctx.tag_name}.")


def local_tag_exists(root: Path, tag_name: str) -> bool | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag_name}"],
            cwd=root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode == 0


def remote_tag_finding(root: Path, tag_name: str) -> ReleaseFinding:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag_name}"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ReleaseFinding("error", "remote_tag", f"Unable to inspect remote tag {tag_name} on origin: {exc}.")

    if result.returncode != 0:
        detail = last_non_empty_line(result.stderr)
        if detail:
            return ReleaseFinding("error", "remote_tag", f"Unable to inspect remote tag {tag_name} on origin: {detail}")
        return ReleaseFinding("error", "remote_tag", f"Unable to inspect remote tag {tag_name} on origin.")
    if result.stdout.strip():
        return ReleaseFinding("error", "remote_tag", f"Remote tag {tag_name} already exists on origin.")
    return ReleaseFinding("ok", "remote_tag", f"Remote tag {tag_name} is available on origin.")


def last_non_empty_line(value: str) -> str | None:
    for line in reversed(value.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return None
