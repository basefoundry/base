from __future__ import annotations

import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import base_cli

from .release_model import ReleaseContext, ReleaseError
from .release_readiness import last_non_empty_line

RELEASE_STEP_TIMEOUT_SECONDS = 120


def release_publish_recovery_guidance(ctx: ReleaseContext, title: str) -> str:
    display_command = base_cli.delegated_display_command("basectl release") or "basectl release"
    notes_file = f"{ctx.tag_name}-notes.md"
    notes_command = (
        f"{display_command} notes --version {shlex.quote(ctx.version)} "
        f"--manifest {shlex.quote(str(ctx.manifest_path))}"
    )
    create_release_command = (
        f"gh release create {shlex.quote(ctx.tag_name)} "
        f"--repo {shlex.quote(ctx.release.github.repository)} "
        f"--title {shlex.quote(title)} "
        f"--notes-file {shlex.quote(notes_file)}"
    )
    return (
        f"Release publish already created and pushed tag {ctx.tag_name}, "
        "but GitHub Release creation failed.\n"
        "To complete the release after fixing GitHub access, create the GitHub Release from the pushed tag:\n"
        f"  {notes_command} > {shlex.quote(notes_file)}\n"
        f"  {create_release_command}\n"
        "To abandon this release attempt, remove the local and remote tag after confirming no one else is using it:\n"
        f"  git tag -d {shlex.quote(ctx.tag_name)}\n"
        f"  git push origin :refs/tags/{shlex.quote(ctx.tag_name)}"
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
    joined = shlex.join(command)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=RELEASE_STEP_TIMEOUT_SECONDS,
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


def write_temp_release_notes(notes: str) -> Path:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as notes_file:
        notes_file.write(notes)
        notes_file.write("\n")
        return Path(notes_file.name)
