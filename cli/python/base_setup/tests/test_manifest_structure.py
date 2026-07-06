from __future__ import annotations

from pathlib import Path
import unittest

from base_setup import manifest
from base_setup import manifest_build
from base_setup import manifest_release


class ManifestReaderStructureTests(unittest.TestCase):
    def test_build_and_release_readers_live_outside_manifest_facade(self) -> None:
        manifest_source = Path(manifest.__file__).read_text(encoding="utf-8")
        build_source = Path(manifest_build.__file__).read_text(encoding="utf-8")
        release_source = Path(manifest_release.__file__).read_text(encoding="utf-8")

        self.assertIn("def read_build_config", build_source)
        self.assertIn("def read_release_config", release_source)
        self.assertNotIn("def _read_build(", manifest_source)
        self.assertNotIn("def _read_build_target", manifest_source)
        self.assertNotIn("def _read_release(", manifest_source)
        self.assertNotIn("def _read_release_github", manifest_source)
