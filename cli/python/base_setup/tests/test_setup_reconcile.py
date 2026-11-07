from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from base_setup import engine
from base_setup.manifest import BaseManifest
from base_setup.tests.helpers import fake_context


class SetupReconcileLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.default_manifest = BaseManifest(
            path=Path("default_manifest.yaml"),
            project_name="base-defaults",
            brewfile=None,
            artifacts=(),
        )
        self.manifest = BaseManifest(
            path=Path("base_manifest.yaml"),
            project_name="demo",
            brewfile=None,
            artifacts=(),
        )

    def test_dry_run_logs_plan_completion_without_claiming_setup_was_applied(self) -> None:
        ctx = fake_context()

        with (
            mock.patch("base_setup.setup_reconcile.reconcile_brewfile"),
            mock.patch("base_setup.setup_reconcile.reconcile_mise"),
            mock.patch("base_setup.setup_reconcile.reconcile_ide_installs"),
            mock.patch("base_setup.setup_reconcile.reconcile_ide_extensions"),
            mock.patch("base_setup.setup_reconcile.reconcile_ide_settings"),
            mock.patch("base_setup.setup_reconcile.reconcile_uv_project"),
            mock.patch("base_setup.setup_reconcile.reconcile_test_requirements"),
        ):
            engine.reconcile_manifest(ctx, self.default_manifest, self.manifest, dry_run=True)

        messages = [call.args for call in ctx.log.info.call_args_list]
        self.assertIn(("[DRY-RUN] Setup plan for project '%s' is complete.", "demo"), messages)
        self.assertNotIn(("Project '%s' setup is complete.", "demo"), messages)

    def test_applied_setup_logs_setup_completion(self) -> None:
        ctx = fake_context()

        with (
            mock.patch("base_setup.setup_reconcile.reconcile_brewfile"),
            mock.patch("base_setup.setup_reconcile.reconcile_mise"),
            mock.patch("base_setup.setup_reconcile.reconcile_ide_installs"),
            mock.patch("base_setup.setup_reconcile.reconcile_ide_extensions"),
            mock.patch("base_setup.setup_reconcile.reconcile_ide_settings"),
            mock.patch("base_setup.setup_reconcile.reconcile_uv_project"),
            mock.patch("base_setup.setup_reconcile.reconcile_test_requirements"),
        ):
            engine.reconcile_manifest(ctx, self.default_manifest, self.manifest, dry_run=False)

        ctx.log.info.assert_any_call("Project '%s' setup is complete.", "demo")
