"""Approval and dependency checks before executing a project test contract."""

from __future__ import annotations

import base_cli

from base_setup.manifest_model import BaseManifest
from base_setup.test_requirements import check_test_requirements


def project_test_preflight(ctx: base_cli.Context, manifest: BaseManifest) -> bool:
    # Import at invocation time: the trust command resolves projects through
    # the project engine, which also owns this preflight's public entry point.
    from base_trust.engine import require_command

    if require_command(ctx, manifest.project_name, None, str(manifest.path)) != base_cli.ExitCode.SUCCESS:
        return False
    check = check_test_requirements(manifest)
    if check is None or check.ok:
        return True
    ctx.log.error(check.message)
    if check.fix:
        ctx.log.error("Fix: %s", check.fix)
    return False
