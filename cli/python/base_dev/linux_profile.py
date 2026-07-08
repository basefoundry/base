from __future__ import annotations

import os
from dataclasses import dataclass

import base_cli
from base_setup import process
from base_setup.errors import ArtifactError
from base_setup.manifest_model import ArtifactRequest
from base_setup.process import command_exists

from .checks import DevCheck


@dataclass(frozen=True)
class LinuxDebianDevTool:
    apt_package: str
    command: str


LINUX_DEBIAN_DEV_TOOLS = {
    "bats-core": LinuxDebianDevTool(apt_package="bats", command="bats"),
    "shellcheck": LinuxDebianDevTool(apt_package="shellcheck", command="shellcheck"),
}

GITHUB_CLI_LINUX_INSTALL_URL = "https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian"


def profile_setup_fix(profile: str) -> str:
    return f"basectl setup --profile {profile}"


def github_cli_linux_install_fix(rerun_command: str) -> str:
    if rerun_command.startswith("basectl setup"):
        return rerun_command
    return "basectl setup --profile dev"


def github_cli_linux_install_guidance() -> str:
    return (
        "GitHub CLI 'gh' is installed by basectl setup's Ubuntu/Debian platform layer. "
        "Base configures GitHub CLI's official Debian/Ubuntu apt repository before installing 'gh': "
        f"{GITHUB_CLI_LINUX_INSTALL_URL}."
    )


def current_base_platform() -> str:
    return os.environ.get("BASE_PLATFORM", "")


def linux_debian_github_cli_artifact(artifact: ArtifactRequest, profile: str) -> bool:
    return (
        profile == "dev"
        and current_base_platform() == "linux-debian"
        and artifact.artifact_type == "tool"
        and artifact.name == "gh"
    )


def linux_debian_dev_tool(artifact: ArtifactRequest, profile: str) -> LinuxDebianDevTool | None:
    if profile != "dev" or current_base_platform() != "linux-debian":
        return None
    if artifact.artifact_type != "tool":
        return None
    return LINUX_DEBIAN_DEV_TOOLS.get(artifact.name)


def check_linux_debian_github_cli_artifact(
    artifact: ArtifactRequest,
    profile: str = "dev",
) -> DevCheck:
    if artifact.version != "latest":
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=f"Artifact '{artifact.name}' uses unsupported developer prerequisite version '{artifact.version}'.",
            fix="Use version 'latest' for GitHub CLI developer prerequisite checks.",
            finding_id="BASE-D102",
        )

    if command_exists("gh"):
        return DevCheck(
            name=artifact.name,
            ok=True,
            message="GitHub CLI 'gh' is installed; authentication remains user-owned.",
            fix="",
            finding_id="BASE-D107",
        )
    return DevCheck(
        name=artifact.name,
        ok=False,
        message=(
            "GitHub CLI 'gh' is not installed; Base setup installs it from GitHub CLI's official "
            "Debian/Ubuntu apt repository."
        ),
        fix=profile_setup_fix(profile),
        finding_id="BASE-D107",
    )


def check_linux_debian_apt_artifact(
    artifact: ArtifactRequest,
    tool: LinuxDebianDevTool,
    profile: str = "dev",
) -> DevCheck:
    if artifact.version != "latest":
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=f"Artifact '{artifact.name}' uses unsupported developer prerequisite version '{artifact.version}'.",
            fix="Use version 'latest' for apt-backed developer prerequisites.",
            finding_id="BASE-D102",
        )

    if command_exists(tool.command):
        return DevCheck(
            name=artifact.name,
            ok=True,
            message=f"Artifact '{artifact.name}' is installed via apt package '{tool.apt_package}'.",
            fix="",
            finding_id="BASE-D104",
        )
    return DevCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact '{artifact.name}' is not installed via apt package '{tool.apt_package}'.",
        fix=profile_setup_fix(profile),
        finding_id="BASE-D104",
    )


def reconcile_linux_debian_github_cli_artifact(
    ctx: base_cli.Context,
    artifact: ArtifactRequest,
) -> None:
    if artifact.version != "latest":
        raise ArtifactError(
            f"GitHub CLI developer prerequisite '{artifact.name}' specifies version '{artifact.version}', "
            "but Base only supports GitHub CLI developer prerequisite version 'latest' right now."
        )

    if command_exists("gh"):
        ctx.log.info("GitHub CLI 'gh' is already installed; authentication remains user-owned.")
        return

    ctx.log.info(github_cli_linux_install_guidance())


def reconcile_linux_debian_apt_artifact(
    ctx: base_cli.Context,
    artifact: ArtifactRequest,
    tool: LinuxDebianDevTool,
    profile: str,
    dry_run: bool,
) -> None:
    if artifact.version != "latest":
        raise ArtifactError(
            f"Apt-backed developer prerequisite '{artifact.name}' specifies version '{artifact.version}', "
            "but Base only supports apt-backed developer prerequisite version 'latest' right now."
        )

    install_command = ["sudo", "apt-get", "install", "-y", tool.apt_package]
    if command_exists(tool.command):
        ctx.log.info(
            "Artifact '%s' is already installed via apt package '%s'.",
            artifact.name,
            tool.apt_package,
        )
        return

    if dry_run:
        process.dry_run_command(ctx, install_command)
        return

    if not command_exists("apt-get"):
        raise ArtifactError(
            f"apt-get is required to install developer prerequisite '{artifact.name}' "
            f"for profile '{profile}'."
        )

    ctx.log.info(
        "Installing artifact '%s' via apt package '%s' (%s).",
        artifact.name,
        tool.apt_package,
        artifact.version,
    )
    process.run_command(ctx, install_command)
