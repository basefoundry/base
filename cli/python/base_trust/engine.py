from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import base_cli
from base_cli.history import base_version as read_base_version
from base_projects import engine as project_engine
from base_projects.project_discovery import Project
from base_projects.project_discovery import discover_projects_cached
from base_projects.project_discovery import read_project
from base_projects.workspace_context import resolve_workspace_root
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.manifest_loader import ManifestError
from .trust_store import ALLOWED_COMMANDS  # pylint: disable=unused-import
from .trust_store import SCHEMA_VERSION
from .trust_store import TRUST_RELATIVE_ROOT  # pylint: disable=unused-import
from .trust_store import ManifestCommandTrustIdentity
from .trust_store import ManifestCommandTrustStore
from .trust_store import TrustStatus
from .trust_store import compute_identity_key  # pylint: disable=unused-import
from .trust_store import compute_trust_identity_for_manifest
from .trust_store import git_head  # pylint: disable=unused-import
from .trust_store import git_origin  # pylint: disable=unused-import
from .trust_store import git_repository_root  # pylint: disable=unused-import
from .trust_store import identity_key_from_record  # pylint: disable=unused-import
from .trust_store import manifest_command_surfaces
from .trust_store import sha256_file  # pylint: disable=unused-import
from .trust_store import write_json_atomic  # pylint: disable=unused-import


app = base_cli.App(
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
@base_cli.option("--format", "output_format", default="text", help="Output format: text or json.")
def status_command(ctx: base_cli.Context, project: str | None, workspace: str | None, output_format: str) -> int:
    if output_format not in {"text", "json"}:
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
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
    if output_format == "json":
        print(json.dumps(status_payload(trust_status), indent=2, sort_keys=True))
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
    ManifestCommandTrustStore().allow(identity, base_version=read_base_version(ctx.base_home))
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

    removed = ManifestCommandTrustStore().revoke(identity)
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
            surfaces = manifest_command_surfaces(project.manifest_path)
            if not surfaces:
                continue
            identity = compute_trust_identity_for_manifest(project.manifest_path)
            statuses.append((store.status(identity), surfaces))
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if output_format == "json":
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "projects": [status_payload(trust_status) for trust_status, _surfaces in statuses],
                },
                indent=2,
                sort_keys=True,
            )
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

        if ctx.base_home is not None:
            base_manifest = ctx.base_home / "base_manifest.yaml"
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
    }
    if trust_status.is_allowed:
        payload["record"] = trust_status.record
    else:
        payload["allow_command"] = allow_command_text(trust_status.identity)
    if trust_status.changed_record is not None:
        changed_project = trust_status.changed_record.get("project", {})
        if isinstance(changed_project, dict) and isinstance(changed_project.get("manifest_sha256"), str):
            payload["recorded_manifest_sha256"] = changed_project["manifest_sha256"]
    return payload


def allow_command_text(identity: ManifestCommandTrustIdentity) -> str:
    return f"basectl trust allow {identity.project_name} --manifest-sha256 {identity.manifest_sha256}"


def print_status_text(trust_status: TrustStatus, surfaces: tuple[str, ...]) -> None:
    identity = trust_status.identity
    if not surfaces:
        print(
            f"Manifest command trust is not required for project '{identity.project_name}': "
            "the manifest declares no executable command surfaces."
        )
        return

    if trust_status.is_allowed:
        print(f"Manifest command trust is allowed for project '{identity.project_name}'.")
        print_identity("Trusted identity", identity)
        return

    if trust_status.reason == "manifest_changed":
        print(f"Manifest command trust is blocked for project '{identity.project_name}': manifest changed.")
        changed_project = (trust_status.changed_record or {}).get("project", {})
        if isinstance(changed_project, dict) and changed_project.get("manifest_sha256"):
            print(f"Recorded Manifest SHA-256: {changed_project['manifest_sha256']}")
    else:
        print(f"Manifest command trust is blocked for project '{identity.project_name}'.")
    print_identity("Current identity", identity)
    print()
    print_review_guidance(identity, surfaces, stream=sys.stdout)
    print()
    print("Allow after review:")
    print(f"  {allow_command_text(identity)}")


def print_blocked_command_text(
    trust_status: TrustStatus,
    surfaces: tuple[str, ...],
    *,
    stream: Any,
) -> None:
    identity = trust_status.identity
    if trust_status.reason == "manifest_changed":
        print(
            f"ERROR: Manifest command trust is blocked for project '{identity.project_name}': "
            "manifest command contract changed.",
            file=stream,
        )
    else:
        print(
            f"ERROR: Manifest-declared commands are not allowed for project "
            f"'{identity.project_name}' on this machine.",
            file=stream,
        )
    print(f"Project root: {identity.project_root}", file=stream)
    print(f"Manifest: {identity.manifest_path}", file=stream)
    if trust_status.reason == "manifest_changed":
        changed_project = (trust_status.changed_record or {}).get("project", {})
        if isinstance(changed_project, dict) and changed_project.get("manifest_sha256"):
            print(f"Recorded Manifest SHA-256: {changed_project['manifest_sha256']}", file=stream)
    print(f"Manifest SHA-256: {identity.manifest_sha256}", file=stream)
    if identity.origin is not None:
        print(f"Origin: {identity.origin}", file=stream)
    print(file=stream)
    print_review_guidance(identity, surfaces, stream=stream)
    print(file=stream)
    print("Allow after review:", file=stream)
    print(f"  {allow_command_text(identity)}", file=stream)


def print_review_guidance(
    identity: ManifestCommandTrustIdentity,
    surfaces: tuple[str, ...],
    *,
    stream: Any,
) -> None:
    print("Review first:", file=stream)
    if "run" in surfaces:
        print(f"  basectl run {identity.project_name} --list", file=stream)
    if "build" in surfaces:
        print(f"  basectl build {identity.project_name} --list", file=stream)
    if "test" in surfaces:
        print(f"  basectl test {identity.project_name} --dry-run", file=stream)
    if "demo" in surfaces:
        print(f"  basectl demo {identity.project_name} --dry-run", file=stream)
    if "activate" in surfaces:
        print(
            f"  Inspect activate.source entries in {identity.manifest_path} before running "
            f"'basectl activate {identity.project_name}'.",
            file=stream,
        )


def print_identity(title: str, identity: ManifestCommandTrustIdentity) -> None:
    print(f"{title}:")
    print(f"  Project: {identity.project_name}")
    print(f"  Project root: {identity.project_root}")
    print(f"  Manifest: {identity.manifest_path}")
    print(f"  Manifest SHA-256: {identity.manifest_sha256}")
    if identity.origin is not None:
        print(f"  Origin: {identity.origin}")
    if identity.head is not None:
        print(f"  HEAD: {identity.head}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
