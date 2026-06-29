from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import base_cli
from base_setup.manifest import BaseManifest
from base_setup.manifest import ManifestError
from base_setup.manifest import ReleaseConfig
from base_setup.manifest import read_manifest


app = base_cli.App(name="base_release")
CHANGELOG_HEADER_RE = re.compile(r"^##\s+(?:\[(?P<bracket>[^\]]+)\]|(?P<plain>\S+))(?:\s+-.*)?$")
GIT_INSPECTION_TIMEOUT_SECONDS = 10
RELEASE_STEP_TIMEOUT_SECONDS = 120


class ReleaseUsageError(RuntimeError):
    pass


class ReleaseError(RuntimeError):
    def __init__(self, message: str, *, guidance: str = "") -> None:
        super().__init__(message)
        self.guidance = guidance


@dataclass(frozen=True)
class ReleaseArguments:
    command: str
    version: str
    manifest_path: Path | None
    dry_run: bool = False
    yes: bool = False


@dataclass
class ReleaseOptionState:
    version: str | None = None
    manifest_path: Path | None = None
    dry_run: bool = False
    yes: bool = False


@dataclass(frozen=True)
class ReleaseContext:
    manifest_path: Path
    manifest: BaseManifest
    release: ReleaseConfig
    version: str
    tag_name: str
    version_file: Path
    changelog: Path


@dataclass(frozen=True)
class ReleaseFinding:
    status: str
    name: str
    message: str


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


def parse_release_args(arguments: tuple[str, ...]) -> ReleaseArguments:
    if not arguments or arguments[0] in ("-h", "--help", "help"):
        print_usage()
        raise SystemExit(0)

    command = arguments[0]
    if command not in ("check", "plan", "notes", "publish"):
        raise ReleaseUsageError(f"Unknown release command '{command}'.")

    state = ReleaseOptionState()
    remaining = list(arguments[1:])
    index = 0
    while index < len(remaining):
        index = parse_release_option(command, remaining, index, state)

    if state.version is None:
        raise ReleaseUsageError(f"The 'release {command}' command requires --version.")
    return ReleaseArguments(
        command=command,
        version=state.version,
        manifest_path=state.manifest_path,
        dry_run=state.dry_run,
        yes=state.yes,
    )


def parse_release_option(
    command: str,
    arguments: list[str],
    index: int,
    state: ReleaseOptionState,
) -> int:
    arg = arguments[index]
    if arg in ("-h", "--help"):
        print_usage()
        raise SystemExit(0)
    if arg == "--version":
        state.version = read_release_option_value(arguments, index, "--version")
        return index + 2
    if arg == "--manifest":
        state.manifest_path = Path(read_release_option_value(arguments, index, "--manifest")).expanduser()
        return index + 2
    if arg == "--dry-run":
        require_publish_option(command, "--dry-run")
        state.dry_run = True
        return index + 1
    if arg == "--yes":
        require_publish_option(command, "--yes")
        state.yes = True
        return index + 1
    raise ReleaseUsageError(f"Unknown release {command} option '{arg}'.")


def read_release_option_value(arguments: list[str], index: int, option_name: str) -> str:
    value_index = index + 1
    if value_index >= len(arguments) or not arguments[value_index]:
        raise ReleaseUsageError(f"Option '{option_name}' requires an argument.")
    return arguments[value_index]


def require_publish_option(command: str, option_name: str) -> None:
    if command != "publish":
        raise ReleaseUsageError(f"Option '{option_name}' is only supported by release publish.")


def print_usage(file: TextIO = sys.stdout) -> None:
    command = base_cli.delegated_display_command("base_release")
    print(
        f"""Usage:
  {command} check --version <version> [--manifest <path>]
  {command} plan --version <version> [--manifest <path>]
  {command} notes --version <version> [--manifest <path>]
  {command} publish --version <version> [--manifest <path>] [--dry-run] [--yes]

Purpose:
  Inspect release readiness and guarded GitHub publishing for a Base-managed
  project. Homebrew tap changes remain a manual handoff.""",
        file=file,
    )


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


def release_findings(ctx: ReleaseContext) -> tuple[ReleaseFinding, ...]:
    findings: list[ReleaseFinding] = [
        ReleaseFinding("ok", "manifest", f"Release metadata found in {ctx.manifest_path}."),
        version_file_finding(ctx),
        changelog_finding(ctx),
        git_worktree_finding(ctx.manifest_path.parent),
        git_branch_finding(ctx.manifest_path.parent),
        gh_cli_finding(),
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


def print_findings(findings: tuple[ReleaseFinding, ...]) -> None:
    for finding in findings:
        print(f"{finding.status:<5}  {finding.name:<14}  {finding.message}")


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
