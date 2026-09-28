"""Approval and dependency checks before executing a project test contract."""

from __future__ import annotations

import sys

import base_cli

from base_setup.manifest_model import BaseManifest
from base_setup.test_requirements import check_test_requirements
from base_setup.manifest_trust import (
    ManifestCommandTrustStore, compute_trust_identity, manifest_command_surfaces_from_manifest,
)
from base_setup.manifest_trust_guidance import print_blocked_command_text


def project_test_preflight(ctx: base_cli.Context, manifest: BaseManifest) -> bool:
    identity = compute_trust_identity(manifest)
    trust_status = ManifestCommandTrustStore().status(identity)
    if not trust_status.is_allowed:
        print_blocked_command_text(
            trust_status, manifest_command_surfaces_from_manifest(manifest), stream=sys.stderr,
        )
        return False
    check = check_test_requirements(manifest)
    if check is None or check.ok:
        return True
    ctx.log.error(check.message)
    if check.fix:
        ctx.log.error("Fix: %s", check.fix)
    return False
