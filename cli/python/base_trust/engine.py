from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base_cli
from base_cli.history import base_version as read_base_version
from base_cli.history import format_timestamp, utc_now
from base_cli.paths import base_state_root
from base_projects import engine as project_engine
from base_projects.workspace_reports import ProjectDiscoveryError
from base_setup import git_remote
from base_setup.manifest import ManifestError, read_manifest


SCHEMA_VERSION = 1
ALLOWED_COMMANDS = ["test", "run", "build", "demo", "activate"]
TRUST_RELATIVE_ROOT = Path("trust") / "manifest-commands"


app = base_cli.App(
    name="base_trust",
    help="Manage local approval for manifest-declared project commands.",
)


@dataclass(frozen=True)
class ManifestCommandTrustIdentity:
    project_name: str
    project_root: Path
    manifest_path: Path
    manifest_sha256: str
    identity_key: str
    git_root: Path | None = None
    origin: str | None = None
    head: str | None = None

    def project_payload(self) -> dict[str, str]:
        payload = {
            "name": self.project_name,
            "root": str(self.project_root),
            "manifest": str(self.manifest_path),
            "manifest_sha256": self.manifest_sha256,
        }
        if self.git_root is not None:
            payload["git_root"] = str(self.git_root)
        if self.origin is not None:
            payload["origin"] = self.origin
        if self.head is not None:
            payload["head"] = self.head
        return payload


@dataclass(frozen=True)
class TrustStatus:
    status: str
    reason: str
    identity: ManifestCommandTrustIdentity
    record: dict[str, Any] | None = None
    changed_record: dict[str, Any] | None = None

    @property
    def is_allowed(self) -> bool:
        return self.status == "allowed"


class ManifestCommandTrustStore:
    def __init__(self, home: Path | None = None) -> None:
        self.root = base_state_root(home) / TRUST_RELATIVE_ROOT

    def record_path(self, identity: ManifestCommandTrustIdentity) -> Path:
        return self.root / f"{identity.identity_key}.json"

    def read_record(self, identity: ManifestCommandTrustIdentity) -> dict[str, Any] | None:
        path = self.record_path(identity)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            return None
        return payload

    def status(self, identity: ManifestCommandTrustIdentity) -> TrustStatus:
        record = self.read_record(identity)
        if record is not None:
            return TrustStatus(status="allowed", reason="allowed", identity=identity, record=record)

        changed_record = self.find_changed_record(identity)
        if changed_record is not None:
            return TrustStatus(
                status="blocked",
                reason="manifest_changed",
                identity=identity,
                changed_record=changed_record,
            )

        return TrustStatus(status="blocked", reason="not_allowed", identity=identity)

    def find_changed_record(self, identity: ManifestCommandTrustIdentity) -> dict[str, Any] | None:
        if not self.root.is_dir():
            return None
        for path in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
                continue
            project = payload.get("project")
            if not isinstance(project, dict):
                continue
            if project.get("root") == str(identity.project_root) and project.get("manifest") == str(
                identity.manifest_path
            ):
                return payload
        return None

    def allow(
        self,
        identity: ManifestCommandTrustIdentity,
        *,
        base_version: str | None,
        allowed_at: str | None = None,
    ) -> Path:
        path = self.record_path(identity)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "allowed_at": allowed_at or format_timestamp(utc_now()),
            "allowed_by": "local-user",
            "base_version": base_version,
            "project": identity.project_payload(),
            "allowed_commands": ALLOWED_COMMANDS,
        }
        write_json_atomic(path, payload)
        return path

    def revoke(self, identity: ManifestCommandTrustIdentity) -> bool:
        removed = False
        paths = [self.record_path(identity)]
        changed_record = self.find_changed_record(identity)
        if changed_record is not None:
            changed_identity_key = identity_key_from_record(changed_record)
            if changed_identity_key is not None:
                paths.append(self.root / f"{changed_identity_key}.json")

        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed = True
        return removed


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.subcommand("status", context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project")
@base_cli.option(
    "--workspace",
    help="Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.",
)
@base_cli.option("--format", "output_format", default="text", help="Output format: text or json.")
def status_command(ctx: base_cli.Context, project: str, workspace: str | None, output_format: str) -> int:
    if output_format not in {"text", "json"}:
        ctx.log.error("Unsupported output format '%s'. Expected one of: text, json.", output_format)
        return base_cli.ExitCode.USAGE_ERROR
    try:
        identity = resolve_trust_identity(ctx, project, workspace)
    except (ProjectDiscoveryError, ManifestError, TrustError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    trust_status = ManifestCommandTrustStore().status(identity)
    if output_format == "json":
        print(json.dumps(status_payload(trust_status), indent=2, sort_keys=True))
    else:
        print_status_text(trust_status)
    return base_cli.ExitCode.SUCCESS


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


def resolve_trust_identity(
    ctx: base_cli.Context,
    project_name: str,
    workspace: str | None,
) -> ManifestCommandTrustIdentity:
    project = project_engine.resolve_named_project(ctx, project_name, workspace)
    return compute_trust_identity_for_manifest(project.manifest_path)


def compute_trust_identity_for_manifest(manifest_path: Path) -> ManifestCommandTrustIdentity:
    manifest = read_manifest(manifest_path.expanduser().resolve())
    canonical_manifest = manifest.path.resolve()
    project_root = canonical_manifest.parent.resolve()
    manifest_sha256 = sha256_file(canonical_manifest)
    git_root = git_repository_root(project_root)
    origin = git_origin(project_root)
    head = git_head(project_root)
    identity_key = compute_identity_key(project_root, canonical_manifest, manifest_sha256)
    return ManifestCommandTrustIdentity(
        project_name=manifest.project_name,
        project_root=project_root,
        manifest_path=canonical_manifest,
        manifest_sha256=manifest_sha256,
        identity_key=identity_key,
        git_root=git_root,
        origin=origin,
        head=head,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_identity_key(project_root: Path, manifest_path: Path, manifest_sha256: str) -> str:
    payload = "\0".join([str(project_root), str(manifest_path), manifest_sha256])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def identity_key_from_record(record: dict[str, Any]) -> str | None:
    project = record.get("project")
    if not isinstance(project, dict):
        return None
    root = project.get("root")
    manifest = project.get("manifest")
    digest = project.get("manifest_sha256")
    if not all(isinstance(value, str) and value for value in (root, manifest, digest)):
        return None
    return compute_identity_key(Path(root), Path(manifest), digest)


def git_repository_root(project_root: Path) -> Path | None:
    result = git_remote.run_git(project_root, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return Path(value).resolve() if value else None


def git_origin(project_root: Path) -> str | None:
    result = git_remote.run_git(project_root, ["remote", "get-url", "origin"])
    if result.returncode != 0:
        return None
    remote_url = result.stdout.strip()
    if not remote_url:
        return None
    remote_info = git_remote.parse_origin_remote(remote_url, project_root)
    return remote_info.sanitized_url if remote_info.valid and remote_info.sanitized_url else None


def git_head(project_root: Path) -> str | None:
    result = git_remote.run_git(project_root, ["rev-parse", "HEAD"])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
        path.chmod(0o600)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


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


def print_status_text(trust_status: TrustStatus) -> None:
    identity = trust_status.identity
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
    print(f"Allow after review: {allow_command_text(identity)}")


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
