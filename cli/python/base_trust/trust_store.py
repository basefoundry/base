from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from base_cli_adapters.history import format_timestamp, utc_now
from base_cli_adapters.paths import base_state_root
from base_setup.git_commands import run_git
from base_setup.git_remote_parse import parse_origin_remote
from base_setup.manifest import BaseManifest
from base_setup.manifest import read_manifest
from base_setup.test_requirements import requirements_file_digest

SCHEMA_VERSION = 1
ALLOWED_COMMANDS = ["test", "run", "build", "demo", "activate"]
TRUST_RELATIVE_ROOT = Path("trust") / "manifest-commands"
TRUST_SCOPE_WARNING = (
    "Approval is bound to the base_manifest.yaml SHA-256 and declared local test "
    "requirements SHA-256. Manifest or declared test requirements changes invalidate "
    "approval; referenced scripts, direct executable files, Git HEAD, and uncommitted "
    "working-tree changes are not independently verified or bound to approval. Re-review "
    "those inputs before execution after repository changes."
)
TRUST_SCOPE = {
    "approval_basis": "base_manifest.yaml_sha256+declared_test_requirements_sha256",
    "manifest_changes_invalidate": True,
    "declared_test_requirements_changes_invalidate": True,
    "referenced_script_changes_invalidate": False,
    "direct_executable_file_changes_invalidate": False,
    "git_head_changes_invalidate": False,
    "working_tree_changes_invalidate": False,
    "warning": TRUST_SCOPE_WARNING,
}


def trust_scope_payload() -> dict[str, object]:
    return dict(TRUST_SCOPE)


@dataclass(frozen=True)
class ManifestCommandTrustIdentity:
    project_name: str
    project_root: Path
    manifest_path: Path
    manifest_sha256: str
    identity_key: str
    test_requirements_sha256: str | None = None
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
        if self.test_requirements_sha256 is not None:
            payload["test_requirements_sha256"] = self.test_requirements_sha256
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
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            return None
        if identity_key_from_record(payload) != identity.identity_key:
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
                reason=trust_change_reason(identity, changed_record),
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
            except (OSError, UnicodeError, json.JSONDecodeError):
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
        paths = {self.record_path(identity)}
        try:
            records = tuple(self.root.iterdir())
        except FileNotFoundError:
            return False
        for path in records:
            if path.suffix != ".json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
                continue
            project = payload.get("project")
            if isinstance(project, dict) and project.get("root") == str(identity.project_root) and project.get(
                "manifest"
            ) == str(identity.manifest_path):
                # Unlink the record in this store, never a path from its contents.
                paths.add(path)

        for path in sorted(paths):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed = True
        return removed


def manifest_command_surfaces(manifest_path: Path) -> tuple[str, ...]:
    manifest = read_manifest(manifest_path.expanduser().resolve())
    return manifest_command_surfaces_from_manifest(manifest)


def manifest_command_surfaces_from_manifest(manifest: BaseManifest) -> tuple[str, ...]:
    surfaces = []
    if manifest.test is not None:
        surfaces.append("test")
    if manifest.commands:
        surfaces.append("run")
    if manifest.build is not None and manifest.build.targets:
        surfaces.append("build")
    if manifest.demo is not None:
        surfaces.append("demo")
    if manifest.activate.source:
        surfaces.append("activate")
    return tuple(surfaces)


def compute_trust_identity_for_manifest(manifest_path: Path) -> ManifestCommandTrustIdentity:
    manifest = read_manifest(manifest_path.expanduser().resolve())
    return compute_trust_identity(manifest)


def compute_trust_identity(manifest: BaseManifest) -> ManifestCommandTrustIdentity:
    canonical_manifest = manifest.path.resolve()
    project_root = canonical_manifest.parent.resolve()
    manifest_sha256 = sha256_file(canonical_manifest)
    requirements_sha256 = requirements_file_digest(manifest)
    git_root = git_repository_root(project_root)
    origin = git_origin(project_root)
    head = git_head(project_root)
    identity_key = compute_identity_key(project_root, canonical_manifest, manifest_sha256, requirements_sha256)
    return ManifestCommandTrustIdentity(
        project_name=manifest.project_name,
        project_root=project_root,
        manifest_path=canonical_manifest,
        manifest_sha256=manifest_sha256,
        test_requirements_sha256=requirements_sha256,
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


def compute_identity_key(
    project_root: Path,
    manifest_path: Path,
    manifest_sha256: str,
    test_requirements_sha256: str | None = None,
) -> str:
    payload = "\0".join([str(project_root), str(manifest_path), manifest_sha256, test_requirements_sha256 or ""])
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
    requirements_digest = project.get("test_requirements_sha256")
    if requirements_digest is not None and not isinstance(requirements_digest, str):
        return None
    return compute_identity_key(Path(root), Path(manifest), digest, requirements_digest)


def trust_change_reason(identity: ManifestCommandTrustIdentity, record: dict[str, Any]) -> str:
    project = record.get("project")
    if not isinstance(project, dict):
        return "manifest_changed"
    if project.get("manifest_sha256") != identity.manifest_sha256:
        return "manifest_changed"
    if project.get("test_requirements_sha256") != identity.test_requirements_sha256:
        return "test_requirements_changed"
    return "manifest_changed"


def git_repository_root(project_root: Path) -> Path | None:
    result = run_git(project_root, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return Path(value).resolve() if value else None


def git_origin(project_root: Path) -> str | None:
    result = run_git(project_root, ["remote", "get-url", "origin"])
    if result.returncode != 0:
        return None
    remote_url = result.stdout.strip()
    if not remote_url:
        return None
    remote_info = parse_origin_remote(remote_url, project_root)
    return remote_info.sanitized_url if remote_info.valid and remote_info.sanitized_url else None


def git_head(project_root: Path) -> str | None:
    result = run_git(project_root, ["rev-parse", "HEAD"])
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
