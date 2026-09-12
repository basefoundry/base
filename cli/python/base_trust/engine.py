from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import base_cli
from base_cli_profile import base_cli_app
from base_cli_adapters.history import base_version as read_base_version
from base_projects import engine as project_engine
from base_projects.project_discovery import Project
from base_projects.project_discovery import discover_projects_cached
from base_projects.project_discovery import read_project
from base_projects.workspace_context import resolve_workspace_root
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from .guidance import allow_command_text
from .guidance import print_blocked_command_text
from .guidance import print_identity
from .guidance import print_status_text
from .guidance import print_trust_scope_warning
from .guidance import print_review_guidance  # pylint: disable=unused-import
from .trust_store import ALLOWED_COMMANDS  # pylint: disable=unused-import
from .trust_store import SCHEMA_VERSION
from .trust_store import TRUST_RELATIVE_ROOT  # pylint: disable=unused-import
from .trust_store import TRUST_SCOPE  # pylint: disable=unused-import
from .trust_store import TRUST_SCOPE_WARNING  # pylint: disable=unused-import
from .trust_store import ManifestCommandTrustIdentity
from .trust_store import ManifestCommandTrustStore
from .trust_store import TrustStatus
from .trust_store import compute_identity_key  # pylint: disable=unused-import
from .trust_store import compute_trust_identity
from .trust_store import compute_trust_identity_for_manifest
from .trust_store import git_head  # pylint: disable=unused-import
from .trust_store import git_origin  # pylint: disable=unused-import
from .trust_store import git_repository_root  # pylint: disable=unused-import
from .trust_store import identity_key_from_record  # pylint: disable=unused-import
from .trust_store import manifest_command_surfaces
from .trust_store import manifest_command_surfaces_from_manifest
from .trust_store import sha256_file  # pylint: disable=unused-import
from .trust_store import trust_scope_payload
from .trust_store import write_json_atomic  # pylint: disable=unused-import


app = base_cli_app(
    name="base_trust",
    help="Manage local approval for manifest-declared project commands.",
)


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.subcommand("status", context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option(
    "--format",
    "output_format",
    default="text",
    help="Output format: text, csv, tsv, yaml, or json.",
)
def status_command(ctx: base_cli.Context, project: str | None, workspace: str | None, output_format: str) -> int:
    try:
        base_cli.resolve_output_format(output_format)
    except base_cli.OutputFormatError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.USAGE_ERROR

    if project is None:
        return workspace_status_command(ctx, workspace, output_format)

    try:
        identity = resolve_trust_identity(ctx, project, workspace)
        surfaces = manifest_command_surfaces(identity.manifest_path)
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    trust_status = ManifestCommandTrustStore().status(identity)
    payload = status_payload(trust_status)
    if output_format == "json":
        base_cli.render_document(payload, requested_format="json")
    elif output_format == "yaml":
        base_cli.render_document(payload, requested_format="yaml")
    elif output_format in {"csv", "tsv"} or not base_cli.is_terminal():
        base_cli.render_records(
            [trust_output_record(payload)],
            requested_format=output_format,
            columns=trust_output_columns(),
        )
    else:
        print_status_text(trust_status, surfaces)
    return base_cli.ExitCode.SUCCESS


@app.subcommand("require", context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project")
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option("--manifest", "manifest_path", help="Resolved base_manifest.yaml path to verify.")
def require_command(ctx: base_cli.Context, project: str, workspace: str | None, manifest_path: str | None) -> int:
    try:
        identity = resolve_trust_identity_for_require(ctx, project, workspace, manifest_path)
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    trust_status = ManifestCommandTrustStore().status(identity)
    if trust_status.is_allowed:
        return base_cli.ExitCode.SUCCESS

    print_blocked_command_text(
        trust_status,
        manifest_command_surfaces(identity.manifest_path),
        stream=sys.stderr,
    )
    return base_cli.ExitCode.FAILURE


@app.subcommand("allow", context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project")
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option("--manifest-sha256", help="Expected SHA-256 digest of base_manifest.yaml.")
def allow_command(ctx: base_cli.Context, project: str, workspace: str | None, manifest_sha256: str | None) -> int:
    try:
        identity = resolve_trust_identity(ctx, project, workspace)
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if manifest_sha256 is not None and manifest_sha256 != identity.manifest_sha256:
        ctx.log.error(
            "Provided --manifest-sha256 '%s' does not match current manifest SHA-256 '%s'.",
            manifest_sha256,
            identity.manifest_sha256,
        )
        return base_cli.ExitCode.USAGE_ERROR

    print_identity("Allowing manifest command trust", identity)
    print_trust_scope_warning()
    ManifestCommandTrustStore().allow(identity, base_version=read_base_version(ctx.application_home))
    print(f"Allowed manifest commands for project '{identity.project_name}'.")
    return base_cli.ExitCode.SUCCESS


@app.subcommand("revoke", context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project")
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
def revoke_command(ctx: base_cli.Context, project: str, workspace: str | None) -> int:
    try:
        identity = resolve_trust_identity(ctx, project, workspace)
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    try:
        removed = ManifestCommandTrustStore().revoke(identity)
    except OSError as exc:
        ctx.log.error("Unable to revoke manifest command trust for project '%s': %s", identity.project_name, exc)
        return base_cli.ExitCode.FAILURE
    if removed:
        print(f"Revoked manifest command trust for project '{identity.project_name}'.")
    else:
        print(f"No manifest command trust record found for project '{identity.project_name}'.")
    return base_cli.ExitCode.SUCCESS


class TrustError(RuntimeError):
    pass


def workspace_status_command(ctx: base_cli.Context, workspace: str | None, output_format: str) -> int:
    try:
        projects = workspace_status_projects(ctx, workspace)
        store = ManifestCommandTrustStore()
        statuses = []
        for project in projects:
            manifest = read_manifest(project.manifest_path)
            surfaces = manifest_command_surfaces_from_manifest(manifest)
            if not surfaces:
                continue
            identity = compute_trust_identity(manifest)
            statuses.append((store.status(identity), surfaces))
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    payload = {
        "schema_version": SCHEMA_VERSION,
        "projects": [status_payload(trust_status) for trust_status, _surfaces in statuses],
    }
    if output_format == "json":
        base_cli.render_document(payload, requested_format="json")
        return base_cli.ExitCode.SUCCESS
    if output_format == "yaml":
        base_cli.render_document(payload, requested_format="yaml")
        return base_cli.ExitCode.SUCCESS
    if output_format in {"csv", "tsv"} or not base_cli.is_terminal():
        base_cli.render_records(
            [trust_output_record(status_payload(trust_status)) for trust_status, _surfaces in statuses],
            requested_format=output_format,
            columns=trust_output_columns(),
        )
        return base_cli.ExitCode.SUCCESS

    if not statuses:
        print("No discovered projects require manifest command trust.")
        return base_cli.ExitCode.SUCCESS

    for index, (trust_status, surfaces) in enumerate(statuses):
        if index:
            print()
        print_status_text(trust_status, surfaces)
    return base_cli.ExitCode.SUCCESS


def workspace_status_projects(ctx: base_cli.Context, workspace: str | None) -> tuple[Project, ...]:
    workspace_root = resolve_workspace_root(ctx, workspace)
    projects_by_name = {project.name: project for project in discover_projects_cached(ctx, workspace_root)}

    if workspace is None:
        active_project = workspace_status_active_project()
        if active_project is not None:
            projects_by_name[active_project.name] = active_project

        if ctx.application_home is not None:
            base_manifest = ctx.application_home / "base_manifest.yaml"
            if base_manifest.is_file():
                base_project = read_project(base_manifest)
                projects_by_name[base_project.name] = base_project

    return tuple(sorted(projects_by_name.values()))


def workspace_status_active_project() -> Project | None:
    if "BASE_TRUST_ACTIVE_PROJECT" in os.environ:
        active_name = os.environ.get("BASE_TRUST_ACTIVE_PROJECT")
        active_manifest = os.environ.get("BASE_TRUST_ACTIVE_PROJECT_MANIFEST")
    else:
        active_name = os.environ.get("BASE_PROJECT")
        active_manifest = os.environ.get("BASE_PROJECT_MANIFEST")

    if not active_name or not active_manifest:
        return None

    project = read_project(Path(active_manifest).expanduser().resolve())
    if project.name != active_name:
        raise ProjectDiscoveryError(
            f"Active project is '{active_name}' but its manifest declares project '{project.name}'."
        )
    return project


def resolve_trust_identity(
    ctx: base_cli.Context,
    project_name: str,
    workspace: str | None,
) -> ManifestCommandTrustIdentity:
    project = project_engine.resolve_named_project(ctx, project_name, workspace)
    return compute_trust_identity_for_manifest(project.manifest_path)


def resolve_trust_identity_for_require(
    ctx: base_cli.Context,
    project_name: str,
    workspace: str | None,
    manifest_path: str | None,
) -> ManifestCommandTrustIdentity:
    if manifest_path is None:
        return resolve_trust_identity(ctx, project_name, workspace)

    identity = compute_trust_identity_for_manifest(Path(manifest_path))
    ctx.bind_project(identity.project_name, identity.project_root, identity.manifest_path)
    if identity.project_name != project_name:
        raise TrustError(
            f"Resolved manifest '{identity.manifest_path}' declares project '{identity.project_name}', "
            f"not '{project_name}'."
        )
    return identity


def status_payload(trust_status: TrustStatus) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": trust_status.status,
        "reason": trust_status.reason,
        "project": trust_status.identity.project_payload(),
        "trust_scope": trust_scope_payload(),
    }
    if trust_status.is_allowed:
        payload["record"] = trust_status.record
    else:
        payload["allow_command"] = allow_command_text(trust_status.identity)
    if trust_status.changed_record is not None:
        changed_project = trust_status.changed_record.get("project", {})
        if isinstance(changed_project, dict):
            if isinstance(changed_project.get("manifest_sha256"), str):
                payload["recorded_manifest_sha256"] = changed_project["manifest_sha256"]
            if isinstance(changed_project.get("test_requirements_sha256"), str):
                payload["recorded_test_requirements_sha256"] = changed_project["test_requirements_sha256"]
    return payload


def trust_output_columns() -> tuple[tuple[str, str], ...]:
    return (("PROJECT", "project"), ("STATUS", "status"), ("REASON", "reason"))


def trust_output_record(payload: dict[str, Any]) -> dict[str, Any]:
    project = payload.get("project")
    project_name = project.get("name", "-") if isinstance(project, dict) else "-"
    return {"project": project_name, "status": payload.get("status", "-"), "reason": payload.get("reason", "-")}




if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
