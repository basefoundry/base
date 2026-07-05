from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from . import process


@dataclass(frozen=True)
class PrerequisiteCheck:
    name: str
    ok: bool
    message: str
    fix: str
    finding_id: str
    status: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HomebrewPackageCheckRequest:
    name: str
    manager: str
    version: str
    package: str
    timeout_seconds: int
    unsupported_manager_message: str
    unsupported_manager_fix: str
    unsupported_manager_finding_id: str
    unsupported_version_message: str
    unsupported_version_fix: str
    unsupported_version_finding_id: str
    missing_homebrew_message: str
    missing_homebrew_fix: str
    missing_homebrew_finding_id: str
    timeout_message: str
    timeout_fix: str
    timeout_finding_id: str
    outdated_message: str
    outdated_fix: str
    package_finding_id: str
    installed_message: str
    missing_package_message: str
    missing_package_fix: str
    details: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def for_artifact(  # pylint: disable=too-many-arguments
        cls,
        *,
        project: str,
        name: str,
        manager: str,
        version: str,
        package: str,
        timeout_seconds: int,
        details: Mapping[str, Any] | None = None,
    ) -> HomebrewPackageCheckRequest:
        return cls(
            name=name,
            manager=manager,
            version=version,
            package=package,
            timeout_seconds=timeout_seconds,
            unsupported_manager_message=f"Artifact manager '{manager}' is not implemented.",
            unsupported_manager_fix=f"basectl setup {project}",
            unsupported_manager_finding_id="BASE-P030",
            unsupported_version_message=(
                f"Homebrew artifact '{name}' specifies version '{version}', "
                "but Base only supports Homebrew artifact version 'latest' right now."
            ),
            unsupported_version_fix=f"Update '{name}' in the project manifest to use version 'latest'.",
            unsupported_version_finding_id="BASE-P031",
            missing_homebrew_message=f"Homebrew is required to check artifact '{name}'.",
            missing_homebrew_fix="basectl setup",
            missing_homebrew_finding_id="BASE-P032",
            timeout_message=f"Homebrew check for artifact '{name}' timed out after {timeout_seconds} seconds.",
            timeout_fix=f"Retry 'basectl doctor {project}' or inspect Homebrew with 'brew doctor'.",
            timeout_finding_id="BASE-P033",
            outdated_message=f"Artifact '{name}' is outdated via Homebrew package '{package}'.",
            outdated_fix=f"basectl setup {project}",
            package_finding_id="BASE-P033",
            installed_message=f"Artifact '{name}' is installed via Homebrew package '{package}' and is current.",
            missing_package_message=f"Artifact '{name}' is not installed via Homebrew package '{package}'.",
            missing_package_fix=f"basectl setup {project}",
            details={} if details is None else details,
        )


@dataclass(frozen=True)
class GitHubCliAuthCheckRequest:
    timeout_seconds: int
    missing_gh_fix: str
    command: tuple[str, ...] = ("gh", "auth", "status", "-h", "github.com")
    missing_gh_finding_id: str = "BASE-D105"
    auth_finding_id: str = "BASE-D106"


CommandExists = Callable[[str], bool]
RunCheck = Callable[..., bool]
PackageOutdated = Callable[[str, int | None], bool]


def homebrew_no_auto_update_env() -> dict[str, str]:
    env = os.environ.copy()
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    return env


def homebrew_package_outdated(package: str, timeout_seconds: int | None = None) -> bool:
    completed = process.run_capture(
        ["brew", "outdated", package],
        env=homebrew_no_auto_update_env(),
        timeout_seconds=timeout_seconds,
    )
    return homebrew_outdated_output_contains_package(completed.stdout, package)


def homebrew_outdated_output_contains_package(output: str, package: str) -> bool:
    for line in output.splitlines():
        fields = line.split()
        if fields and fields[0] == package:
            return True
    return False


def check_homebrew_package(  # pylint: disable=too-many-return-statements
    request: HomebrewPackageCheckRequest,
    *,
    command_exists: CommandExists | None = None,
    run_check: RunCheck | None = None,
    package_outdated: PackageOutdated | None = None,
) -> PrerequisiteCheck:
    command_exists = command_exists or process.command_exists
    run_check = run_check or process.run_check
    package_outdated = package_outdated or homebrew_package_outdated

    if request.manager != "homebrew":
        return PrerequisiteCheck(
            name=request.name,
            ok=False,
            message=request.unsupported_manager_message,
            fix=request.unsupported_manager_fix,
            finding_id=request.unsupported_manager_finding_id,
            details=request.details,
        )

    if request.version != "latest":
        return PrerequisiteCheck(
            name=request.name,
            ok=False,
            message=request.unsupported_version_message,
            fix=request.unsupported_version_fix,
            finding_id=request.unsupported_version_finding_id,
            details=request.details,
        )

    if not command_exists("brew"):
        return PrerequisiteCheck(
            name=request.name,
            ok=False,
            message=request.missing_homebrew_message,
            fix=request.missing_homebrew_fix,
            finding_id=request.missing_homebrew_finding_id,
            details=request.details,
        )

    try:
        installed = run_check(
            ["brew", "list", request.package],
            timeout_seconds=request.timeout_seconds,
        )
        outdated = installed and package_outdated(
            request.package,
            timeout_seconds=request.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return PrerequisiteCheck(
            name=request.name,
            ok=False,
            message=request.timeout_message,
            fix=request.timeout_fix,
            status="warn",
            finding_id=request.timeout_finding_id,
            details=request.details,
        )

    if installed:
        if outdated:
            return PrerequisiteCheck(
                name=request.name,
                ok=False,
                message=request.outdated_message,
                fix=request.outdated_fix,
                finding_id=request.package_finding_id,
                details=request.details,
            )
        return PrerequisiteCheck(
            name=request.name,
            ok=True,
            message=request.installed_message,
            fix="",
            finding_id=request.package_finding_id,
            details=request.details,
        )

    return PrerequisiteCheck(
        name=request.name,
        ok=False,
        message=request.missing_package_message,
        fix=request.missing_package_fix,
        finding_id=request.package_finding_id,
        details=request.details,
    )


def check_github_cli_auth(
    request: GitHubCliAuthCheckRequest,
    *,
    command_exists: CommandExists | None = None,
    run_check: RunCheck | None = None,
) -> PrerequisiteCheck:
    command_exists = command_exists or process.command_exists
    run_check = run_check or process.run_check

    if not command_exists("gh"):
        return PrerequisiteCheck(
            name="gh-auth",
            ok=False,
            message="GitHub CLI 'gh' was not found.",
            fix=request.missing_gh_fix,
            finding_id=request.missing_gh_finding_id,
        )

    try:
        ok = run_check(
            list(request.command),
            timeout_seconds=request.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return PrerequisiteCheck(
            name="gh-auth",
            ok=False,
            message=f"GitHub CLI authentication check timed out after {request.timeout_seconds} seconds.",
            fix="Retry 'gh auth status -h github.com' or run 'gh auth login -h github.com'.",
            status="warn",
            finding_id=request.auth_finding_id,
        )

    if ok:
        return PrerequisiteCheck(
            name="gh-auth",
            ok=True,
            message="GitHub CLI authentication is ready.",
            fix="",
            finding_id=request.auth_finding_id,
        )

    return PrerequisiteCheck(
        name="gh-auth",
        ok=False,
        message="GitHub CLI authentication is not ready.",
        fix="gh auth login -h github.com",
        finding_id=request.auth_finding_id,
    )
