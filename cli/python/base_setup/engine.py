from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.config import UserConfig, read_user_config
from base_cli.paths import discover_manifest

from .artifacts import check_artifact
from .artifacts import merge_artifacts
from .artifacts import reconcile_artifacts
from .artifacts import resolve_artifact_definitions
from .checks import ArtifactCheck
from .checks import check_to_doctor_json
from .checks import check_to_json
from .checks import doctor_status
from .checks import print_doctor_finding
from .demo import check_demo
from .delegates import check_brewfile
from .delegates import check_mise
from .delegates import reconcile_brewfile
from .delegates import reconcile_mise
from .errors import ArtifactError
from .health import check_required_env
from .ide import check_ide_extensions
from .ide import check_ide_installs
from .ide import check_ide_settings
from .ide import effective_ide_config
from .ide import ide_preference_warning_checks
from .ide import log_ide_preference_warnings
from .ide import reconcile_ide_extensions
from .ide import reconcile_ide_installs
from .ide import reconcile_ide_settings
from .manifest import BaseManifest, ManifestError, read_manifest


app = base_cli.App(name="base_setup")


@dataclass(frozen=True)
class ManifestAction:
    action: str
    dry_run: bool
    output_format: str


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option("--manifest", help="Path to base_manifest.yaml.")
@base_cli.option("--start-dir", default=".", help="Directory where manifest discovery should start.")
@base_cli.option("--dry-run", is_flag=True, help="Log planned changes without making them.")
@base_cli.option(
    "--action",
    default="setup",
    help="Action to run: setup, bootstrap, check, or doctor. Defaults to setup.",
)
@base_cli.option("--format", "output_format", default="text", help="Output format for check/doctor: text or json.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    project: str | None,
    manifest: str | None,
    start_dir: str,
    dry_run: bool,
    action: str,
    output_format: str,
) -> int:
    manifest_path = Path(manifest).resolve() if manifest else discover_manifest(Path(start_dir))
    if manifest_path is None:
        if project:
            ctx.log.error("No base_manifest.yaml found for project '%s'.", project)
            return 1
        ctx.log.info("No base_manifest.yaml found; skipping project artifact work.")
        return 0

    try:
        base_manifest = read_manifest(manifest_path)
        validate_project_name(base_manifest, project)
        default_manifest = read_default_manifest(ctx)
        return run_manifest_action(ctx, ManifestAction(action, dry_run, output_format), default_manifest, base_manifest)
    except ManifestError as exc:
        ctx.log.error(str(exc))
        return 1
    except ValueError as exc:
        ctx.log.error(str(exc))
        return 1
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1


def run_manifest_action(
    ctx: base_cli.Context,
    manifest_action: ManifestAction,
    default_manifest: BaseManifest,
    base_manifest: BaseManifest,
) -> int:
    action = manifest_action.action
    if action == "setup":
        reconcile_manifest(ctx, default_manifest, base_manifest, dry_run=manifest_action.dry_run)
        return 0
    if action == "bootstrap":
        reconcile_bootstrap_artifacts(ctx, default_manifest, base_manifest, dry_run=manifest_action.dry_run)
        return 0
    if action == "check":
        return check_manifest(ctx, default_manifest, base_manifest, output_format=manifest_action.output_format)
    if action == "doctor":
        return doctor_manifest(default_manifest, base_manifest, output_format=manifest_action.output_format)
    ctx.log.error("Unsupported base_setup action '%s'. Expected setup, bootstrap, check, or doctor.", action)
    return 2


def validate_project_name(manifest: BaseManifest, expected_project: str | None) -> None:
    if expected_project and manifest.project_name != expected_project:
        raise ManifestError(
            f"{manifest.path}: project.name is '{manifest.project_name}', expected '{expected_project}'."
        )


def read_default_manifest(ctx: base_cli.Context) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's default artifact manifest.")
    default_manifest_path = ctx.base_home / "lib" / "base" / "default_manifest.yaml"
    return read_manifest(default_manifest_path)


def reconcile_manifest(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    dry_run: bool,
) -> None:
    ctx.log.info("Reading Base manifest at '%s'.", manifest.path)
    ctx.log.info("Setting up project '%s'.", manifest.project_name)
    user_config = read_user_config()
    log_ide_preference_warnings(ctx, ide_preference_warning_checks(manifest, user_config))
    effective_manifest = effective_manifest_with_user_config(manifest, user_config)

    artifacts = merge_artifacts(default_manifest.artifacts, effective_manifest.artifacts)
    definitions = resolve_artifact_definitions(artifacts)
    if not effective_manifest.artifacts:
        if artifacts:
            ctx.log.info(
                "Project '%s' declares no artifacts; installing Base default artifacts only.",
                effective_manifest.project_name,
            )
        else:
            ctx.log.info("Project '%s' has no artifacts to install.", effective_manifest.project_name)

    reconcile_brewfile(ctx, effective_manifest, dry_run=dry_run)
    reconcile_mise(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_installs(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_extensions(ctx, effective_manifest, dry_run=dry_run)
    reconcile_ide_settings(ctx, effective_manifest, dry_run=dry_run)

    reconcile_artifacts(ctx, artifacts, definitions, effective_manifest.project_name, dry_run=dry_run)

    ctx.log.info("Project '%s' setup is complete.", effective_manifest.project_name)


def reconcile_bootstrap_artifacts(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    dry_run: bool,
) -> None:
    ctx.log.info("Bootstrapping project '%s' Python runtime.", manifest.project_name)

    artifacts = tuple(artifact for artifact in default_manifest.artifacts if artifact.bootstrap)
    definitions = resolve_artifact_definitions(artifacts)
    if not artifacts:
        ctx.log.info("Base default manifest declares no bootstrap artifacts.")
        return

    reconcile_artifacts(ctx, artifacts, definitions, manifest.project_name, dry_run=dry_run)


def check_manifest(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    output_format: str,
) -> int:
    checks = manifest_checks(default_manifest, manifest)
    if output_format == "json":
        print(json.dumps([check_to_json(check) for check in checks], indent=2))
    elif output_format == "text":
        ctx.log.info("Checking project '%s' manifest requirements.", manifest.project_name)
        for check in checks:
            if check.ok:
                ctx.log.info(check.message)
            else:
                ctx.log.warning(check.message)
                if check.fix:
                    ctx.log.warning("Fix: %s", check.fix)
    else:
        ctx.log.error("Unsupported check output format '%s'. Expected text or json.", output_format)
        return 2
    return 0 if all(check.ok or doctor_status(check) == "warn" for check in checks) else 1


def doctor_manifest(default_manifest: BaseManifest, manifest: BaseManifest, output_format: str) -> int:
    checks = manifest_checks(default_manifest, manifest)
    if output_format == "json":
        print(json.dumps([check_to_doctor_json(check) for check in checks], indent=2))
        return min(sum(1 for check in checks if doctor_status(check) == "error"), 125)
    if output_format != "text":
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.")
        return 2

    error_count = 0
    print(f"\nProject doctor: {manifest.project_name}\n")
    for check in checks:
        status = doctor_status(check)
        if status == "error":
            print_doctor_finding("error", check.finding_id, check.name, check.message, check.fix)
            error_count += 1
        else:
            print_doctor_finding(status, check.finding_id, check.name, check.message, check.fix)
    return min(error_count, 125)


def manifest_checks(default_manifest: BaseManifest, manifest: BaseManifest) -> tuple[ArtifactCheck, ...]:
    checks: list[ArtifactCheck] = []
    user_config = read_user_config()
    effective_manifest = effective_manifest_with_user_config(manifest, user_config)
    artifacts = merge_artifacts(default_manifest.artifacts, effective_manifest.artifacts)
    definitions = resolve_artifact_definitions(artifacts)

    checks.extend(ide_preference_warning_checks(manifest, user_config))

    if effective_manifest.brewfile is not None:
        checks.append(check_brewfile(effective_manifest))
    if effective_manifest.mise is not None:
        checks.append(check_mise(effective_manifest))

    checks.extend(check_required_env(effective_manifest))
    checks.extend(check_demo(effective_manifest))
    checks.extend(check_ide_installs(effective_manifest))
    checks.extend(check_ide_extensions(effective_manifest))
    checks.extend(check_ide_settings(effective_manifest))

    for artifact, definition in zip(artifacts, definitions, strict=True):
        checks.append(check_artifact(effective_manifest.project_name, artifact, definition))

    if not checks:
        checks.append(
            ArtifactCheck(
                name="manifest",
                ok=True,
                message=f"Project '{effective_manifest.project_name}' declares no artifacts.",
                fix="",
                finding_id="BASE-P001",
            )
        )
    return tuple(checks)


def effective_manifest_with_user_config(manifest: BaseManifest, user_config: UserConfig) -> BaseManifest:
    return BaseManifest(
        path=manifest.path,
        project_name=manifest.project_name,
        brewfile=manifest.brewfile,
        artifacts=manifest.artifacts,
        ide=effective_ide_config(manifest.ide, user_config),
        mise=manifest.mise,
        test=manifest.test,
        schema_version=manifest.schema_version,
        health=manifest.health,
        commands=manifest.commands,
        activate=manifest.activate,
        demo=manifest.demo,
    )
