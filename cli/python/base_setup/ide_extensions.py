from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import base_cli
from base_cli.ide_schema import IDE_DEFINITIONS
from base_cli.ide_schema import IdeDefinition

from . import process
from .checks import ArtifactCheck
from .errors import ArtifactError
from .manifest import BaseManifest

if TYPE_CHECKING:
    from .ide_diagnostics import IdeDiagnosticSnapshot


def reconcile_ide_extensions(ctx: base_cli.Context, manifest: BaseManifest, dry_run: bool) -> None:
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.extensions:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        if dry_run:
            for extension in ide_config.extensions:
                process.dry_run_command(ctx, [definition.cli, "--install-extension", extension])
            continue
        if not process.command_exists(definition.cli):
            ctx.log.warning(
                "%s CLI '%s' is not on PATH; skipping extension setup.",
                definition.label,
                definition.cli,
            )
            continue
        installed_extensions = list_ide_extensions(definition)
        for extension in ide_config.extensions:
            if extension in installed_extensions:
                ctx.log.debug(
                    "%s extension '%s' is already installed.",
                    definition.label,
                    extension,
                )
                continue
            ctx.log.info("Installing %s extension '%s'.", definition.label, extension)
            process.run_command(ctx, [definition.cli, "--install-extension", extension])


def list_ide_extensions(definition: IdeDefinition) -> set[str]:
    try:
        completed = process.run_capture(
            [definition.cli, "--list-extensions"],
            timeout_seconds=process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ArtifactError(
            f"Unable to list {definition.label} extensions with "
            f"'{definition.cli} --list-extensions': timed out after "
            f"{process.DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
        ) from exc
    if completed.returncode:
        stderr = (completed.stderr or "").strip()
        message = f"Unable to list {definition.label} extensions with '{definition.cli} --list-extensions'."
        if stderr:
            message = f"{message}\n{stderr}"
        raise ArtifactError(message)
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def check_ide_extensions(manifest: BaseManifest) -> list[ArtifactCheck]:
    from .ide_diagnostics import IdeDiagnosticSnapshot

    checks: list[ArtifactCheck] = []
    for ide_name, ide_config in manifest.ide.items():
        if not ide_config.extensions:
            continue
        definition = IDE_DEFINITIONS[ide_name]
        snapshot = IdeDiagnosticSnapshot(definition)
        checks.extend(
            check_ide_extension(manifest.project_name, definition, extension, snapshot=snapshot)
            for extension in ide_config.extensions
        )
    return checks


def check_ide_extension(
    project: str,
    definition: IdeDefinition,
    extension: str,
    snapshot: IdeDiagnosticSnapshot | None = None,
) -> ArtifactCheck:
    from .ide_diagnostics import IdeDiagnosticSnapshot

    snapshot = snapshot or IdeDiagnosticSnapshot(definition)
    if not snapshot.cli_available():
        return ArtifactCheck(
            name=extension,
            ok=False,
            message=(
                f"Cannot check {definition.label} extension '{extension}' "
                f"because CLI '{definition.cli}' is not on PATH."
            ),
            fix=(
                f"Enable the '{definition.cli}' shell command from {definition.label}, "
                f"then run 'basectl setup {project}'."
            ),
            finding_id="BASE-P110",
        )

    try:
        installed_extensions = snapshot.installed_extensions()
    except ArtifactError as exc:
        return ArtifactCheck(
            name=extension,
            ok=False,
            message=str(exc),
            fix=f"basectl setup {project}",
            finding_id="BASE-P111",
        )

    if extension in installed_extensions:
        return ArtifactCheck(
            name=extension,
            ok=True,
            message=f"{definition.label} extension '{extension}' is installed.",
            fix="",
            finding_id="BASE-P112",
        )
    return ArtifactCheck(
        name=extension,
        ok=False,
        message=f"{definition.label} extension '{extension}' is not installed.",
        fix=f"basectl setup {project}",
        finding_id="BASE-P112",
    )
