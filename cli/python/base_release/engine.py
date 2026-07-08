from __future__ import annotations

import subprocess  # pylint: disable=unused-import
import sys

import base_cli
from base_setup import process  # pylint: disable=unused-import
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError

from .release_model import ReleaseContext, ReleaseError, ReleaseFinding
from .release_parser import ReleaseArguments
from .release_parser import ReleaseUsageError
from .release_parser import parse_release_args
from .release_parser import print_usage
# pylint: disable=unused-import
from .release_publish import RELEASE_STEP_TIMEOUT_SECONDS
from .release_publish import release_publish_recovery_guidance, require_interactive_publish_confirmation
from .release_publish import run_release_step, write_temp_release_notes
from .release_readiness import CHANGELOG_HEADER_RE, GIT_INSPECTION_TIMEOUT_SECONDS
from .release_readiness import changelog_finding, current_git_branch, extract_changelog_section
from .release_readiness import gh_cli_finding, git_branch_finding, git_status, git_worktree_finding
from .release_readiness import github_release_finding, last_non_empty_line, local_tag_exists, local_tag_finding
from .release_readiness import read_version_file, release_findings as _release_findings
from .release_readiness import remote_tag_finding, version_file_finding
# pylint: enable=unused-import

app = base_cli.App(name="base_release")
release_findings = lambda ctx: _release_findings(  # pylint: disable=unnecessary-lambda-assignment
    ctx,
    gh_cli_finding_func=gh_cli_finding,
)


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(
    context_settings={
        "allow_extra_args": True,
        "help_option_names": ["-h", "--help"],
        "ignore_unknown_options": True,
    }
)
@base_cli.argument("arguments", nargs=-1)
def run(ctx: base_cli.Context, arguments: tuple[str, ...]) -> int:
    try:
        args = parse_release_args(arguments)
        release_context = build_release_context(ctx, args)
        if args.command == "check":
            return release_check_command(release_context)
        if args.command == "plan":
            return release_plan_command(release_context)
        if args.command == "notes":
            return release_notes_command(release_context)
        if args.command == "publish":
            return release_publish_command(release_context, args)
        raise ReleaseUsageError(f"Unknown release command '{args.command}'.")
    except ReleaseUsageError as exc:
        print_usage(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR
    except (ManifestError, ReleaseError) as exc:
        print_error(exc)
        return base_cli.ExitCode.FAILURE


def print_error(exc: ManifestError | ReleaseError) -> None:
    print(f"ERROR: {exc}", file=sys.stderr)
    guidance = getattr(exc, "guidance", "")
    if guidance:
        print("", file=sys.stderr)
        print("Recovery guidance:", file=sys.stderr)
        print(guidance, file=sys.stderr)


def build_release_context(ctx: base_cli.Context, args: ReleaseArguments) -> ReleaseContext:
    manifest_path = args.manifest_path or ctx.manifest_path
    if manifest_path is None:
        raise ReleaseError("No base_manifest.yaml was found. Pass --manifest <path>.")
    manifest_path = manifest_path.resolve()
    manifest = read_manifest(manifest_path)
    if manifest.release is None:
        raise ReleaseError(f"{manifest_path}: manifest does not declare release metadata.")

    project_root = manifest_path.parent
    release = manifest.release
    return ReleaseContext(
        manifest_path=manifest_path,
        manifest=manifest,
        release=release,
        version=args.version,
        tag_name=f"{release.tag_prefix}{args.version}",
        version_file=project_root / release.version_file,
        changelog=project_root / release.changelog,
    )


def release_check_command(ctx: ReleaseContext) -> int:
    findings = release_findings(ctx)
    print(f"\nRelease check for {ctx.manifest.project_name} v{ctx.version}\n")
    for finding in findings:
        print(f"{finding.status:<5}  {finding.name:<14}  {finding.message}")
    if any(finding.status == "error" for finding in findings):
        return base_cli.ExitCode.FAILURE
    return base_cli.ExitCode.SUCCESS


def release_plan_command(ctx: ReleaseContext) -> int:
    title = render_release_title(ctx)
    print(f"Release plan for {ctx.manifest.project_name} v{ctx.version}")
    print("")
    print(f"Version file: {ctx.release.version_file}")
    print(f"Changelog: {ctx.release.changelog}")
    print(f"Tag: {ctx.tag_name}")
    print(f"GitHub repository: {ctx.release.github.repository}")
    print(f"GitHub release title: {title}")
    print("")
    print_homebrew_handoff(ctx, after_publish=False)
    return base_cli.ExitCode.SUCCESS


def release_notes_command(ctx: ReleaseContext) -> int:
    print(extract_changelog_section(ctx.changelog, ctx.version))
    return base_cli.ExitCode.SUCCESS


def release_publish_command(ctx: ReleaseContext, args: ReleaseArguments) -> int:
    title = render_release_title(ctx)
    findings = tuple(release_findings(ctx))
    blockers = tuple(finding for finding in findings if finding.status != "ok")
    if not blockers:
        findings = findings + (github_release_finding(ctx),)
        blockers = tuple(finding for finding in findings if finding.status != "ok")
    if blockers:
        print(f"\nRelease publish blocked by readiness findings for {ctx.manifest.project_name} v{ctx.version}\n")
        print_findings(blockers)
        return base_cli.ExitCode.FAILURE

    notes = extract_changelog_section(ctx.changelog, ctx.version)

    if args.dry_run:
        print(f"DRY RUN: release publish for {ctx.manifest.project_name} v{ctx.version}")
        print("")
        print(f"Would create annotated tag: {ctx.tag_name}")
        print(f"Would push tag to origin: {ctx.tag_name}")
        print(f"Would create GitHub Release: {title}")
        print(f"Tag URL: {github_tag_url(ctx.release.github.repository, ctx.tag_name)}")
        print(f"GitHub Release URL: {github_release_url(ctx.release.github.repository, ctx.tag_name)}")
        print("")
        print_homebrew_handoff(ctx, after_publish=True)
        return base_cli.ExitCode.SUCCESS

    if not args.yes:
        require_interactive_publish_confirmation(ctx, title)

    project_root = ctx.manifest_path.parent
    run_release_step(["git", "tag", "-a", ctx.tag_name, "-m", f"Release {ctx.tag_name}"], cwd=project_root)
    run_release_step(["git", "push", "origin", ctx.tag_name], cwd=project_root)

    notes_path = write_temp_release_notes(notes)
    try:
        run_release_step(
            [
                "gh",
                "release",
                "create",
                ctx.tag_name,
                "--repo",
                ctx.release.github.repository,
                "--title",
                title,
                "--notes-file",
                str(notes_path),
            ],
            cwd=project_root,
        )
    except ReleaseError as exc:
        raise ReleaseError(
            str(exc),
            guidance=release_publish_recovery_guidance(ctx, title),
        ) from exc
    finally:
        notes_path.unlink(missing_ok=True)

    print(f"GitHub Release published: {github_release_url(ctx.release.github.repository, ctx.tag_name)}")
    print(f"Tag URL: {github_tag_url(ctx.release.github.repository, ctx.tag_name)}")
    print("")
    print_homebrew_handoff(ctx, after_publish=True)
    return base_cli.ExitCode.SUCCESS


def print_findings(findings: tuple[ReleaseFinding, ...]) -> None:
    for finding in findings:
        print(f"{finding.status:<5}  {finding.name:<14}  {finding.message}")


def render_release_title(ctx: ReleaseContext) -> str:
    return ctx.release.github.release_title.format(
        repository=ctx.release.github.repository,
        version=ctx.version,
        tag=ctx.tag_name,
    )


def github_tag_archive_url(repository: str, tag_name: str) -> str:
    return f"https://github.com/{repository}/archive/refs/tags/{tag_name}.tar.gz"


def github_release_url(repository: str, tag_name: str) -> str:
    return f"https://github.com/{repository}/releases/tag/{tag_name}"


def github_tag_url(repository: str, tag_name: str) -> str:
    return f"https://github.com/{repository}/tree/{tag_name}"


def print_homebrew_handoff(ctx: ReleaseContext, *, after_publish: bool) -> None:
    for line in homebrew_handoff_lines(ctx, after_publish=after_publish):
        print(line)


def homebrew_handoff_lines(ctx: ReleaseContext, *, after_publish: bool) -> tuple[str, ...]:
    homebrew = ctx.release.homebrew
    if homebrew is None or not homebrew.required:
        return ("Homebrew handoff: not declared",)

    archive_url = github_tag_archive_url(ctx.release.github.repository, ctx.tag_name)
    header = "Homebrew handoff required after GitHub release:" if after_publish else "Homebrew handoff required:"
    lines = [
        header,
        f"  Tap repository: {homebrew.tap_repository}",
        f"  Formula path: {homebrew.formula_path}",
        f"  Package: {homebrew.package}",
        f"  Archive URL: {archive_url}",
        f"  SHA256 command: curl -fsSL {archive_url} | shasum -a 256",
        "  Validation commands:",
        f"    brew install --build-from-source {homebrew.formula_path}",
        f"    brew test {homebrew.package}",
        f"    brew audit --new --formula {homebrew.formula_path}",
        "  Upgrade smoke:",
        "    brew update",
        f"    brew upgrade {homebrew.package}",
    ]
    if requires_homebrew_upgrade_rehearsal(ctx.version):
        lines.append("  1.0 reminder: validate the Homebrew upgrade path before publishing.")
    return tuple(lines)


def requires_homebrew_upgrade_rehearsal(version: str) -> bool:
    return version == "1.0.0" or version.startswith("1.0.0-rc")
