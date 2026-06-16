from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_setup.checks import DIAGNOSTIC_JSON_SCHEMA_VERSION
from base_setup.artifacts import reconcile_artifact, resolve_artifact_definitions
from base_setup.errors import ArtifactError
from base_setup.manifest import ArtifactRequest, BaseManifest, ManifestError, read_manifest
from base_setup.process import command_exists, dry_run_command, run_check, run_command
from base_setup.registry import ArtifactDefinition


app = base_cli.App(name="base_dev")
SUPPORTED_PROFILES = ("dev", "sre", "ai")


@dataclass(frozen=True)
class DevCheck:
    name: str
    ok: bool
    message: str
    fix: str
    status: str = ""
    finding_id: str = "BASE-D100"


@dataclass(frozen=True)
class ProfileManifest:
    name: str
    manifest: BaseManifest
    definitions: tuple[ArtifactDefinition, ...]


@dataclass(frozen=True)
class AITool:
    name: str
    display_name: str
    version_args: tuple[str, ...]
    installer_url: str
    installer_shell: str


class ProfileError(ValueError):
    pass


AI_TOOLS = (
    AITool(
        name="codex",
        display_name="Codex CLI",
        version_args=("--version",),
        installer_url="https://chatgpt.com/codex/install.sh",
        installer_shell="sh",
    ),
    AITool(
        name="claude",
        display_name="Claude Code",
        version_args=("--version",),
        installer_url="https://claude.ai/install.sh",
        installer_shell="bash",
    ),
)
AI_REMOTE_INSTALLER_ALLOWLIST = (
    "https://chatgpt.com/codex/install.sh",
    "https://claude.ai/install.sh",
)


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
        return 1
    except ProfileError as exc:
        ctx.log.error(str(exc))
        return 2

    if action == "setup":
        return setup_profiles(ctx, normalized_profiles, profile_manifests, dry_run=dry_run)
    if action == "check":
        return check_profiles(ctx, normalized_profiles, profile_manifests, output_format=output_format)
    if action == "doctor":
        return doctor_profiles(normalized_profiles, profile_manifests, output_format=output_format)

    ctx.log.error("Unsupported base_dev action '%s'. Expected setup, check, or doctor.", action)
    return 2


def normalize_profiles(profiles: tuple[str, ...]) -> tuple[str, ...]:
    if not profiles:
        return ("dev",)

    normalized: list[str] = []
    for profile_list in profiles:
        for raw_profile in profile_list.split(","):
            profile = raw_profile.strip().lower()
            if not profile:
                raise ProfileError("Profile list must not contain empty entries.")
            if profile not in SUPPORTED_PROFILES:
                display_profile = raw_profile.strip() or raw_profile
                raise ProfileError(
                    f"Unsupported profile '{display_profile}'. Expected one of: {', '.join(SUPPORTED_PROFILES)}."
                )
            if profile not in normalized:
                normalized.append(profile)
    return tuple(normalized)


def read_profile_manifests(ctx: base_cli.Context, profiles: tuple[str, ...]) -> tuple[ProfileManifest, ...]:
    profile_manifests: list[ProfileManifest] = []
    for profile in profiles:
        if profile == "ai":
            continue
        manifest = read_profile_manifest(ctx, profile)
        definitions = resolve_artifact_definitions(manifest.artifacts)
        profile_manifests.append(ProfileManifest(profile, manifest, definitions))
    return tuple(profile_manifests)


def read_profile_manifest(ctx: base_cli.Context, profile: str) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's prerequisite profile manifests.")
    return read_manifest(profile_manifest_path(ctx.base_home, profile))


def read_dev_manifest(ctx: base_cli.Context) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's developer prerequisite manifest.")
    return read_profile_manifest(ctx, "dev")


def dev_manifest_path(base_home: Path) -> Path:
    return base_home / "lib" / "base" / "dev_manifest.yaml"


def profile_manifest_path(base_home: Path, profile: str) -> Path:
    if profile == "dev":
        return dev_manifest_path(base_home)
    return base_home / "lib" / "base" / f"{profile}_manifest.yaml"


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
        if status != 0:
            return status
    return 0


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
        else:
            profile_manifest = profile_manifest_by_name[profile]
            status = setup_profile_artifacts(
                ctx,
                profile_manifest.name,
                profile_manifest.manifest,
                profile_manifest.definitions,
                dry_run=dry_run,
            )
        if status != 0:
            return status
    return 0


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
        for artifact, definition in zip(manifest.artifacts, definitions, strict=True):
            reconcile_artifact(ctx, definition, artifact.version, manifest.project_name, dry_run=dry_run)
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1

    if profile == "dev":
        ctx.log.info("Base developer prerequisite setup is complete.")
    else:
        ctx.log.info("Base '%s' prerequisite setup is complete.", profile)
    return 0


def setup_ai_tools(ctx: base_cli.Context, dry_run: bool) -> int:
    ctx.log.info("Setting up Base 'ai' prerequisites.")
    try:
        for tool in AI_TOOLS:
            check = check_ai_tool(tool)
            if check.ok:
                ctx.log.info("%s", check.message)
                continue
            installer_command = ai_tool_installer_command(tool)
            log_ai_remote_installer_policy(ctx, tool)
            ctx.log.info("Installing %s.", tool.display_name)
            if dry_run:
                dry_run_command(ctx, list(installer_command))
            else:
                run_command(ctx, list(installer_command))
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1

    ctx.log.info("Base 'ai' prerequisite setup is complete.")
    return 0


def ai_remote_installer_urls() -> tuple[str, ...]:
    return AI_REMOTE_INSTALLER_ALLOWLIST


def validate_ai_remote_installer(tool: AITool) -> None:
    if tool.installer_url not in AI_REMOTE_INSTALLER_ALLOWLIST:
        raise ArtifactError(
            "Remote installer URL is not allowlisted for Base 'ai' profile: "
            f"{tool.installer_url}"
        )


def ai_tool_installer_command(tool: AITool) -> tuple[str, ...]:
    validate_ai_remote_installer(tool)
    return ("sh", "-c", f"curl -fsSL {tool.installer_url} | {tool.installer_shell}")


def log_ai_remote_installer_policy(ctx: base_cli.Context, tool: AITool) -> None:
    ctx.log.info(
        "Remote installer policy: %s uses allowlisted installer %s; execution requires explicit --profile ai.",
        tool.display_name,
        tool.installer_url,
    )


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
        return 2

    return 0 if all(doctor_status(check) != "error" for check in checks) else 1


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
        print(f"Unsupported doctor output format '{output_format}'. Expected text or json.")
        return 2

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
        check = check_homebrew_artifact(artifact, definition, profile=profile)
        checks.append(check)
        if artifact.name == "gh" and check.ok:
            checks.append(check_github_cli_auth())
    return tuple(checks)


def ai_tool_checks() -> tuple[DevCheck, ...]:
    return tuple(check_ai_tool(tool) for tool in AI_TOOLS)


def check_ai_tool(tool: AITool) -> DevCheck:
    executable_path = shutil.which(tool.name)
    if executable_path is None:
        return DevCheck(
            name=tool.name,
            ok=False,
            message=f"{tool.display_name} '{tool.name}' was not found.",
            fix=profile_setup_fix("ai"),
            finding_id="BASE-D107",
        )

    command = [executable_path, *tool.version_args]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = summarize_command_output(completed.stderr) or summarize_command_output(completed.stdout)
        message = f"{tool.display_name} version check failed with exit {completed.returncode}."
        if detail:
            message = f"{message} {detail}"
        return DevCheck(
            name=tool.name,
            ok=False,
            message=message,
            fix=profile_setup_fix("ai"),
            finding_id="BASE-D107",
        )

    version = (
        summarize_command_output(completed.stdout)
        or summarize_command_output(completed.stderr)
        or "version unknown"
    )
    return DevCheck(
        name=tool.name,
        ok=True,
        message=f"{tool.display_name} is already installed at '{executable_path}' ({version}).",
        fix="",
        finding_id="BASE-D107",
    )


def summarize_command_output(output: str | None) -> str:
    return " ".join((output or "").split())


def profile_setup_fix(profile: str) -> str:
    return f"basectl setup --profile {profile}"


def check_homebrew_artifact(
    artifact: ArtifactRequest,
    definition: ArtifactDefinition,
    profile: str = "dev",
) -> DevCheck:
    if definition.manager != "homebrew":
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=(
                f"Artifact '{artifact.name}' uses unsupported developer prerequisite manager '{definition.manager}'."
            ),
            fix=f"Update {profile_manifest_path(Path('lib/base'), profile).name} to use a Homebrew-managed tool.",
            finding_id="BASE-D101",
        )
    if artifact.version != "latest":
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=f"Artifact '{artifact.name}' uses unsupported developer prerequisite version '{artifact.version}'.",
            fix="Use version 'latest' for Homebrew-managed developer prerequisites.",
            finding_id="BASE-D102",
        )

    if not command_exists("brew"):
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=f"Homebrew is required to check developer prerequisite '{artifact.name}'.",
            fix="basectl setup",
            finding_id="BASE-D103",
        )

    ok = run_check(["brew", "list", definition.package])
    if ok:
        return DevCheck(
            name=artifact.name,
            ok=True,
            message=f"Artifact '{artifact.name}' is installed via Homebrew package '{definition.package}'.",
            fix="",
            finding_id="BASE-D104",
        )
    return DevCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact '{artifact.name}' is not installed via Homebrew package '{definition.package}'.",
        fix=profile_setup_fix(profile),
        finding_id="BASE-D104",
    )


def check_github_cli_auth() -> DevCheck:
    if not command_exists("gh"):
        return DevCheck(
            name="gh-auth",
            ok=False,
            message="GitHub CLI 'gh' was not found.",
            fix="basectl setup --profile dev",
            finding_id="BASE-D105",
        )

    ok = run_check(["gh", "auth", "status"])
    if ok:
        return DevCheck(
            name="gh-auth",
            ok=True,
            message="GitHub CLI authentication is ready.",
            fix="",
            finding_id="BASE-D106",
        )
    return DevCheck(
        name="gh-auth",
        ok=False,
        message="GitHub CLI authentication is not ready.",
        fix="gh auth login -h github.com",
        finding_id="BASE-D106",
    )


def check_to_json(check: DevCheck) -> dict[str, str]:
    return {
        "id": check.finding_id,
        "status": doctor_status(check),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def check_to_doctor_json(check: DevCheck) -> dict[str, str]:
    return check_to_json(check)


def checks_status(checks: tuple[DevCheck, ...]) -> str:
    statuses = tuple(doctor_status(check) for check in checks)
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


def doctor_status(check: DevCheck) -> str:
    return check.status or ("ok" if check.ok else "error")


def print_doctor_finding(status: str, finding_id: str, name: str, message: str, fix: str = "") -> None:
    print(f"{status:<5}  {finding_id:<9}  {name:<26}  {message}")
    if fix:
        print(f"       Fix: {fix}")
