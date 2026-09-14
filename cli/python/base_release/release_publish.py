from __future__ import annotations

import shlex
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal
from urllib.parse import quote

import base_cli
from base_setup import process

from .release_bom import ReleaseBomError, read_validated_bom
from .release_model import ReleaseContext, ReleaseError
from .release_readiness import last_non_empty_line

RELEASE_STEP_TIMEOUT_SECONDS = 120
FULL_GIT_SHA_LENGTHS = frozenset((40, 64))
RELEASE_BOM_ASSET_NAME = "release-bom.json"
RELEASE_BOM_DIGEST_ASSET_NAME = "release-bom.sha256"
RemoteTagState = Literal["absent", "intended", "conflict", "unavailable"]


def release_publish_recovery_guidance(ctx: ReleaseContext, title: str) -> str:
    display_command = base_cli.delegated_display_command("basectl release") or "basectl release"
    notes_file = f"{ctx.tag_name}-notes.md"
    notes_command = (
        f"{display_command} notes --version {shlex.quote(ctx.version)} "
        f"--manifest {shlex.quote(str(ctx.manifest_path))}"
    )
    create_release_command = (
        f"gh release create {shlex.quote(ctx.tag_name)} --verify-tag "
        f"--repo {shlex.quote(ctx.release.github.repository)} "
        f"--title {shlex.quote(title)} "
        f"--notes-file {shlex.quote(notes_file)}"
    )
    bom_guidance = ""
    if ctx.bom_path is not None or (ctx.release.bom is not None and ctx.release.bom.required):
        bom_guidance = (
            "A governed release is NOT complete without release-bom.json and release-bom.sha256.\n"
            "Recover the original reviewed canonical BOM and matching digest sidecar; do not regenerate "
            "evidence from a different checkout. Validate the BOM against the intended repository, version, "
            "and commit, and verify its SHA-256 before uploading the pair under those stable asset names.\n"
            "If the GitHub Release already exists, inspect it instead of rerunning create. Upload missing "
            "assets without overwriting existing ones; stop if an existing asset conflicts. Download and "
            "verify both published assets against the reviewed pair before declaring success.\n"
        )
    return (
        f"Release publish already created and pushed tag {ctx.tag_name}, "
        "but GitHub Release creation, BOM asset upload, or verification did not complete cleanly.\n"
        "After confirming the pushed annotated tag resolves to the intended commit, complete the GitHub Release:\n"
        f"  {notes_command} > {shlex.quote(notes_file)}\n"
        f"  {create_release_command}\n"
        f"{bom_guidance}"
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
    expected_assets: tuple[str, ...] = (),
) -> None:
    release_tag = capture_release_step(
        [
            "gh",
            "release",
            "view",
            ctx.tag_name,
            "--repo",
            ctx.release.github.repository,
            "--json",
            "tagName",
            "--jq",
            ".tagName",
        ],
        cwd=ctx.manifest_path.parent,
    )
    if release_tag != ctx.tag_name:
        raise ReleaseError(
            f"GitHub Release resolved tag '{release_tag or 'none'}', expected '{ctx.tag_name}'."
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
        assets = capture_release_step(
            [
                "gh",
                "release",
                "view",
                ctx.tag_name,
                "--repo",
                ctx.release.github.repository,
                "--json",
                "assets",
                "--jq",
                '[.assets[].name] | sort | join("\\n")',
            ],
            cwd=ctx.manifest_path.parent,
        )
        actual_assets = set(assets.splitlines())
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


def upload_release_bom_assets(ctx: ReleaseContext, assets: tuple[Path, Path]) -> None:
    """Attach the BOM and its digest to the already-created GitHub Release."""
    run_release_step(
        [
            "gh",
            "release",
            "upload",
            ctx.tag_name,
            *(str(asset) for asset in assets),
            "--repo",
            ctx.release.github.repository,
            "--clobber",
        ],
        cwd=ctx.manifest_path.parent,
    )
