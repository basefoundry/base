from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from base_cli_adapters.config import user_config_path
from base_uninstall import engine


class BaseUninstallTests(unittest.TestCase):
    def test_project_uninstall_removes_only_selected_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            cache = root / "cache"
            project_root = root / "demo"
            manifest_path = project_root / "base_manifest.yaml"
            project_root.mkdir()
            manifest_path.write_text("project:\n  name: demo\n", encoding="utf-8")
            target = engine.ProjectTarget("demo", project_root, manifest_path)

            trust_root = home / ".base.d" / "trust" / "manifest-commands"
            trust_root.mkdir(parents=True)
            selected_record = trust_root / "selected.json"
            selected_record.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project": {
                            "name": "demo",
                            "root": str(project_root),
                            "manifest": str(manifest_path),
                        },
                    }
                ),
                encoding="utf-8",
            )
            other_record = trust_root / "other.json"
            other_record.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project": {
                            "name": "other",
                            "root": str(root / "other"),
                            "manifest": str(root / "other" / "base_manifest.yaml"),
                        },
                    }
                ),
                encoding="utf-8",
            )
            (home / ".base.d" / "demo" / "checks").mkdir(parents=True)
            (home / ".base.d" / "demo" / "checks" / "last.json").write_text("{}", encoding="utf-8")
            (home / ".base.d" / "demo" / ".venv" / "bin").mkdir(parents=True)
            (home / ".base.d" / "demo" / ".venv" / "bin" / "python").touch()
            (cache / "projects" / "demo" / "checkout" / "cache").mkdir(parents=True)
            (cache / "projects" / "other" / "checkout" / "cache").mkdir(parents=True)

            with mock.patch.dict(
                os.environ,
                {"HOME": str(home), "BASE_CACHE_DIR": str(cache)},
                clear=False,
            ):
                with redirect_stdout(StringIO()):
                    status = engine.uninstall_state(target, apply=True, dry_run=False)

            self.assertEqual(status, 0)
            self.assertFalse(selected_record.exists())
            self.assertTrue(other_record.exists())
            self.assertFalse((home / ".base.d" / "demo" / "checks").exists())
            self.assertFalse((home / ".base.d" / "demo" / ".venv").exists())
            self.assertFalse((cache / "projects" / "demo").exists())
            self.assertTrue((cache / "projects" / "other").exists())
            self.assertTrue(manifest_path.exists())

    def test_all_uninstall_clears_workspace_state_and_base_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            cache = root / "cache"
            trust_root = home / ".base.d" / "trust" / "manifest-commands"
            trust_root.mkdir(parents=True)
            (trust_root / "record.json").write_text("{}", encoding="utf-8")
            (home / ".base.d" / "profile.conf").parent.mkdir(parents=True, exist_ok=True)
            (home / ".base.d" / "profile.conf").write_text("BASE_PROFILE_VERSION=1\n", encoding="utf-8")
            (home / ".base.d" / "base" / "checks").mkdir(parents=True)
            (home / ".base.d" / "base" / "checks" / "last.json").write_text("{}", encoding="utf-8")
            config_path = user_config_path(home)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                "workspace:\n  root: /tmp/work\n  manifest: /tmp/work/workspace.yaml\n"
                "github:\n  default_owner: codeforester\n",
                encoding="utf-8",
            )
            (cache / "base" / "cache" / "components").mkdir(parents=True)
            (cache / "base" / "cache" / "components" / "marker").touch()
            (cache / "projects" / "demo" / "checkout").mkdir(parents=True)

            with mock.patch.dict(
                os.environ,
                {"HOME": str(home), "BASE_CACHE_DIR": str(cache)},
                clear=False,
            ):
                with redirect_stdout(StringIO()):
                    status = engine.uninstall_state(None, apply=True, dry_run=False)

            self.assertEqual(status, 0)
            self.assertFalse(trust_root.exists())
            self.assertFalse((home / ".base.d" / "profile.conf").exists())
            self.assertFalse((home / ".base.d" / "base" / "checks").exists())
            self.assertFalse((cache / "base" / "cache").exists())
            self.assertFalse((cache / "projects").exists())
            self.assertNotIn("workspace:", config_path.read_text(encoding="utf-8"))
            self.assertIn("default_owner", config_path.read_text(encoding="utf-8"))

    def test_verify_state_reports_shell_startup_residue(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            (home / ".bashrc").write_text(
                "# >>> base: bashrc managed >>>\n# <<< base: bashrc managed <<<\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                output = StringIO()
                with redirect_stdout(output):
                    status = engine.verify_state(None)

            self.assertEqual(status, 1)
            self.assertIn("managed shell startup section", output.getvalue())

    def test_profile_residue_accepts_partial_marker_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            (home / ".zshrc").write_text("# >>> base: zshrc managed >>>\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                self.assertTrue(engine.profile_residue(home))

    def test_dry_run_does_not_mutate_selected_resources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            cache = root / "cache"
            project_root = root / "demo"
            manifest_path = project_root / "base_manifest.yaml"
            project_root.mkdir()
            manifest_path.write_text("project:\n  name: demo\n", encoding="utf-8")
            check_path = home / ".base.d" / "demo" / "checks"
            check_path.mkdir(parents=True)
            (check_path / "last.json").write_text("{}", encoding="utf-8")
            target = engine.ProjectTarget("demo", project_root, manifest_path)

            with mock.patch.dict(
                os.environ,
                {"HOME": str(home), "BASE_CACHE_DIR": str(cache)},
                clear=False,
            ):
                with redirect_stdout(StringIO()):
                    status = engine.uninstall_state(target, apply=False, dry_run=True)

            self.assertEqual(status, 0)
            self.assertTrue((check_path / "last.json").exists())

