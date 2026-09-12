"""Trust review guidance shared by CLI commands and execution preflight."""

from __future__ import annotations

import shlex
import sys
from typing import Any

from .trust_store import TRUST_SCOPE_WARNING, ManifestCommandTrustIdentity, TrustStatus


def allow_command_text(identity: ManifestCommandTrustIdentity) -> str:
    return shlex.join(
        [
            "basectl",
            "trust",
            "allow",
            identity.project_name,
            "--manifest-sha256",
            identity.manifest_sha256,
            "--workspace",
            str(identity.project_root.parent),
        ]
    )


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
        print()
        print_trust_scope_warning()
        return

    if trust_status.reason in {"manifest_changed", "test_requirements_changed"}:
        print(
            f"Manifest command trust is blocked for project '{identity.project_name}': "
            "manifest or declared test requirements changed."
        )
        if trust_status.reason == "test_requirements_changed":
            print("Declared test requirements changed; review the requirements file before allowing commands.")
        changed_project = (trust_status.changed_record or {}).get("project", {})
        if isinstance(changed_project, dict) and changed_project.get("manifest_sha256"):
            print(f"Recorded Manifest SHA-256: {changed_project['manifest_sha256']}")
    else:
        print(f"Manifest command trust is blocked for project '{identity.project_name}'.")
    print_identity("Current identity", identity)
    print()
    print_trust_scope_warning()
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
    if trust_status.reason in {"manifest_changed", "test_requirements_changed"}:
        print(
            f"ERROR: Manifest command trust is blocked for project '{identity.project_name}': "
            "manifest command or declared test requirements contract changed.",
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
    if trust_status.reason in {"manifest_changed", "test_requirements_changed"}:
        changed_project = (trust_status.changed_record or {}).get("project", {})
        if isinstance(changed_project, dict) and changed_project.get("manifest_sha256"):
            print(f"Recorded Manifest SHA-256: {changed_project['manifest_sha256']}", file=stream)
    print(f"Manifest SHA-256: {identity.manifest_sha256}", file=stream)
    if identity.test_requirements_sha256 is not None:
        print(f"Test requirements SHA-256: {identity.test_requirements_sha256}", file=stream)
    if identity.origin is not None:
        print(f"Origin: {identity.origin}", file=stream)
    print(file=stream)
    print_trust_scope_warning(stream=stream)
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
    workspace = str(identity.project_root.parent)
    print("Review first:", file=stream)
    if "run" in surfaces:
        print(
            f"  {shlex.join(['basectl', 'run', identity.project_name, '--list', '--workspace', workspace])}",
            file=stream,
        )
    if "build" in surfaces:
        print(
            f"  {shlex.join(['basectl', 'build', identity.project_name, '--list', '--workspace', workspace])}",
            file=stream,
        )
    if "test" in surfaces:
        print(
            f"  {shlex.join(['basectl', 'test', identity.project_name, '--dry-run', '--workspace', workspace])}",
            file=stream,
        )
    if "demo" in surfaces:
        print(
            f"  {shlex.join(['basectl', 'demo', identity.project_name, '--dry-run', '--workspace', workspace])}",
            file=stream,
        )
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
    if identity.test_requirements_sha256 is not None:
        print(f"  Test requirements SHA-256: {identity.test_requirements_sha256}")
    if identity.origin is not None:
        print(f"  Origin: {identity.origin}")
    if identity.head is not None:
        print(f"  HEAD: {identity.head}")


def print_trust_scope_warning(*, stream: Any | None = None) -> None:
    if stream is None:
        stream = sys.stdout
    print("Trust scope:", file=stream)
    print(f"  {TRUST_SCOPE_WARNING}", file=stream)

