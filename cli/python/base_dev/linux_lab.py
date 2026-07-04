from __future__ import annotations

import shutil
import subprocess

import base_cli
from base_setup import process
from base_setup.errors import ArtifactError
from base_setup.platform_policy import current_base_platform
from base_setup.platform_policy import platform_label
from base_setup.process import DIAGNOSTIC_TIMEOUT_SECONDS

from .checks import DevCheck


MULTIPASS_INSTALL_COMMAND = ("brew", "install", "--cask", "multipass")
LINUX_LAB_FINDING_ID = "BASE-D108"


def setup_linux_lab(ctx: base_cli.Context, dry_run: bool) -> int:
    ctx.log.info("Setting up Base 'linux-lab' prerequisites.")
    check = check_multipass()
    if check.ok:
        ctx.log.info("%s", check.message)
        ctx.log.info("Base 'linux-lab' prerequisite setup is complete.")
        return base_cli.ExitCode.SUCCESS

    ctx.log.info(
        "Multipass creates host-managed Ubuntu VMs; Base does not create VM instances during setup."
    )
    if current_base_platform() not in {"", "macos"}:
        ctx.log.error(
            "The 'linux-lab' setup profile installs Multipass via Homebrew cask and is supported "
            "only on macOS hosts. Current BASE_PLATFORM='%s'. Install Multipass manually from "
            "https://canonical.com/multipass/install if this host should manage lab VMs.",
            platform_label(),
        )
        return base_cli.ExitCode.FAILURE
    try:
        if dry_run:
            process.dry_run_command(ctx, list(MULTIPASS_INSTALL_COMMAND))
            ctx.log.info("Base 'linux-lab' prerequisite setup dry-run is complete.")
            return base_cli.ExitCode.SUCCESS
        else:
            if not process.command_exists("brew"):
                raise ArtifactError(
                    "Homebrew is required to install Multipass for the 'linux-lab' profile. "
                    "Install Multipass from https://canonical.com/multipass/install or run "
                    "'brew install --cask multipass' after Homebrew is available."
                )
            ctx.log.info("Installing Multipass via Homebrew cask.")
            process.run_command(ctx, list(MULTIPASS_INSTALL_COMMAND))
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    ctx.log.info("Base 'linux-lab' prerequisite setup is complete.")
    return base_cli.ExitCode.SUCCESS


def linux_lab_checks() -> tuple[DevCheck, ...]:
    return (check_multipass(),)


def check_multipass() -> DevCheck:
    executable_path = shutil.which("multipass")
    if executable_path is None:
        return DevCheck(
            name="multipass",
            ok=False,
            message="Multipass 'multipass' was not found.",
            fix="basectl setup --profile linux-lab",
            finding_id=LINUX_LAB_FINDING_ID,
        )

    command = [executable_path, "version"]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=DIAGNOSTIC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return DevCheck(
            name="multipass",
            ok=False,
            message=f"Multipass version check timed out after {DIAGNOSTIC_TIMEOUT_SECONDS} seconds.",
            fix="Retry 'multipass version' or run 'basectl setup --profile linux-lab'.",
            status="warn",
            finding_id=LINUX_LAB_FINDING_ID,
        )

    if completed.returncode != 0:
        detail = summarize_command_output(completed.stderr) or summarize_command_output(completed.stdout)
        message = f"Multipass version check failed with exit {completed.returncode}."
        if detail:
            message = f"{message} {detail}"
        return DevCheck(
            name="multipass",
            ok=False,
            message=message,
            fix="basectl setup --profile linux-lab",
            finding_id=LINUX_LAB_FINDING_ID,
        )

    version = (
        summarize_command_output(completed.stdout)
        or summarize_command_output(completed.stderr)
        or "version unknown"
    )
    return DevCheck(
        name="multipass",
        ok=True,
        message=f"Multipass is already installed at '{executable_path}' ({version}).",
        fix="",
        finding_id=LINUX_LAB_FINDING_ID,
    )


def summarize_command_output(output: str | None) -> str:
    return " ".join((output or "").split())
