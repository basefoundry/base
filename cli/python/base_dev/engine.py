from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_setup.engine import ArtifactError, reconcile_artifact, resolve_artifact_definitions, run_check
from base_setup.manifest import ArtifactRequest, BaseManifest, ManifestError, read_manifest
from base_setup.registry import ArtifactDefinition


app = base_cli.App(name="base_dev")


@dataclass(frozen=True)
class DevCheck:
    name: str
    ok: bool
    message: str
    fix: str
    status: str = ""


def main(argv: list[str] | None = None) -> int:
    result = app.click_command.main(args=argv, standalone_mode=False)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("action", required=True)
@base_cli.option("--dry-run", is_flag=True, help="Log planned setup changes without making them.")
@base_cli.option("--format", "output_format", default="text", help="Output format for check/doctor: text or json.")
def run(ctx: base_cli.Context, action: str, dry_run: bool, output_format: str) -> int:
    try:
        manifest = read_dev_manifest(ctx)
        definitions = resolve_artifact_definitions(manifest.artifacts)
    except (ManifestError, ArtifactError) as exc:
        ctx.log.error(str(exc))
        return 1

    if action == "setup":
        return setup_dev_artifacts(ctx, manifest, definitions, dry_run=dry_run)
    if action == "check":
        return check_dev_artifacts(ctx, manifest.artifacts, definitions, output_format=output_format)
    if action == "doctor":
        return doctor_dev_artifacts(manifest.artifacts, definitions, output_format=output_format)

    ctx.log.error("Unsupported base_dev action '%s'. Expected setup, check, or doctor.", action)
    return 2


def read_dev_manifest(ctx: base_cli.Context) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's developer prerequisite manifest.")
    return read_manifest(dev_manifest_path(ctx.base_home))


def dev_manifest_path(base_home: Path) -> Path:
    return base_home / "lib" / "base" / "dev_manifest.yaml"


def setup_dev_artifacts(
    ctx: base_cli.Context,
    manifest: BaseManifest,
    definitions: tuple[ArtifactDefinition, ...],
    dry_run: bool,
) -> int:
    ctx.log.info("Reading Base developer prerequisite manifest at '%s'.", manifest.path)
    ctx.log.info("Setting up Base developer prerequisites.")

    try:
        for artifact, definition in zip(manifest.artifacts, definitions, strict=True):
            reconcile_artifact(ctx, definition, artifact.version, manifest.project_name, dry_run=dry_run)
    except ArtifactError as exc:
        ctx.log.error(str(exc))
        return 1

    ctx.log.info("Base developer prerequisite setup is complete.")
    return 0


def check_dev_artifacts(
    ctx: base_cli.Context,
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    output_format: str,
) -> int:
    checks = dev_checks(artifacts, definitions)
    if output_format == "json":
        print(json.dumps([check_to_json(check) for check in checks], indent=2))
    elif output_format == "text":
        for check in checks:
            if check.ok:
                ctx.log.info(check.message)
            else:
                ctx.log.warning(check.message)
    else:
        ctx.log.error("Unsupported check output format '%s'. Expected text or json.", output_format)
        return 2

    return 0 if all(check.ok for check in checks) else 1


def doctor_dev_artifacts(
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
    output_format: str,
) -> int:
    checks = dev_checks(artifacts, definitions)
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
            print_doctor_finding("error", check.name, check.message, check.fix)
            error_count += 1
        else:
            print_doctor_finding(status, check.name, check.message, check.fix)
    return min(error_count, 125)


def dev_checks(
    artifacts: tuple[ArtifactRequest, ...],
    definitions: tuple[ArtifactDefinition, ...],
) -> tuple[DevCheck, ...]:
    checks: list[DevCheck] = []
    for artifact, definition in zip(artifacts, definitions):
        check = check_homebrew_artifact(artifact, definition)
        checks.append(check)
        if artifact.name == "gh" and check.ok:
            checks.append(check_github_cli_auth())
    return tuple(checks)


def check_homebrew_artifact(artifact: ArtifactRequest, definition: ArtifactDefinition) -> DevCheck:
    if definition.manager != "homebrew":
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=(
                f"Artifact '{artifact.name}' uses unsupported developer prerequisite manager '{definition.manager}'."
            ),
            fix="Update lib/base/dev_manifest.yaml to use a Homebrew-managed tool.",
        )
    if artifact.version != "latest":
        return DevCheck(
            name=artifact.name,
            ok=False,
            message=f"Artifact '{artifact.name}' uses unsupported developer prerequisite version '{artifact.version}'.",
            fix="Use version 'latest' for Homebrew-managed developer prerequisites.",
        )

    ok = run_check(["brew", "list", definition.package])
    if ok:
        return DevCheck(
            name=artifact.name,
            ok=True,
            message=f"Artifact '{artifact.name}' is installed via Homebrew package '{definition.package}'.",
            fix="",
        )
    return DevCheck(
        name=artifact.name,
        ok=False,
        message=f"Artifact '{artifact.name}' is not installed via Homebrew package '{definition.package}'.",
        fix="basectl setup --dev",
    )


def check_github_cli_auth() -> DevCheck:
    ok = run_check(["gh", "auth", "status"])
    if ok:
        return DevCheck(
            name="gh-auth",
            ok=True,
            message="GitHub CLI authentication is ready.",
            fix="",
        )
    return DevCheck(
        name="gh-auth",
        ok=False,
        message="GitHub CLI authentication is not ready.",
        fix="gh auth login -h github.com",
    )


def check_to_json(check: DevCheck) -> dict[str, str | bool]:
    return {
        "name": check.name,
        "ok": check.ok,
        "message": check.message,
        "fix": check.fix,
    }


def check_to_doctor_json(check: DevCheck) -> dict[str, str]:
    return {
        "status": doctor_status(check),
        "name": check.name,
        "message": check.message,
        "fix": check.fix,
    }


def doctor_status(check: DevCheck) -> str:
    return check.status or ("ok" if check.ok else "error")


def print_doctor_finding(status: str, name: str, message: str, fix: str = "") -> None:
    print(f"{status:<5}  {name:<26}  {message}")
    if fix:
        print(f"       Fix: {fix}")
