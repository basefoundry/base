from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal
from urllib.parse import quote

import base_cli
from base_setup import process

from .release_bom import ReleaseBomError, read_validated_bom
from .release_model import ReleaseContext, ReleaseError
from .release_readiness import last_non_empty_line

RELEASE_STEP_TIMEOUT_SECONDS = 120
RELEASE_API_RETRY_DELAYS_SECONDS = (1, 2)
FULL_GIT_SHA_LENGTHS = frozenset((40, 64))
RELEASE_BOM_ASSET_NAME = "release-bom.json"
RELEASE_BOM_DIGEST_ASSET_NAME = "release-bom.sha256"
RemoteTagState = Literal["absent", "intended", "conflict", "unavailable"]
GithubReleaseState = Literal["absent", "draft", "published", "unavailable"]


@dataclass(frozen=True)
class GithubReleaseRecord:
    release_id: int
    tag_name: str
    name: str
    body: str
    draft: bool
    prerelease: bool
    target_commitish: str
    immutable: bool | None


def release_publish_recovery_guidance(ctx: ReleaseContext, _title: str) -> str:
    display_command = base_cli.delegated_display_command("basectl release") or "basectl release"
    bom_guidance = ""
    if ctx.bom_path is not None or (ctx.release.bom is not None and ctx.release.bom.required):
        bom_guidance = (
            "A governed release is NOT complete without release-bom.json and release-bom.sha256.\n"
            "Recover the original reviewed canonical BOM and matching digest sidecar; do not regenerate "
            "evidence from a different checkout. Validate the BOM against the intended repository, version, "
            "and commit, and verify its SHA-256 before uploading the pair under those stable asset names.\n"
            "If the GitHub draft already exists, resume it instead of creating another release. Upload missing "
            "assets without overwriting existing ones; stop if an existing asset conflicts. Download and "
            "verify both published assets against the reviewed pair before declaring success.\n"
        )
    return (
        f"Release publication for {ctx.tag_name} did not complete cleanly after the tag was pushed.\n"
        "Do not create a second release or delete the tag. Re-run the same guarded publish command; "
        "it will inspect the tag, resume an existing mutable draft, upload only missing assets, "
        "verify downloaded bytes, and publish only after the checks pass.\n"
        f"  {display_command} publish --version {shlex.quote(ctx.version)} "
        f"--manifest {shlex.quote(str(ctx.manifest_path))}"
        + (f" --bom {shlex.quote(str(ctx.bom_path))}" if ctx.bom_path is not None else "")
        + " --yes\n"
        f"{bom_guidance}"
        "If the guarded command cannot resume the draft, inspect it by release ID and use the REST API; "
        "do not use the by-tag release endpoint for a draft:\n"
        f"  gh api repos/{ctx.release.github.repository}/releases --paginate --slurp\n"
        f"  gh api repos/{ctx.release.github.repository}/releases/<release-id>\n"
        f"  gh api repos/{ctx.release.github.repository}/releases/<release-id>/assets --paginate --slurp\n"
        "After independently verifying the reviewed asset bytes, publish the draft by release ID:\n"
        f"  gh api repos/{ctx.release.github.repository}/releases/<release-id> --method PATCH --field draft=false\n"
        "To abandon this release attempt, remove the local and remote tag after confirming no one else is using it:\n"
        f"  git tag -d {shlex.quote(ctx.tag_name)}\n"
        f"  git push origin :refs/tags/{shlex.quote(ctx.tag_name)}"
    )


def release_tag_push_recovery_guidance(ctx: ReleaseContext, title: str, state: RemoteTagState) -> str:
    """Describe non-destructive recovery after local tag creation and push failure."""
    tag = shlex.quote(ctx.tag_name)
    inspect_command = f"git ls-remote --tags origin refs/tags/{tag} 'refs/tags/{tag}^{{}}'"
    if state == "intended":
        return (
            f"The remote tag {ctx.tag_name} is present and resolves to the intended release commit. "
            "Do not push or delete the tag again. Complete the GitHub Release with the verified tag:\n"
            f"{release_publish_recovery_guidance(ctx, title)}"
        )
    if state == "absent":
        return (
            f"The local annotated tag {ctx.tag_name} remains, but the remote tag is absent. "
            "After resolving the push failure, retry the tag push:\n"
            f"  git push origin {tag}\n"
            "Then verify the remote annotated tag before creating the GitHub Release. "
            "If abandoning the attempt, remove only the local tag:\n"
            f"  git tag -d {tag}"
        )
    return (
        f"The local annotated tag {ctx.tag_name} remains, but the remote tag state could not be verified safely. "
        "Do not retry blindly, force-update, or delete any tag. Inspect the exact remote refs first:\n"
        f"  {inspect_command}\n"
        "If the remote tag conflicts with the intended commit, stop and resolve it with the repository owner."
    )


def require_interactive_publish_confirmation(ctx: ReleaseContext, title: str) -> None:
    if not sys.stdin.isatty():
        raise ReleaseError("release publish requires --yes when stdin is not interactive.")

    response = input(
        f"Publish {ctx.tag_name} to {ctx.release.github.repository} with title '{title}'? [y/N] "
    )
    if response.strip().lower() not in ("y", "yes"):
        raise ReleaseError("release publish cancelled.")


def run_release_step(command: list[str], *, cwd: Path | None = None) -> None:
    capture_release_step(command, cwd=cwd)


def capture_release_step(command: list[str], *, cwd: Path | None = None) -> str:
    joined = shlex.join(command)
    try:
        result = process.run_capture(
            command,
            cwd=cwd,
            stderr=subprocess.STDOUT,
            timeout_seconds=RELEASE_STEP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ReleaseError(f"Release command timed out after {exc.timeout} seconds: {joined}") from exc
    except OSError as exc:
        raise ReleaseError(f"Unable to run release command: {joined}: {exc}") from exc
    if result.returncode != 0:
        detail = last_non_empty_line(result.stdout)
        if detail:
            raise ReleaseError(f"Release command failed: {joined}: {detail}")
        raise ReleaseError(f"Release command failed: {joined}")
    return result.stdout.strip()


def is_github_rate_limit_error(error: ReleaseError) -> bool:
    detail = str(error).lower()
    return any(
        marker in detail
        for marker in (
            "rate limit",
            "secondary limit",
            "abuse detection",
            "too many requests",
            "http 429",
        )
    )


def capture_github_step(command: list[str], *, cwd: Path | None = None) -> str:
    """Run a read-only GitHub command with bounded rate-limit recovery."""
    last_error: ReleaseError | None = None
    for attempt, delay in enumerate((0, *RELEASE_API_RETRY_DELAYS_SECONDS)):
        if delay:
            time.sleep(delay)
        try:
            return capture_release_step(command, cwd=cwd)
        except ReleaseError as exc:
            last_error = exc
            if attempt == len(RELEASE_API_RETRY_DELAYS_SECONDS) or not is_github_rate_limit_error(exc):
                raise
    if last_error is not None:
        raise last_error
    raise ReleaseError("GitHub command did not execute.")


def parse_github_release_record(payload: object, *, description: str) -> GithubReleaseRecord:
    if not isinstance(payload, dict):
        raise ReleaseError(f"{description} did not return a GitHub release object.")
    release_id = payload.get("id")
    tag_name = payload.get("tag_name")
    name = payload.get("name")
    body = payload.get("body")
    draft = payload.get("draft")
    prerelease = payload.get("prerelease")
    target_commitish = payload.get("target_commitish")
    immutable = payload.get("immutable")
    complete = (
        not isinstance(release_id, bool),
        isinstance(release_id, int),
        isinstance(tag_name, str),
        isinstance(name, str),
        isinstance(body, str),
        isinstance(draft, bool),
        isinstance(prerelease, bool),
        isinstance(target_commitish, str),
        immutable is None or isinstance(immutable, bool),
    )
    if not all(complete):
        raise ReleaseError(f"{description} did not return a complete GitHub release object.")
    return GithubReleaseRecord(
        release_id=release_id,
        tag_name=tag_name,
        name=name,
        body=body,
        draft=draft,
        prerelease=prerelease,
        target_commitish=target_commitish,
        immutable=immutable,
    )


def github_release_records(ctx: ReleaseContext) -> tuple[GithubReleaseRecord, ...]:
    output = capture_github_step(
        [
            "gh",
            "api",
            f"repos/{ctx.release.github.repository}/releases",
            "--paginate",
            "--slurp",
            "--field",
            "per_page=100",
        ],
        cwd=ctx.manifest_path.parent,
    )
    try:
        pages = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ReleaseError("GitHub REST release list readback was not valid JSON.") from exc
    if not isinstance(pages, list):
        raise ReleaseError("GitHub REST release list readback did not return pages.")
    records: list[GithubReleaseRecord] = []
    for page in pages:
        if not isinstance(page, list):
            raise ReleaseError("GitHub REST release list readback contained an invalid page.")
        for payload in page:
            record = parse_github_release_record(payload, description="GitHub REST release list")
            if record.tag_name == ctx.tag_name:
                records.append(record)
    return tuple(records)


def github_release_record(ctx: ReleaseContext, release_id: int) -> GithubReleaseRecord:
    output = capture_github_step(
        [
            "gh",
            "api",
            f"repos/{ctx.release.github.repository}/releases/{release_id}",
        ],
        cwd=ctx.manifest_path.parent,
    )
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ReleaseError("GitHub REST release readback was not valid JSON.") from exc
    return parse_github_release_record(payload, description=f"GitHub Release {release_id}")


def github_release_state(ctx: ReleaseContext) -> tuple[GithubReleaseState, int | None]:
    """Read a release state through the list API, which includes drafts."""
    try:
        records = github_release_records(ctx)
    except ReleaseError as exc:
        detail = str(exc).lower()
        if "not found" in detail or "http 404" in detail or "404" in detail:
            return "absent", None
        return "unavailable", None

    if not records:
        return "absent", None
    if len(records) > 1:
        raise ReleaseError(f"GitHub has multiple releases for tag {ctx.tag_name}; refusing to choose one.")
    record = records[0]
    return ("draft" if record.draft else "published"), record.release_id


def github_release_assets(ctx: ReleaseContext, release_id: int) -> dict[str, int]:
    output = capture_github_step(
        [
            "gh",
            "api",
            f"repos/{ctx.release.github.repository}/releases/{release_id}/assets",
            "--paginate",
            "--slurp",
            "--field",
            "per_page=100",
        ],
        cwd=ctx.manifest_path.parent,
    )
    try:
        pages = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ReleaseError("GitHub REST release asset readback was not valid JSON.") from exc
    if not isinstance(pages, list):
        raise ReleaseError("GitHub REST release asset readback did not return pages.")
    assets: dict[str, int] = {}
    for page in pages:
        if not isinstance(page, list):
            raise ReleaseError("GitHub REST release asset readback contained an invalid page.")
        for payload in page:
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("name"), str)
                or isinstance(payload.get("id"), bool)
                or not isinstance(payload.get("id"), int)
            ):
                raise ReleaseError("GitHub REST release asset readback contained an invalid asset.")
            assets[payload["name"]] = payload["id"]
    return assets


def github_release_asset_names(ctx: ReleaseContext, release_id: int) -> set[str]:
    return set(github_release_assets(ctx, release_id))


def verify_downloaded_release_asset(ctx: ReleaseContext, release_id: int, asset: Path) -> None:
    """Download one public asset and compare its bytes with the staged input."""
    with tempfile.TemporaryDirectory(prefix="base-release-asset-readback-") as directory:
        download_directory = Path(directory)
        asset_id = github_release_assets(ctx, release_id).get(asset.name)
        if asset_id is None:
            raise ReleaseError(f"GitHub Release is missing required asset: {asset.name}.")
        downloaded = download_directory / asset.name
        capture_github_step(
            [
                "gh",
                "api",
                f"repos/{ctx.release.github.repository}/releases/assets/{asset_id}",
                "--header",
                "Accept: application/octet-stream",
                "--output",
                str(downloaded),
            ],
            cwd=ctx.manifest_path.parent,
        )
        try:
            downloaded_bytes = downloaded.read_bytes()
            expected_bytes = asset.read_bytes()
        except OSError as exc:
            raise ReleaseError(f"Unable to read downloaded release asset {asset.name}: {exc}") from exc
        if downloaded_bytes != expected_bytes:
            raise ReleaseError(
                f"GitHub Release asset {asset.name} differs from the reviewed staged bytes."
            )


def verify_release_assets(ctx: ReleaseContext, release_id: int, assets: tuple[Path, ...]) -> None:
    names = github_release_asset_names(ctx, release_id)
    missing = sorted(asset.name for asset in assets if asset.name not in names)
    if missing:
        raise ReleaseError(f"GitHub Release is missing required assets: {', '.join(missing)}.")
    for asset in assets:
        verify_downloaded_release_asset(ctx, release_id, asset)


def reconcile_draft_release(
    ctx: ReleaseContext, release_id: int, title: str, body: str, expected_sha: str,
) -> int:
    record = github_release_record(ctx, release_id)
    if record.tag_name != ctx.tag_name:
        raise ReleaseError(
            f"GitHub Release {release_id} has tag {record.tag_name!r}, expected {ctx.tag_name!r}."
        )
    if not record.draft:
        raise ReleaseError(f"GitHub Release {ctx.tag_name} is no longer a mutable draft.")
    if record.target_commitish != expected_sha:
        raise ReleaseError(
            f"GitHub draft {ctx.tag_name} targets {record.target_commitish!r}, expected {expected_sha}."
        )
    if record.name == title and record.body == body:
        return release_id

    patch_command = [
        "gh",
        "api",
        f"repos/{ctx.release.github.repository}/releases/{release_id}",
        "--method",
        "PATCH",
        "--raw-field",
        f"name={title}",
        "--raw-field",
        f"body={body}",
        "--raw-field",
        f"target_commitish={expected_sha}",
        "--field",
        "draft=true",
        "--field",
        "prerelease=false",
    ]
    capture_release_step(patch_command, cwd=ctx.manifest_path.parent)
    updated = github_release_record(ctx, release_id)
    if updated.name != title or updated.body != body or updated.target_commitish != expected_sha:
        raise ReleaseError(f"GitHub draft {ctx.tag_name} did not reconcile to the reviewed release metadata.")
    return release_id


def create_or_resume_draft_release(
    ctx: ReleaseContext, title: str, notes_path: Path, expected_sha: str,
) -> int:
    """Create a mutable REST draft or safely resume the existing draft."""
    try:
        body = notes_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReleaseError(f"Unable to read staged release notes: {exc}") from exc

    state, release_id = github_release_state(ctx)
    if state == "draft" and release_id is not None:
        return reconcile_draft_release(ctx, release_id, title, body, expected_sha)
    if state == "published":
        raise ReleaseError(
            f"GitHub Release {ctx.tag_name} is already published and immutable; refusing to mutate it."
        )
    if state == "unavailable":
        raise ReleaseError(f"Unable to inspect GitHub Release {ctx.tag_name} before draft creation.")

    create_command = [
        "gh",
        "api",
        f"repos/{ctx.release.github.repository}/releases",
        "--method",
        "POST",
        "--raw-field",
        f"tag_name={ctx.tag_name}",
        "--raw-field",
        f"name={title}",
        "--raw-field",
        f"body={body}",
        "--raw-field",
        f"target_commitish={expected_sha}",
        "--field",
        "draft=true",
        "--field",
        "prerelease=false",
        "--jq",
        ".id",
    ]
    try:
        release_id_text = capture_release_step(create_command, cwd=ctx.manifest_path.parent)
    except ReleaseError as exc:
        # A timed-out POST may have succeeded. Read first; never create a second
        # release when the server already has the draft.
        recovered_state, recovered_id = github_release_state(ctx)
        if recovered_state == "draft" and recovered_id is not None:
            return reconcile_draft_release(ctx, recovered_id, title, body, expected_sha)
        if not is_github_rate_limit_error(exc):
            raise
        time.sleep(RELEASE_API_RETRY_DELAYS_SECONDS[0])
        recovered_state, recovered_id = github_release_state(ctx)
        if recovered_state == "draft" and recovered_id is not None:
            return reconcile_draft_release(ctx, recovered_id, title, body, expected_sha)
        try:
            release_id_text = capture_release_step(create_command, cwd=ctx.manifest_path.parent)
        except ReleaseError as retry_exc:
            recovered_state, recovered_id = github_release_state(ctx)
            if recovered_state == "draft" and recovered_id is not None:
                return reconcile_draft_release(ctx, recovered_id, title, body, expected_sha)
            raise retry_exc from exc

    if not release_id_text.strip().isdigit():
        raise ReleaseError("GitHub draft creation did not return a valid release ID.")
    release_id = int(release_id_text.strip())
    return reconcile_draft_release(ctx, release_id, title, body, expected_sha)


def upload_and_verify_release_assets(
    ctx: ReleaseContext, release_id: int, assets: tuple[Path, ...],
) -> None:
    """Upload only missing assets, then verify their downloaded bytes."""
    for asset in assets:
        names = github_release_asset_names(ctx, release_id)
        if asset.name not in names:
            upload_url = (
                f"https://uploads.github.com/repos/{ctx.release.github.repository}"
                f"/releases/{release_id}/assets?name={quote(asset.name, safe='')}"
            )
            upload_command = [
                "gh",
                "api",
                upload_url,
                "--method",
                "POST",
                "--header",
                "Content-Type: application/octet-stream",
                "--input",
                str(asset),
            ]
            try:
                capture_release_step(upload_command, cwd=ctx.manifest_path.parent)
            except ReleaseError as exc:
                # An upload can succeed while its response is lost. Treat a
                # now-visible asset as success; retry only when it is absent.
                names = github_release_asset_names(ctx, release_id)
                if asset.name not in names:
                    if not is_github_rate_limit_error(exc):
                        raise
                    time.sleep(RELEASE_API_RETRY_DELAYS_SECONDS[0])
                    names = github_release_asset_names(ctx, release_id)
                    if asset.name not in names:
                        try:
                            capture_release_step(upload_command, cwd=ctx.manifest_path.parent)
                        except ReleaseError as retry_exc:
                            if asset.name not in github_release_asset_names(ctx, release_id):
                                raise retry_exc from exc
    verify_release_assets(ctx, release_id, assets)


def publish_draft_release(ctx: ReleaseContext, release_id: int) -> None:
    """Publish only after the draft's assets have passed byte-level readback."""
    record = github_release_record(ctx, release_id)
    if record.tag_name != ctx.tag_name:
        raise ReleaseError(
            f"GitHub Release {release_id} has tag {record.tag_name!r}, expected {ctx.tag_name!r}."
        )
    if not record.draft:
        return

    patch_command = [
        "gh",
        "api",
        f"repos/{ctx.release.github.repository}/releases/{release_id}",
        "--method",
        "PATCH",
        "--field",
        "draft=false",
    ]
    try:
        capture_release_step(patch_command, cwd=ctx.manifest_path.parent)
    except ReleaseError as exc:
        current = github_release_record(ctx, release_id)
        if not current.draft:
            return
        if not is_github_rate_limit_error(exc):
            raise
        time.sleep(RELEASE_API_RETRY_DELAYS_SECONDS[0])
        try:
            capture_release_step(patch_command, cwd=ctx.manifest_path.parent)
        except ReleaseError as retry_exc:
            current = github_release_record(ctx, release_id)
            if not current.draft:
                return
            raise retry_exc from exc

    current = github_release_record(ctx, release_id)
    if current.draft:
        raise ReleaseError("GitHub Release did not become published after draft publication.")


def verify_local_annotated_tag(root: Path, tag_name: str, expected_sha: str) -> None:
    object_type = capture_release_step(["git", "cat-file", "-t", f"refs/tags/{tag_name}"], cwd=root)
    if object_type != "tag":
        raise ReleaseError(f"Local release tag {tag_name} is not an annotated tag.")
    peeled_sha = capture_release_step(["git", "rev-parse", f"refs/tags/{tag_name}^{{}}"], cwd=root).lower()
    if peeled_sha != expected_sha:
        raise ReleaseError(
            f"Local annotated tag {tag_name} resolves to {peeled_sha or 'no commit'}, expected {expected_sha}."
        )


def verify_remote_annotated_tag(root: Path, tag_name: str, expected_sha: str) -> None:
    state = inspect_remote_annotated_tag(root, tag_name, expected_sha)
    if state == "intended":
        return
    if state == "unavailable":
        raise ReleaseError(f"Unable to verify remote tag {tag_name} safely on origin.")
    if state == "conflict":
        raise ReleaseError(
            f"Remote tag {tag_name} is missing or is not an annotated tag on origin, "
            "or resolves to a conflicting commit."
        )
    raise ReleaseError(f"Remote tag {tag_name} is missing or is not an annotated tag on origin.")


def local_tag_ref_exists(root: Path, tag_name: str) -> bool:
    try:
        capture_release_step(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag_name}"],
            cwd=root,
        )
    except ReleaseError:
        return False
    return True


def inspect_remote_annotated_tag(root: Path, tag_name: str, expected_sha: str) -> RemoteTagState:
    try:
        output = capture_release_step(
            [
                "git",
                "ls-remote",
                "--tags",
                "origin",
                f"refs/tags/{tag_name}",
                f"refs/tags/{tag_name}^{{}}",
            ],
            cwd=root,
        )
    except ReleaseError:
        return "unavailable"

    if not output.strip():
        return "absent"
    tag_object_sha: str | None = None
    peeled_sha: str | None = None
    for line in output.splitlines():
        value, separator, ref_name = line.partition("\t")
        normalized = value.lower()
        if not separator or not valid_full_git_sha(normalized):
            continue
        if ref_name == f"refs/tags/{tag_name}":
            tag_object_sha = normalized
        elif ref_name == f"refs/tags/{tag_name}^{{}}":
            peeled_sha = normalized
    if tag_object_sha is None or peeled_sha is None:
        return "conflict"
    return "intended" if peeled_sha == expected_sha else "conflict"


def verify_github_release(
    ctx: ReleaseContext,
    expected_sha: str,
    *,
    release_id: int | None = None,
    expected_assets: tuple[str, ...] = (),
) -> None:
    if release_id is None:
        state, release_id = github_release_state(ctx)
        if state not in {"draft", "published"} or release_id is None:
            raise ReleaseError(f"GitHub Release {ctx.tag_name} is not available for verification.")
    release_record = github_release_record(ctx, release_id)
    if release_record.tag_name != ctx.tag_name:
        raise ReleaseError(
            f"GitHub Release resolved tag '{release_record.tag_name}', expected '{ctx.tag_name}'."
        )
    if release_record.target_commitish != expected_sha:
        raise ReleaseError(
            f"GitHub Release {ctx.tag_name} targets {release_record.target_commitish!r}, expected {expected_sha}."
        )

    encoded_tag = quote(ctx.tag_name, safe="")
    ref_type, tag_object_sha = parse_github_object(
        capture_release_step(
            [
                "gh",
                "api",
                f"repos/{ctx.release.github.repository}/git/ref/tags/{encoded_tag}",
                "--jq",
                '.object.type + "\\t" + .object.sha',
            ],
            cwd=ctx.manifest_path.parent,
        ),
        description=f"GitHub tag ref {ctx.tag_name}",
    )
    if ref_type != "tag":
        raise ReleaseError(f"GitHub tag {ctx.tag_name} is not annotated.")

    tag_target_type, github_sha = parse_github_object(
        capture_release_step(
            [
                "gh",
                "api",
                f"repos/{ctx.release.github.repository}/git/tags/{tag_object_sha}",
                "--jq",
                '.object.type + "\\t" + .object.sha',
            ],
            cwd=ctx.manifest_path.parent,
        ),
        description=f"GitHub annotated tag {ctx.tag_name}",
    )
    if tag_target_type != "commit" or github_sha != expected_sha:
        raise ReleaseError(
            f"GitHub annotated tag {ctx.tag_name} resolves to {tag_target_type} {github_sha}, "
            f"expected commit {expected_sha}."
        )

    if expected_assets:
        actual_assets = github_release_asset_names(ctx, release_id)
        missing_assets = sorted(set(expected_assets) - actual_assets)
        if missing_assets:
            raise ReleaseError(
                f"GitHub Release {ctx.tag_name} is missing required assets: {', '.join(missing_assets)}."
            )


def parse_github_object(output: str, *, description: str) -> tuple[str, str]:
    object_type, separator, object_sha = output.strip().partition("\t")
    normalized_sha = object_sha.lower()
    if not separator or object_type not in {"commit", "tag"} or not valid_full_git_sha(normalized_sha):
        raise ReleaseError(f"{description} did not resolve to an unambiguous full Git object.")
    return object_type, normalized_sha


def valid_full_git_sha(value: str) -> bool:
    return len(value) in FULL_GIT_SHA_LENGTHS and all(character in "0123456789abcdef" for character in value)


def write_release_bom_assets(
    bom_path: Path, directory: Path, *, expected_repository: str | None = None,
    expected_version: str | None = None, expected_commit: str | None = None,
) -> tuple[Path, Path]:
    """Stage one validated BOM snapshot under the stable publication names."""
    try:
        snapshot = read_validated_bom(
            bom_path, expected_repository=expected_repository,
            expected_version=expected_version, expected_commit=expected_commit,
        )
    except ReleaseBomError as exc:
        raise ReleaseError(str(exc)) from exc
    bom_asset = directory / RELEASE_BOM_ASSET_NAME
    digest_asset = directory / RELEASE_BOM_DIGEST_ASSET_NAME
    try:
        bom_asset.write_bytes(snapshot.content)
        digest_asset.write_text(f"{snapshot.digest}  {RELEASE_BOM_ASSET_NAME}\n", encoding="utf-8")
    except OSError as exc:
        raise ReleaseError(f"Unable to stage release BOM assets: {exc}") from exc
    return bom_asset, digest_asset


@contextmanager
def stage_release_files(
    ctx: ReleaseContext, notes: str, expected_sha: str,
) -> Iterator[tuple[Path, tuple[Path, Path] | None]]:
    """Prepare all local publication inputs before the caller creates a tag."""
    try:
        with tempfile.TemporaryDirectory(prefix="base-release-assets-") as directory:
            asset_directory = Path(directory)
            bom_assets = (
                write_release_bom_assets(
                    ctx.bom_path, asset_directory,
                    expected_repository=ctx.release.github.repository,
                    expected_version=ctx.version, expected_commit=expected_sha,
                ) if ctx.bom_path is not None else None
            )
            notes_path = asset_directory / "release-notes.md"
            notes_path.write_text(notes + "\n", encoding="utf-8")
            yield notes_path, bom_assets
    except OSError as exc:
        raise ReleaseError(f"Unable to prepare local release files: {exc}") from exc
