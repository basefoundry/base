from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.config import UserConfig
from base_cli.paths import discover_manifest
from base_devcontainer.export import DevcontainerExportError
from base_devcontainer.export import build_devcontainer_export
from base_devcontainer.export import dumps_export_json
from base_devcontainer.export import print_devcontainer_export_text
from base_devcontainer.export import write_devcontainer_export
from base_devenv.report import build_devenv_report
from base_devenv.report import dumps_devenv_report_json
from base_devenv.report import print_devenv_report_text

from .checks import check_to_json
from .checks import checks_payload_to_json
from .checks import checks_status
from .checks import doctor_status
from .checks import print_doctor_finding
from .errors import ArtifactError
from .manifest import BaseManifest, ManifestError, read_manifest
from .manifest_checks import empty_user_config  # pylint: disable=unused-import
from .manifest_checks import IDE_EXTENSION_PROFILE  # pylint: disable=unused-import
from .manifest_checks import manifest_checks
from .manifest_checks import pre_venv_manifest_checks
from .manifest_checks import setup_profile_enabled  # pylint: disable=unused-import
from .project_routing import route_for_manifest
from .project_routing import route_to_text
from .setup_reconcile import effective_manifest_with_user_config  # pylint: disable=unused-import
from .setup_reconcile import project_runtime_argument  # pylint: disable=unused-import
from .setup_reconcile import reconcile_bootstrap_artifacts
from .setup_reconcile import reconcile_manifest


app = base_cli.App(name="base_setup")


@dataclass(frozen=True)
class ManifestAction:
    action: str
    dry_run: bool
    output_format: str
    write: bool = False
    remote_network: bool = False


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option("--manifest", help="Path to base_manifest.yaml.")
@base_cli.option("--start-dir", default=".", help="Directory where manifest discovery should start.")
@base_cli.option("--dry-run", is_flag=True, help="Log planned changes without making them.")
@base_cli.option("--write", is_flag=True, help="Write actions that default to dry-run output.")
@base_cli.option(
    "--action",
    default="setup",
    help="Action to run: setup, bootstrap, check, doctor, or route. Defaults to setup.",
)
@base_cli.option("--format", "output_format", default="text", help="Output format for check/doctor: text or json.")
@base_cli.option(
    "--remote-network",
    is_flag=True,
    help="Opt in to bounded network reachability diagnostics for project Git origin.",
)
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    project: str | None,
    manifest: str | None,
    start_dir: str,
    dry_run: bool,
    write: bool,
    action: str,
    output_format: str,
    remote_network: bool,
) -> int:
    manifest_path = Path(manifest).resolve() if manifest else discover_manifest(Path(start_dir))
    if manifest_path is None:
        if project:
            ctx.log.error("No base_manifest.yaml found for project '%s'.", project)
            return base_cli.ExitCode.FAILURE
        ctx.log.info("No base_manifest.yaml found; skipping project artifact work.")
        return base_cli.ExitCode.SUCCESS

    try:
        base_manifest = read_manifest(manifest_path)
        validate_project_name(base_manifest, project)
        manifest_action = ManifestAction(action, dry_run, output_format, write, remote_network)
        if action == "route":
            status = route_manifest(ctx, manifest_action, base_manifest)
        elif action == "devcontainer":
            status = devcontainer_manifest(ctx, manifest_action, base_manifest)
        elif action == "devenv-report":
            status = devenv_report_manifest(ctx, manifest_action, base_manifest)
        else:
            default_manifest = read_default_manifest(ctx)
            status = run_manifest_action(
                ctx,
                manifest_action,
                default_manifest,
                base_manifest,
            )
    except ManifestError as exc:
        ctx.log.error(str(exc))
        status = base_cli.ExitCode.FAILURE
    except ValueError as exc:
        ctx.log.error(str(exc))
        status = base_cli.ExitCode.FAILURE
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        status = base_cli.ExitCode.FAILURE
    except DevcontainerExportError as exc:
        ctx.log.error(str(exc))
        status = base_cli.ExitCode.FAILURE
    return status


def run_manifest_action(
    ctx: base_cli.Context,
    manifest_action: ManifestAction,
    default_manifest: BaseManifest,
    base_manifest: BaseManifest,
) -> int:
    action = manifest_action.action
    if action == "setup":
        reconcile_manifest(ctx, default_manifest, base_manifest, dry_run=manifest_action.dry_run)
        status = 0
    elif action == "bootstrap":
        reconcile_bootstrap_artifacts(ctx, default_manifest, base_manifest, dry_run=manifest_action.dry_run)
        status = 0
    elif action == "check":
        status = check_manifest(
            ctx,
            default_manifest,
            base_manifest,
            output_format=manifest_action.output_format,
            remote_network=manifest_action.remote_network,
        )
    elif action == "doctor":
        status = doctor_manifest(
            default_manifest,
            base_manifest,
            output_format=manifest_action.output_format,
            remote_network=manifest_action.remote_network,
            user_config=ctx.user_config,
        )
    elif action == "precheck":
        status = check_pre_venv_manifest(
            ctx,
            base_manifest,
            output_format=manifest_action.output_format,
            remote_network=manifest_action.remote_network,
        )
    elif action == "predoctor":
        status = doctor_pre_venv_manifest(
            base_manifest,
            output_format=manifest_action.output_format,
            remote_network=manifest_action.remote_network,
        )
    else:
        ctx.log.error(
            "Unsupported base_setup action '%s'. Expected setup, bootstrap, check, doctor, "
            "route, devcontainer, devenv-report, precheck, or predoctor.",
            action,
        )
        status = base_cli.ExitCode.USAGE_ERROR
    return status


def devcontainer_manifest(
    ctx: base_cli.Context,
    manifest_action: ManifestAction,
    manifest: BaseManifest,
) -> int:
    if manifest_action.output_format not in ("text", "json"):
        ctx.log.error(
            "Unsupported devcontainer output format '%s'. Expected text or json.",
            manifest_action.output_format,
        )
        return base_cli.ExitCode.USAGE_ERROR

    export = build_devcontainer_export(manifest, write=manifest_action.write)
    if manifest_action.write:
        write_devcontainer_export(export)
        export = build_devcontainer_export(manifest, write=True)

    if manifest_action.output_format == "json":
        print(dumps_export_json(export), end="")
    else:
        print_devcontainer_export_text(export)
    return base_cli.ExitCode.SUCCESS


def devenv_report_manifest(
    ctx: base_cli.Context,
    manifest_action: ManifestAction,
    manifest: BaseManifest,
) -> int:
    if manifest_action.output_format not in ("text", "json"):
        ctx.log.error(
            "Unsupported devenv-report output format '%s'. Expected text or json.",
            manifest_action.output_format,
        )
        return base_cli.ExitCode.USAGE_ERROR

    report = build_devenv_report(manifest)
    if manifest_action.output_format == "json":
        print(dumps_devenv_report_json(report), end="")
    else:
        print_devenv_report_text(report)
    return base_cli.ExitCode.SUCCESS


def route_manifest(
    ctx: base_cli.Context,
    manifest_action: ManifestAction,
    manifest: BaseManifest,
) -> int:
    try:
        print(route_to_text(route_for_manifest(manifest), manifest_action.output_format))
    except ValueError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR
    return base_cli.ExitCode.SUCCESS


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


def check_manifest(
    ctx: base_cli.Context,
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    output_format: str,
    remote_network: bool = False,
) -> int:
    checks = manifest_checks(
        default_manifest,
        manifest,
        remote_network=remote_network,
        user_config=ctx.user_config,
    )
    if output_format == "json":
        print(json.dumps(checks_payload_to_json(checks, project=manifest.project_name), indent=2))
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
        return base_cli.ExitCode.USAGE_ERROR
    if all(check.ok or doctor_status(check) == "warn" for check in checks):
        return base_cli.ExitCode.SUCCESS
    return base_cli.ExitCode.FAILURE


def check_pre_venv_manifest(
    ctx: base_cli.Context,
    manifest: BaseManifest,
    output_format: str,
    remote_network: bool = False,
) -> int:
    checks = pre_venv_manifest_checks(manifest, remote_network=remote_network)
    if output_format == "json":
        print(json.dumps([check_to_json(check) for check in checks], separators=(",", ":")))
    elif output_format == "text":
        for check in checks:
            if check.ok:
                ctx.log.info(check.message)
            else:
                ctx.log.warning(check.message)
                if check.fix:
                    ctx.log.warning("Fix: %s", check.fix)
    else:
        ctx.log.error("Unsupported check output format '%s'. Expected text or json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    if all(check.ok or doctor_status(check) == "warn" for check in checks):
        return base_cli.ExitCode.SUCCESS
    return base_cli.ExitCode.FAILURE


def doctor_manifest(
    default_manifest: BaseManifest,
    manifest: BaseManifest,
    output_format: str,
    remote_network: bool = False,
    *,
    user_config: UserConfig | None = None,
) -> int:
    if output_format not in {"json", "text"}:
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR

    checks = manifest_checks(
        default_manifest,
        manifest,
        remote_network=remote_network,
        user_config=user_config,
    )
    if output_format == "json":
        print(json.dumps([check_to_json(check) for check in checks], indent=2))
        return min(sum(1 for check in checks if doctor_status(check) == "error"), 125)

    error_count = 0
    output_stream = sys.stderr if checks_status(checks) != "ok" else sys.stdout
    print(f"\nProject doctor: {manifest.project_name}\n", file=output_stream)
    for check in checks:
        status = doctor_status(check)
        if status == "error":
            print_doctor_finding("error", check.finding_id, check.name, check.message, check.fix)
            error_count += 1
        else:
            print_doctor_finding(status, check.finding_id, check.name, check.message, check.fix)
    return min(error_count, 125)


def doctor_pre_venv_manifest(
    manifest: BaseManifest,
    output_format: str,
    remote_network: bool = False,
) -> int:
    if output_format not in {"json", "text"}:
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR

    checks = pre_venv_manifest_checks(manifest, remote_network=remote_network)
    if output_format == "json":
        print(json.dumps([check_to_json(check) for check in checks], separators=(",", ":")))
        return min(sum(1 for check in checks if doctor_status(check) == "error"), 125)

    error_count = 0
    for check in checks:
        status = doctor_status(check)
        print_doctor_finding(status, check.finding_id, check.name, check.message, check.fix)
        if status == "error":
            error_count += 1
    return min(error_count, 125)
