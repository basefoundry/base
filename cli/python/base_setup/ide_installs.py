from __future__ import annotations

import subprocess

import base_cli
from base_cli.ide_schema import IDE_DEFINITIONS
from base_cli.ide_schema import IdeDefinition

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest


def reconcile_ide_installs(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        definition = IDE_DEFINITIONS[ide_name]
        if not ide_config.install:
            ctx.log.debug("IDE '%s' does not request installation; skipping cask install.", ide_name)
            continue
        reconcile_ide_install(ctx, definition, dry_run=dry_run)


def reconcile_ide_install(ctx: base_cli.Context, definition: IdeDefinition, dry_run: bool) -> None:
    command = ["brew", "install", "--cask", definition.cask]
    if dry_run:
        process.dry_run_command(ctx, command)
        return

    if not process.command_exists("brew"):
        raise ArtifactError(f"Homebrew is required to install {definition.label}.")

    if process.run_check(["brew", "list", "--cask", definition.cask]):
        ctx.log.info("%s is already installed via Homebrew cask '%s'.", definition.label, definition.cask)
    else:
        ctx.log.info("Installing %s via Homebrew cask '%s'.", definition.label, definition.cask)
        process.run_command(ctx, command)

    if process.command_exists(definition.cli):
        ctx.log.info("%s CLI '%s' is available on PATH.", definition.label, definition.cli)
    else:
        ctx.log.warning(
            "%s is installed, but CLI '%s' is not on PATH. Enable the IDE shell command before extension setup.",
            definition.label,
            definition.cli,
        )


def check_ide_installs(manifest: BaseManifest) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        definition = IDE_DEFINITIONS[ide_name]
        if ide_config.install:
            checks.append(check_ide_install(manifest.project_name, definition))
    return checks


def check_ide_install(project: str, definition: IdeDefinition) -> ArtifactCheck:
    if not process.command_exists("brew"):
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=f"Homebrew is required to check {definition.label} installation.",
            fix="basectl setup",
            finding_id="BASE-P130",
        )

    try:
        cask_installed = process.run_check(
            ["brew", "list", "--cask", definition.cask],
            timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=(
                f"Homebrew cask check for {definition.label} timed out after "
                f"{process.DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
            ),
            fix=f"Retry 'basectl doctor {project}' or inspect Homebrew with 'brew doctor'.",
            status="warn",
            finding_id="BASE-P131",
        )
    cli_available = process.command_exists(definition.cli)

    if cask_installed and cli_available:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=True,
            message=f"{definition.label} is installed and CLI '{definition.cli}' is on PATH.",
            fix="",
            finding_id="BASE-P131",
        )
    if not cask_installed:
        return ArtifactCheck(
            name=f"{definition.label} app",
            ok=False,
            message=f"{definition.label} is not installed via Homebrew cask '{definition.cask}'.",
            fix=f"basectl setup {project}",
            finding_id="BASE-P131",
        )
    return ArtifactCheck(
        name=f"{definition.label} CLI",
        ok=False,
        message=f"{definition.label} is installed, but CLI '{definition.cli}' is not on PATH.",
        fix=f"Enable the '{definition.cli}' shell command from {definition.label}.",
        finding_id="BASE-P132",
    )
