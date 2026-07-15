from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import SplitResult
from urllib.parse import unquote_plus
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from base_cli.redaction import REDACTED
from base_cli.redaction import is_secret_key
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_onboarding import test_command_for_status
from base_projects.workspace_statuses import WorkspaceProjectStatus
from base_projects.workspace_statuses import workspace_manifest_project_statuses


# Keep these tuples in parity with the shell-owned repo check contract. The
# focused parity test prevents either representation from drifting silently.
REPO_BASELINE_FILES = (
    "README.md",
    "VERSION",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    ".github/pull_request_template.md",
    ".github/base-project.yml",
    "LICENSE",
    ".gitignore",
    "base_manifest.yaml",
    "tests/validate.sh",
    ".github/workflows/issue-branch-policy.yml",
    ".github/workflows/project-intake.yml",
    ".github/workflows/tests.yml",
)

REPO_AGENT_GUIDANCE_FILES = (
    "AGENTS.md",
    "skills.md",
    ".github/pull_request_template.md",
)

UNMANAGED_AGENT_GUIDANCE_FILES = (
    "AGENTS.md",
    "skills.md",
)

SCP_REPOSITORY_URL_RE = re.compile(r"^(?P<userinfo>[^@\s]+)@(?P<location>[^:\s]+:.+)$")
URL_PARAMETER_SEPARATOR_RE = re.compile(r"([&;])")
NETWORK_REPOSITORY_URL_SCHEMES = frozenset(("git", "https", "ssh"))


@dataclass(frozen=True)
class RepositoryFileSignal:
    status: str
    missing_files: tuple[str, ...] = ()
    not_executable_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepositoryValidationSignal:
    status: str
    command: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class WorkspaceAgentBriefRepository:
    repository: str
    project: str | None
    path: Path
    expected: bool
    required: bool
    base_managed: bool
    scope: str
    discovery_status: str
    manifest: str
    venv: str
    handoff_status: str
    baseline: RepositoryFileSignal
    agent_guidance: RepositoryFileSignal
    ai_context_status: str
    validation: RepositoryValidationSignal
    next_actions: tuple[str, ...]
    manifest_path: Path | None = None
    url: str | None = None
    default_branch: str | None = None


@dataclass(frozen=True)
class WorkspaceAgentBrief:
    workspace_root: Path
    workspace_manifest: WorkspaceManifest
    repositories: tuple[WorkspaceAgentBriefRepository, ...]


def workspace_agent_brief(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
) -> WorkspaceAgentBrief:
    statuses = workspace_manifest_project_statuses(
        workspace_root,
        workspace_manifest,
        probe_venv=False,
    )
    return WorkspaceAgentBrief(
        workspace_root=workspace_root,
        workspace_manifest=workspace_manifest,
        repositories=tuple(agent_brief_repository_from_status(status) for status in statuses),
    )


def agent_brief_repository_from_status(status: WorkspaceProjectStatus) -> WorkspaceAgentBriefRepository:
    repository = status.repository or status.root.name
    present = status.repo != "missing"
    base_managed = status.manifest in ("valid", "invalid")
    if not present:
        baseline = unavailable_file_signal()
        agent_guidance = unavailable_file_signal()
    elif not base_managed:
        baseline = not_applicable_file_signal()
        agent_guidance = unmanaged_agent_guidance_signal(status.root)
    else:
        baseline = repository_file_signal(status.root, REPO_BASELINE_FILES, check_executable=True)
        agent_guidance = repository_file_signal(status.root, REPO_AGENT_GUIDANCE_FILES)
    ai_context_status = repository_ai_context_status(status.root) if present else "unavailable"
    validation = repository_validation_signal(status) if present else RepositoryValidationSignal(status="unavailable")
    handoff_status = repository_handoff_status(status, baseline, agent_guidance)

    return WorkspaceAgentBriefRepository(
        repository=repository,
        project=status.name if status.manifest == "valid" else None,
        path=status.root,
        expected=status.expected,
        required=status.required,
        base_managed=base_managed,
        scope=repository_scope(status),
        discovery_status=status.repo,
        manifest=status.manifest,
        venv=status.venv,
        handoff_status=handoff_status,
        baseline=baseline,
        agent_guidance=agent_guidance,
        ai_context_status=ai_context_status,
        validation=validation,
        next_actions=repository_next_actions(status, handoff_status, baseline, agent_guidance, validation),
        manifest_path=status.manifest_path,
        url=redact_repository_url(status.url) if status.url is not None else None,
        default_branch=status.default_branch,
    )


def unavailable_file_signal() -> RepositoryFileSignal:
    return RepositoryFileSignal(status="unavailable")


def not_applicable_file_signal() -> RepositoryFileSignal:
    return RepositoryFileSignal(status="not_applicable")


def repository_file_signal(
    root: Path,
    required_files: tuple[str, ...],
    *,
    check_executable: bool = False,
) -> RepositoryFileSignal:
    missing_files = tuple(relative_path for relative_path in required_files if not (root / relative_path).is_file())
    not_executable_files: tuple[str, ...] = ()
    if check_executable:
        validation_script = root / "tests" / "validate.sh"
        if validation_script.is_file() and not executable_file(validation_script):
            not_executable_files = ("tests/validate.sh",)

    status = "complete" if not missing_files and not not_executable_files else "incomplete"
    return RepositoryFileSignal(
        status=status,
        missing_files=missing_files,
        not_executable_files=not_executable_files,
    )


def unmanaged_agent_guidance_signal(root: Path) -> RepositoryFileSignal:
    missing_files = tuple(
        relative_path for relative_path in UNMANAGED_AGENT_GUIDANCE_FILES if not (root / relative_path).is_file()
    )
    if not missing_files:
        status = "present"
    elif len(missing_files) == len(UNMANAGED_AGENT_GUIDANCE_FILES):
        status = "missing"
    else:
        status = "partial"
    return RepositoryFileSignal(status=status, missing_files=missing_files)


def executable_file(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def redact_repository_url(value: str) -> str:
    if Path(value).is_absolute():
        return value

    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value):
        return REDACTED

    scp_match = None if "://" in value else SCP_REPOSITORY_URL_RE.match(value)
    if scp_match is not None:
        userinfo = scp_match.group("userinfo")
        sanitized_userinfo = userinfo if userinfo == "git" else REDACTED
        sanitized = f"{sanitized_userinfo}@{scp_match.group('location')}"
        return redact_url_suffix_parameters(sanitized)

    parsed = parse_repository_url(value)
    if parsed is None:
        return REDACTED

    netloc = parsed.netloc
    userinfo, separator, host = netloc.rpartition("@")
    if separator and userinfo != "git":
        netloc = f"{REDACTED}@{host}"
    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            redact_url_parameters(parsed.query),
            redact_url_parameters(parsed.fragment),
        )
    )


def parse_repository_url(value: str) -> SplitResult | None:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme in NETWORK_REPOSITORY_URL_SCHEMES:
        return parsed if valid_network_repository_url(parsed) else None
    if parsed.scheme == "file":
        return parsed
    return None


def valid_network_repository_url(parsed: SplitResult) -> bool:
    try:
        hostname = parsed.hostname
        _port = parsed.port
    except ValueError:
        return False
    return bool(parsed.netloc and hostname)


def redact_url_suffix_parameters(value: str) -> str:
    base_and_query, fragment_separator, fragment = value.partition("#")
    base, query_separator, query = base_and_query.partition("?")
    sanitized = base
    if query_separator:
        sanitized = f"{sanitized}?{redact_url_parameters(query)}"
    if fragment_separator:
        sanitized = f"{sanitized}#{redact_url_parameters(fragment)}"
    return sanitized


def redact_url_parameters(value: str) -> str:
    parts = URL_PARAMETER_SEPARATOR_RE.split(value)
    for index in range(0, len(parts), 2):
        key, separator, _parameter_value = parts[index].partition("=")
        if separator and is_secret_key(unquote_plus(key)):
            parts[index] = f"{key}={REDACTED}"
    return "".join(parts)


def repository_ai_context_status(root: Path) -> str:
    context_dir = root / ".ai-context"
    if not context_dir.exists():
        return "missing"
    if not context_dir.is_dir():
        return "invalid"
    try:
        has_markdown = any(path.is_file() for path in context_dir.rglob("*.md"))
    except OSError:
        return "invalid"
    return "present" if has_markdown else "invalid"


def repository_validation_signal(status: WorkspaceProjectStatus) -> RepositoryValidationSignal:
    validation_script = status.root / "tests" / "validate.sh"
    if executable_file(validation_script):
        return RepositoryValidationSignal(
            status="available",
            command=command_in_directory(status.root, "./tests/validate.sh"),
            source="repo_baseline",
        )

    test_command = test_command_for_status(status)
    if test_command is not None:
        return RepositoryValidationSignal(
            status="available",
            command=command_in_directory(status.root, "basectl test"),
            source="manifest_test",
        )
    return RepositoryValidationSignal(status="unavailable")


def repository_scope(status: WorkspaceProjectStatus) -> str:
    if not status.expected:
        return "local_only"
    return "required" if status.required else "optional"


def repository_handoff_status(
    status: WorkspaceProjectStatus,
    baseline: RepositoryFileSignal,
    agent_guidance: RepositoryFileSignal,
) -> str:
    if status.repo == "missing":
        handoff_status = "missing_required" if status.required else "missing_optional"
    elif status.manifest == "missing":
        handoff_status = "unmanaged"
    elif status.manifest == "invalid":
        handoff_status = "needs_manifest_repair"
    elif baseline.status != "complete" or status.manifest != "valid":
        handoff_status = "needs_baseline"
    elif status.venv not in ("ready", "present_unverified"):
        handoff_status = "needs_setup"
    elif agent_guidance.status != "complete":
        handoff_status = "needs_agent_guidance"
    else:
        handoff_status = "ready"
    return handoff_status


def repository_next_actions(
    status: WorkspaceProjectStatus,
    handoff_status: str,
    baseline: RepositoryFileSignal,
    agent_guidance: RepositoryFileSignal,
    validation: RepositoryValidationSignal,
) -> tuple[str, ...]:
    if status.repo == "missing":
        clone_command = None
        if status.url is not None:
            clone_command = shlex.join(
                ["git", "clone", redact_repository_url(status.url), str(status.root)]
            )
        if status.required:
            if clone_command is not None:
                return (clone_command,)
            return (f"Create or clone repository '{status.repository or status.name}' into {status.root}.",)
        if clone_command is not None:
            return (f"Optional repository; clone only if this handoff needs it: {clone_command}",)
        return ("Optional repository is missing; no action is required for this handoff.",)

    if handoff_status == "unmanaged":
        return ()

    actions: list[str] = []
    if status.manifest == "invalid":
        actions.append(f"Fix invalid manifest {status.manifest_path}.")
    elif baseline.status != "complete" or status.manifest != "valid":
        actions.append(repo_init_command(status))

    if status.manifest == "valid" and status.venv not in ("ready", "present_unverified"):
        actions.append(command_in_directory(status.root, "basectl setup"))

    if baseline.status == "complete" and agent_guidance.status != "complete":
        actions.append(shlex.join(["basectl", "repo", "agent-guidance", str(status.root)]))

    if baseline.status == "complete" and agent_guidance.status == "complete":
        actions.append(shlex.join(["basectl", "repo", "check", str(status.root), "--agent-ready"]))

    if validation.status == "available" and validation.command is not None:
        actions.append(validation.command)

    return tuple(dict.fromkeys(actions))


def repo_init_command(status: WorkspaceProjectStatus) -> str:
    return shlex.join(
        [
            "basectl",
            "repo",
            "init",
            status.root.name,
            "--path",
            str(status.root),
            "--agent-ready",
        ]
    )


def command_in_directory(root: Path, command: str) -> str:
    return f"cd {shlex.quote(str(root))} && {command}"
