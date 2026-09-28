"""Compatibility exports for the shared manifest trust contract."""

from __future__ import annotations

from base_setup.git_commands import run_git  # pylint: disable=unused-import
from base_setup.git_remote_parse import parse_origin_remote  # pylint: disable=unused-import

from base_setup.manifest_trust import (
    ALLOWED_COMMANDS,
    SCHEMA_VERSION,
    TRUST_RELATIVE_ROOT,
    TRUST_SCOPE,
    TRUST_SCOPE_WARNING,
    ManifestCommandTrustIdentity,
    ManifestCommandTrustStore,
    TrustStatus,
    compute_identity_key,
    compute_trust_identity,
    compute_trust_identity_for_manifest,
    git_head,
    git_origin,
    git_repository_root,
    identity_key_from_record,
    manifest_command_surfaces,
    manifest_command_surfaces_from_manifest,
    sha256_file,
    trust_change_reason,
    trust_scope_payload,
    write_json_atomic,
)

__all__ = [
    "ALLOWED_COMMANDS",
    "SCHEMA_VERSION",
    "TRUST_RELATIVE_ROOT",
    "TRUST_SCOPE",
    "TRUST_SCOPE_WARNING",
    "ManifestCommandTrustIdentity",
    "ManifestCommandTrustStore",
    "TrustStatus",
    "compute_identity_key",
    "compute_trust_identity",
    "compute_trust_identity_for_manifest",
    "git_head",
    "git_origin",
    "git_repository_root",
    "identity_key_from_record",
    "manifest_command_surfaces",
    "manifest_command_surfaces_from_manifest",
    "sha256_file",
    "trust_change_reason",
    "trust_scope_payload",
    "write_json_atomic",
]
