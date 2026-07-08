from __future__ import annotations

import json
import sys
from pathlib import Path

import base_cli
from base_setup.artifacts import reconcile_artifact
from base_setup.artifacts import resolve_artifact_definitions  # pylint: disable=unused-import
from base_setup.checks import DIAGNOSTIC_JSON_SCHEMA_VERSION
from base_setup.errors import ArtifactError
from base_setup.manifest import read_manifest  # pylint: disable=unused-import
from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import ArtifactRequest, BaseManifest
from base_setup.prerequisites import GitHubCliAuthCheckRequest
from base_setup.prerequisites import HomebrewPackageCheckRequest
from base_setup.prerequisites import PrerequisiteCheck
from base_setup.prerequisites import check_github_cli_auth as check_github_cli_auth_prerequisite
from base_setup.prerequisites import check_homebrew_package
from base_setup.prerequisites import homebrew_package_outdated
from base_setup.process import DIAGNOSTIC_TIMEOUT_SECONDS, command_exists, run_check
from base_setup.registry import ArtifactDefinition

from .ai_tools import ai_tool_checks, setup_ai_tools
from .checks import DevCheck
from .checks import check_to_doctor_json
from .checks import check_to_json
from .checks import checks_status
from .checks import doctor_status
from .checks import print_doctor_finding
from .linux_lab import linux_lab_checks
from .linux_lab import setup_linux_lab
from .linux_profile import check_linux_debian_apt_artifact
from .linux_profile import check_linux_debian_github_cli_artifact
from .linux_profile import current_base_platform
from .linux_profile import github_cli_linux_install_fix
from .linux_profile import linux_debian_dev_tool
from .linux_profile import linux_debian_github_cli_artifact
from .linux_profile import LinuxDebianDevTool  # pylint: disable=unused-import
from .linux_profile import profile_setup_fix
from .linux_profile import reconcile_linux_debian_apt_artifact
from .linux_profile import reconcile_linux_debian_github_cli_artifact
from .profiles import SUPPORTED_PROFILES  # pylint: disable=unused-import
from .profiles import ProfileError
from .profiles import ProfileManifest
from .profiles import ProfileRuntime
from .profiles import dev_manifest_path  # pylint: disable=unused-import
from .profiles import normalize_profiles
from .profiles import profile_manifest_path
from .profiles import read_dev_manifest  # pylint: disable=unused-import
from .profiles import read_profile_manifest  # pylint: disable=unused-import
from .profiles import read_profile_manifests


app = base_cli.App(name="base_dev")


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("action", required=True)
@base_cli.option("--dry-run", is_flag=True, help="Log planned setup changes without making them.")
@base_cli.option("--format", "output_format", default="text", help="Output format for check/doctor: text or json.")
@base_cli.option(
    "--profile",
    "profiles",
    multiple=True,
    help="Comma-separated prerequisite profiles to include. Defaults to dev.",
)
def run(ctx: base_cli.Context, action: str, dry_run: bool, output_format: str, profiles: tuple[str, ...]) -> int:
    try:
        normalized_profiles = normalize_profiles(profiles)
        profile_manifests = read_profile_manifests(ctx, normalized_profiles)
    except (ManifestError, ArtifactError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE
    except ProfileError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    if action == "setup":
        return setup_profiles(ctx, normalized_profiles, profile_manifests, dry_run=dry_run)
    if action == "check":
        return check_profiles(ctx, normalized_profiles, profile_manifests, output_format=output_format)
    if action == "doctor":
        return doctor_profiles(normalized_profiles, profile_manifests, output_format=output_format)

    ctx.log.error("Unsupported base_dev action '%s'. Expected setup, check, or doctor.", action)
    return base_cli.ExitCode.USAGE_ERROR


def setup_profile_manifests(
    ctx: base_cli.Context,
    profile_manifests: tuple[ProfileManifest, ...],
    dry_run: bool,
) -> int:
    for profile_manifest in profile_manifests:
        status = setup_profile_artifacts(
            ctx,
            profile_manifest.name,
            profile_manifest.manifest,
            profile_manifest.definitions,
            dry_run=dry_run,
        )
        if status != base_cli.ExitCode.SUCCESS:
            return status
    return base_cli.ExitCode.SUCCESS


def setup_profiles(
    ctx: base_cli.Context,
    profiles: tuple[str, ...],
    profile_manifests: tuple[ProfileManifest, ...],
    dry_run: bool,
) -> int:
    profile_manifest_by_name = {
        profile_manifest.name: profile_manifest for profile_manifest in profile_manifests
    }
    for profile in profiles:
        if profile == "ai":
            status = setup_ai_tools(ctx, dry_run=dry_run)
        elif profile == "linux-lab":
            status = setup_linux_lab(ctx, dry_run=dry_run)
        else:
            profile_manifest = profile_manifest_by_name[profile]
            status = setup_profile_artifacts(
                ctx,
                profile_manifest.name,
                profile_manifest.manifest,
                profile_manifest.definitions,
                dry_run=dry_run,
            )
        if status != base_cli.ExitCode.SUCCESS:
            return status
    return base_cli.ExitCode.SUCCESS


def setup_dev_artifacts(
    ctx: base_cli.Context,
    manifest: BaseManifest,
    definitions: tuple[ArtifactDefinition, ...],
    dry_run: bool,
) -> int:
    return setup_profile_artifacts(ctx, "dev", manifest, definitions, dry_run=dry_run)


def setup_profile_artifacts(
    ctx: base_cli.Context,
    profile: str,
    manifest: BaseManifest,
    definitions: tuple[ArtifactDefinition, ...],
    dry_run: bool,
) -> int:
    if profile == "dev":
        ctx.log.info("Reading Base developer prerequisite manifest at '%s'.", manifest.path)
        ctx.log.info("Setting up Base developer prerequisites.")
    else:
        ctx.log.info("Reading Base '%s' prerequisite manifest at '%s'.", profile, manifest.path)
        ctx.log.info("Setting up Base '%s' prerequisites.", profile)

    try:
        runtime = ProfileRuntime(profile=profile, project=manifest.project_name)
        for artifact, definition in zip(manifest.artifacts, definitions, strict=True):
            reconcile_profile_artifact(
                ctx,
                artifact,
                definition,
                runtime,
                dry_run=dry_run,
            )
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if profile == "dev":
        ctx.log.info("Base developer prerequisite setup is complete.")
    else:
        ctx.log.info("Base '%s' prerequisite setup is complete.", profile)
    return base_cli.ExitCode.SUCCESS


def check_profile_manifests(
    ctx: base_cli.Context,
    profile_manifests: tuple[ProfileManifest, ...],
    output_format: str,
) -> int:
    checks = tuple(
        check
        for profile_manifest in profile_manifests
        for check in dev_checks(
            profile_manifest.manifest.artifacts,
            profile_manifest.definitions,
            profile=profile_manifest.name,
        )
    )
    return print_check_results(
        ctx,
        checks,
        output_format=output_format,
        profiles=tuple(profile_manifest.name for profile_manifest in profile_manifests),
    )


def check_profiles(
    ctx: base_cli.Context,
    profiles: tuple[str, ...],
    profile_manifests: tuple[ProfileManifest, ...],
    output_format: str,
) -> int:
    checks = collect_profile_checks(profiles, profile_manifests)
    return print_check_results(ctx, checks, output_format=output_format, profiles=profiles)


def check_dev_artifacts(
    ctx: base_cli.Context,
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    output_format: str,
) -> int:
    checks = dev_checks(artifacts, definitions, profile="dev")
    return print_check_results(ctx, checks, output_format=output_format, profiles=("dev",))


def print_check_results(
    ctx: base_cli.Context,
    checks: tuple[DevCheck, ...],
    output_format: str,
    profiles: tuple[str, ...],
) -> int:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "schema_version": DIAGNOSTIC_JSON_SCHEMA_VERSION,
                    "status": checks_status(checks),
                    "profiles": list(profiles),
                    "checks": [check_to_json(check) for check in checks],
                },
                indent=2,
            )
        )
    elif output_format == "text":
        for check in checks:
            if check.ok:
                ctx.log.info(check.message)
            else:
                ctx.log.warning(check.message)
    else:
        ctx.log.error("Unsupported check output format '%s'. Expected text or json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR

    if all(doctor_status(check) != "error" for check in checks):
        return base_cli.ExitCode.SUCCESS
    return base_cli.ExitCode.FAILURE


def doctor_profile_manifests(
    profile_manifests: tuple[ProfileManifest, ...],
    output_format: str,
) -> int:
    checks = tuple(
        check
        for profile_manifest in profile_manifests
        for check in dev_checks(
            profile_manifest.manifest.artifacts,
            profile_manifest.definitions,
            profile=profile_manifest.name,
        )
    )
    return print_doctor_results(checks, output_format=output_format)


def doctor_profiles(
    profiles: tuple[str, ...],
    profile_manifests: tuple[ProfileManifest, ...],
    output_format: str,
) -> int:
    checks = collect_profile_checks(profiles, profile_manifests)
    return print_doctor_results(checks, output_format=output_format)


def doctor_dev_artifacts(
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    output_format: str,
) -> int:
    checks = dev_checks(artifacts, definitions, profile="dev")
    return print_doctor_results(checks, output_format=output_format)


def print_doctor_results(checks: tuple[DevCheck, ...], output_format: str) -> int:
    if output_format == "json":
        print(json.dumps([check_to_doctor_json(check) for check in checks], indent=2))
        return min(sum(1 for check in checks if doctor_status(check) == "error"), 125)
    if output_format != "text":
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR

    error_count = 0
    for check in checks:
        status = doctor_status(check)
        if status == "error":
            print_doctor_finding("error", check.finding_id, check.name, check.message, check.fix)
            error_count += 1
        else:
            print_doctor_finding(status, check.finding_id, check.name, check.message, check.fix)
    return min(error_count, 125)


def collect_profile_checks(
    profiles: tuple[str, ...],
    profile_manifests: tuple[ProfileManifest, ...],
) -> tuple[DevCheck, ...]:
    profile_manifest_by_name = {
        profile_manifest.name: profile_manifest for profile_manifest in profile_manifests
    }
    checks: list[DevCheck] = []
    for profile in profiles:
        if profile == "ai":
            checks.extend(ai_tool_checks())
            continue
        if profile == "linux-lab":
            checks.extend(linux_lab_checks())
            continue
        profile_manifest = profile_manifest_by_name[profile]
        checks.extend(
            dev_checks(
                profile_manifest.manifest.artifacts,
                profile_manifest.definitions,
                profile=profile_manifest.name,
            )
        )
    return tuple(checks)


def dev_checks(
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    profile: str = "dev",
) -> tuple[DevCheck, ...]:
    checks: list[DevCheck] = []
    for artifact, definition in zip(artifacts, definitions):
        check = check_profile_artifact(artifact, definition, profile=profile)
        checks.append(check)
        if artifact.name == "gh" and check.ok:
            checks.append(check_github_cli_auth())
    return tuple(checks)


def check_profile_artifact(
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
    profile: str = "dev",
) -> DevCheck:
    if linux_debian_github_cli_artifact(artifact, profile):
        return check_linux_debian_github_cli_artifact(artifact, profile=profile)
    linux_debian_tool = linux_debian_dev_tool(artifact, profile)
    if linux_debian_tool is not None:
        return check_linux_debian_apt_artifact(artifact, linux_debian_tool, profile=profile)
    return check_homebrew_artifact(artifact, definition, profile=profile)


def check_homebrew_artifact(  # pylint: disable=too-many-return-statements
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
    profile: str = "dev",
) -> DevCheck:
    request = HomebrewPackageCheckRequest(
        name=artifact.name,
        manager=definition.manager,
        version=artifact.version,
        package=definition.package,
        timeout_seconds=DIAGNOSTIC_TIMEOUT_SECONDS,
        unsupported_manager_message=(
            f"Artifact '{artifact.name}' uses unsupported developer prerequisite manager '{definition.manager}'."
        ),
        unsupported_manager_fix=(
            f"Update {profile_manifest_path(Path('lib/base'), profile).name} to use a Homebrew-managed tool."
        ),
        unsupported_manager_finding_id="BASE-D101",
        unsupported_version_message=(
            f"Artifact '{artifact.name}' uses unsupported developer prerequisite version '{artifact.version}'."
        ),
        unsupported_version_fix="Use version 'latest' for Homebrew-managed developer prerequisites.",
        unsupported_version_finding_id="BASE-D102",
        missing_homebrew_message=f"Homebrew is required to check developer prerequisite '{artifact.name}'.",
        missing_homebrew_fix="basectl setup",
        missing_homebrew_finding_id="BASE-D103",
        timeout_message=(
            f"Homebrew check for artifact '{artifact.name}' timed out after "
            f"{DIAGNOSTIC_TIMEOUT_SECONDS} seconds."
        ),
        timeout_fix=f"Retry 'basectl doctor --profile {profile}' or inspect Homebrew with 'brew doctor'.",
        timeout_finding_id="BASE-D104",
        outdated_message=f"Artifact '{artifact.name}' is outdated via Homebrew package '{definition.package}'.",
        outdated_fix=profile_setup_fix(profile),
        package_finding_id="BASE-D104",
        installed_message=(
            f"Artifact '{artifact.name}' is installed via Homebrew package "
            f"'{definition.package}' and is current."
        ),
        missing_package_message=(
            f"Artifact '{artifact.name}' is not installed via Homebrew package '{definition.package}'."
        ),
        missing_package_fix=profile_setup_fix(profile),
    )
    return dev_check_from_prerequisite(
        check_homebrew_package(
            request,
            command_exists=command_exists,
            run_check=run_check,
            package_outdated=homebrew_package_outdated,
        )
    )


def dev_check_from_prerequisite(check: PrerequisiteCheck) -> DevCheck:
    return DevCheck(
        name=check.name,
        ok=check.ok,
        message=check.message,
        fix=check.fix,
        status=check.status,
        finding_id=check.finding_id,
    )


def reconcile_profile_artifact(
    ctx: base_cli.Context,
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
    runtime: ProfileRuntime,
    dry_run: bool,
) -> None:
    if linux_debian_github_cli_artifact(artifact, runtime.profile):
        reconcile_linux_debian_github_cli_artifact(ctx, artifact)
        return
    linux_debian_tool = linux_debian_dev_tool(artifact, runtime.profile)
    if linux_debian_tool is not None:
        reconcile_linux_debian_apt_artifact(ctx, artifact, linux_debian_tool, profile=runtime.profile, dry_run=dry_run)
        return
    reconcile_artifact(ctx, definition, artifact.version, runtime.project, dry_run=dry_run)


def check_github_cli_auth() -> DevCheck:
    missing_gh_fix = (
        github_cli_linux_install_fix("basectl check --profile dev")
        if current_base_platform() == "linux-debian"
        else "basectl setup --profile dev"
    )
    request = GitHubCliAuthCheckRequest(
        timeout_seconds=DIAGNOSTIC_TIMEOUT_SECONDS,
        missing_gh_fix=missing_gh_fix,
    )
    return dev_check_from_prerequisite(
        check_github_cli_auth_prerequisite(
            request,
            command_exists=command_exists,
            run_check=run_check,
        )
    )
