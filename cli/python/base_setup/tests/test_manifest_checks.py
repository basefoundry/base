from __future__ import annotations

import unittest

from base_setup import engine
from base_setup import manifest_checks


class ManifestChecksModuleTests(unittest.TestCase):
    def test_engine_reexports_manifest_check_helpers(self) -> None:
        self.assertIs(engine.manifest_checks, manifest_checks.manifest_checks)
        self.assertIs(engine.pre_venv_manifest_checks, manifest_checks.pre_venv_manifest_checks)
        self.assertIs(engine.setup_profile_enabled, manifest_checks.setup_profile_enabled)
        self.assertIs(engine.empty_user_config, manifest_checks.empty_user_config)


if __name__ == "__main__":
    unittest.main()
