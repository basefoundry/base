from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from base_setup.git_remote_parse import parse_origin_remote

from .release_bom import ReleaseBomError, canonical_bom_bytes, load_bom, validate_bom
from .release_model import ReleaseContext, ReleaseError, ReleaseFinding

CHANGELOG_HEADER_RE = re.compile(r"^##\s+(?:\[(?P<bracket>[^\]]+)\]|(?P<plain>\S+))(?:\s+-.*)?$")
GIT_INSPECTION_TIMEOUT_SECONDS = 10
FULL_GIT_SHA_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")


@dataclass(frozen=True)
class ReleaseProvenanceInspection:
    findings: tuple[ReleaseFinding, ...]
    commit_sha: str | None = None


def release_findings(
    ctx: ReleaseContext,
    *,
    gh_cli_finding_func: Callable[[], ReleaseFinding] | None = None,
) -> tuple[ReleaseFinding, ...]:
    gh_check = gh_cli_finding_func or gh_cli_finding
    provenance = inspect_release_provenance(ctx)
    findings: list[ReleaseFinding] = [
        ReleaseFinding("ok", "manifest", f"Release metadata found in {ctx.manifest_path}."),
        version_file_finding(ctx),
        changelog_finding(ctx),
        git_worktree_finding(ctx.manifest_path.parent),
        *provenance.findings,
        bom_finding(ctx, provenance.commit_sha),
        gh_check(),
        local_tag_finding(ctx.manifest_path.parent, ctx.tag_name),
        remote_tag_finding(ctx.manifest_path.parent, ctx.tag_name),
    ]
    return tuple(findings)


def bom_finding(ctx: ReleaseContext, reviewed_commit: str | None) -> ReleaseFinding:
    if ctx.bom_path is None:
        if ctx.release.bom is not None and ctx.release.bom.required:
            return ReleaseFinding(
                "error",
                "bom",
                "Release BOM is required by release.bom.required; pass --bom <path>.",
            )
        return ReleaseFinding("ok", "bom", "No release BOM was requested for this check.")
    if not ctx.bom_path.is_file():
        return ReleaseFinding("error", "bom", f"Release BOM is missing: {ctx.bom_path}")
    try:
        document = load_bom(ctx.bom_path)
        if canonical_bom_bytes(document) != ctx.bom_path.read_bytes():
            raise ReleaseBomError(
                "Release BOM is not in canonical form; regenerate it with bin/base-release-bom assemble."
            )
        validate_bom(
            document,
            expected_repository=ctx.release.github.repository,
            expected_version=ctx.version,
            expected_commit=reviewed_commit,
        )
    except ReleaseBomError as exc:
        return ReleaseFinding("error", "bom", str(exc))
    return ReleaseFinding("ok", "bom", f"Release BOM is valid: {ctx.bom_path}.")


def inspect_release_provenance(ctx: ReleaseContext) -> ReleaseProvenanceInspection:
    root = ctx.manifest_path.parent
    origin_finding = origin_repository_finding(root, ctx.release.github.repository)
    if origin_finding.status != "ok":
        return ReleaseProvenanceInspection(
            findings=(
                origin_finding,
                ReleaseFinding(
                    "error",
                    "default_branch",
                    "Unable to verify the remote default branch until origin matches the configured repository.",
                ),
                ReleaseFinding(
                    "error",
                    "release_commit",
                    "Unable to verify the release commit until origin matches the configured repository.",
                ),
            )
        )

    remote_default, remote_error = remote_default_branch(root)
    current_branch = current_git_branch(root)
    local_head = current_git_head(root)
    if remote_default is None:
        detail = remote_error or "the remote did not advertise a symbolic default branch and full commit SHA"
        return ReleaseProvenanceInspection(
            findings=(
                origin_finding,
                ReleaseFinding(
                    "error",
                    "default_branch",
                    f"Unable to resolve origin's current default branch: {detail}. "
                    "Confirm origin is reachable and its default branch is configured, then retry.",
                ),
                ReleaseFinding(
                    "error",
                    "release_commit",
                    "Unable to compare local HEAD with the current remote default-branch commit.",
                ),
            )
        )

    default_branch, remote_head = remote_default
    branch_finding = release_default_branch_finding(current_branch, default_branch)
    commit_finding = release_commit_finding(local_head, default_branch, remote_head)
    commit_sha = remote_head if branch_finding.status == "ok" and commit_finding.status == "ok" else None
    return ReleaseProvenanceInspection(
        findings=(origin_finding, branch_finding, commit_finding),
        commit_sha=commit_sha,
    )


def require_release_provenance(ctx: ReleaseContext) -> str:
    inspection = inspect_release_provenance(ctx)
    if inspection.commit_sha is not None and all(finding.status == "ok" for finding in inspection.findings):
        return inspection.commit_sha
    detail = "; ".join(finding.message for finding in inspection.findings if finding.status != "ok")
    raise ReleaseError(f"Release provenance changed or could not be verified before tagging: {detail}")


def origin_repository_finding(root: Path, configured_repository: str) -> ReleaseFinding:
    fetch_urls = git_remote_urls(root, push=False)
    push_urls = git_remote_urls(root, push=True)
    if fetch_urls is None or push_urls is None or not fetch_urls or not push_urls:
        return ReleaseFinding(
            "error",
            "origin_repository",
            "Unable to resolve every origin fetch and push URL. Configure origin for the release repository and retry.",
        )

    configured = configured_repository.casefold()
    for remote_url in (*fetch_urls, *push_urls):
        remote = parse_origin_remote(remote_url, root)
        if not remote.valid or remote.provider != "github" or not remote.repository:
            return ReleaseFinding(
                "error",
                "origin_repository",
                f"Origin must use the configured GitHub repository '{configured_repository}' for fetch and push. "
                "Update origin and retry.",
            )
        if remote.repository.casefold() != configured:
            return ReleaseFinding(
                "error",
                "origin_repository",
                f"Origin resolves to GitHub repository '{remote.repository}', but release.github.repository is "
                f"'{configured_repository}'. Update origin or the manifest before publishing.",
            )

    return ReleaseFinding(
        "ok",
        "origin_repository",
        f"Every origin fetch and push URL matches GitHub repository '{configured_repository}'.",
    )


def git_remote_urls(root: Path, *, push: bool) -> tuple[str, ...] | None:
    command = ["git", "remote", "get-url", "--all"]
    if push:
        command.append("--push")
    command.append("origin")
    try:
        result = subprocess.run(
            command,
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
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def remote_default_branch(root: Path) -> tuple[tuple[str, str] | None, str | None]:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", "origin", "HEAD"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, "the remote inspection timed out"
    except OSError:
        return None, "Git could not inspect origin"
    if result.returncode != 0:
        return None, "Git could not read origin HEAD"
    return parse_remote_default_branch(result.stdout)


def parse_remote_default_branch(output: str) -> tuple[tuple[str, str] | None, str | None]:
    branch: str | None = None
    commit_sha: str | None = None
    for line in output.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            branch = line.removeprefix("ref: refs/heads/").removesuffix("\tHEAD")
            continue
        value, separator, ref_name = line.partition("\t")
        if separator and ref_name == "HEAD" and FULL_GIT_SHA_RE.fullmatch(value):
            commit_sha = value.lower()
    if not branch:
        return None, "origin did not advertise HEAD as a branch"
    if not commit_sha:
        return None, "origin did not advertise HEAD as a full commit SHA"
    return (branch, commit_sha), None


def current_git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip().lower()
    if result.returncode != 0 or not FULL_GIT_SHA_RE.fullmatch(value):
        return None
    return value


def release_default_branch_finding(current_branch: str | None, default_branch: str) -> ReleaseFinding:
    if current_branch is None:
        return ReleaseFinding(
            "error",
            "default_branch",
            "Unable to inspect the current Git branch. Check out the remote default branch and retry.",
        )
    if not current_branch:
        return ReleaseFinding(
            "error",
            "default_branch",
            f"Git HEAD is detached. Check out origin's default branch '{default_branch}' and retry.",
        )
    if current_branch != default_branch:
        return ReleaseFinding(
            "error",
            "default_branch",
            f"Current branch '{current_branch}' is not origin's default branch '{default_branch}'. "
            f"Merge the reviewed release PR, check out '{default_branch}', synchronize it, and retry.",
        )
    return ReleaseFinding(
        "ok",
        "default_branch",
        f"Current branch '{current_branch}' matches origin's default branch.",
    )


def release_commit_finding(local_head: str | None, default_branch: str, remote_head: str) -> ReleaseFinding:
    if local_head is None:
        return ReleaseFinding(
            "error",
            "release_commit",
            "Unable to resolve local HEAD to a full commit SHA. Repair the checkout and retry.",
        )
    if local_head != remote_head:
        return ReleaseFinding(
            "error",
            "release_commit",
            f"Local HEAD {local_head} does not match current origin/{default_branch} {remote_head}. "
            "Fetch origin, reconcile any behind, ahead, or diverged commits, and retry from the synchronized branch.",
        )
    return ReleaseFinding(
        "ok",
        "release_commit",
        f"Local HEAD and origin/{default_branch} resolve to reviewed commit {local_head}.",
    )


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
