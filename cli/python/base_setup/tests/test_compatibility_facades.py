from __future__ import annotations

from pathlib import Path
import unittest

from base_devenv import report as devenv_report_impl
from base_devcontainer import export as devcontainer_export_impl
from base_setup import devenv_report
from base_setup import git_remote
from base_setup import ide
from base_setup import devcontainer_export
from base_setup import engine as setup_engine
from base_setup import manifest_checks
from base_setup import setup_reconcile
from base_trust import trust_store


class CompatibilityFacadeTests(unittest.TestCase):
    def test_git_remote_declares_compatibility_exports(self) -> None:
        self.assertIn("check_git_remote", git_remote.__all__)
        self.assertIn("parse_origin_remote", git_remote.__all__)
        self.assertIn("RemoteInfo", git_remote.__all__)
        self.assertIn("run_git", git_remote.__all__)

    def test_ide_declares_compatibility_exports(self) -> None:
        self.assertIn("effective_ide_config", ide.__all__)
        self.assertIn("check_ide_extensions", ide.__all__)
        self.assertIn("reconcile_ide_settings", ide.__all__)
        self.assertIn("IdeDiagnosticSnapshot", ide.__all__)

    def test_devcontainer_export_declares_compatibility_exports(self) -> None:
        self.assertIn("build_devcontainer_export", devcontainer_export.__all__)
        self.assertIn("write_devcontainer_export", devcontainer_export.__all__)
        self.assertIn("DevcontainerExportError", devcontainer_export.__all__)
        self.assertIs(devcontainer_export.build_devcontainer_export, devcontainer_export_impl.build_devcontainer_export)
        self.assertIs(devcontainer_export.write_devcontainer_export, devcontainer_export_impl.write_devcontainer_export)

    def test_devenv_report_declares_compatibility_exports(self) -> None:
        self.assertIn("build_devenv_report", devenv_report.__all__)
        self.assertIn("dumps_devenv_report_json", devenv_report.__all__)
        self.assertIn("print_devenv_report_text", devenv_report.__all__)
        self.assertIs(devenv_report.build_devenv_report, devenv_report_impl.build_devenv_report)
        self.assertIs(devenv_report.dumps_devenv_report_json, devenv_report_impl.dumps_devenv_report_json)
        self.assertIs(devenv_report.print_devenv_report_text, devenv_report_impl.print_devenv_report_text)

    def test_setup_callers_use_focused_ide_modules(self) -> None:
        manifest_checks_source = Path(manifest_checks.__file__).read_text(encoding="utf-8")
        setup_reconcile_source = Path(setup_reconcile.__file__).read_text(encoding="utf-8")

        self.assertNotIn("from .ide import check_ide_extensions", manifest_checks_source)
        self.assertNotIn("from .ide import check_ide_installs", manifest_checks_source)
        self.assertNotIn("from .ide import check_ide_settings", manifest_checks_source)
        self.assertIn("from .ide_extensions import check_ide_extensions", manifest_checks_source)
        self.assertIn("from .ide_installs import check_ide_installs", manifest_checks_source)
        self.assertIn("from .ide_settings import check_ide_settings", manifest_checks_source)

        self.assertNotIn("from .ide import reconcile_ide_extensions", setup_reconcile_source)
        self.assertNotIn("from .ide import reconcile_ide_installs", setup_reconcile_source)
        self.assertNotIn("from .ide import reconcile_ide_settings", setup_reconcile_source)
        self.assertIn("from .ide_extensions import reconcile_ide_extensions", setup_reconcile_source)
        self.assertIn("from .ide_installs import reconcile_ide_installs", setup_reconcile_source)
        self.assertIn("from .ide_settings import reconcile_ide_settings", setup_reconcile_source)

    def test_setup_engine_uses_focused_devcontainer_package(self) -> None:
        setup_engine_source = Path(setup_engine.__file__).read_text(encoding="utf-8")
        facade_source = Path(devcontainer_export.__file__).read_text(encoding="utf-8")

        self.assertIn("from base_devcontainer.export import build_devcontainer_export", setup_engine_source)
        self.assertIn("from base_devcontainer.export import write_devcontainer_export", setup_engine_source)
        self.assertNotIn("from .devcontainer_export import", setup_engine_source)
        self.assertIn("from base_devcontainer.export import build_devcontainer_export", facade_source)
        self.assertNotIn("def build_devcontainer_export", facade_source)
        self.assertNotIn("@dataclass", facade_source)

    def test_setup_engine_uses_focused_devenv_package(self) -> None:
        setup_engine_source = Path(setup_engine.__file__).read_text(encoding="utf-8")
        facade_source = Path(devenv_report.__file__).read_text(encoding="utf-8")

        self.assertIn("from base_devenv.report import build_devenv_report", setup_engine_source)
        self.assertIn("from base_devenv.report import dumps_devenv_report_json", setup_engine_source)
        self.assertIn("from base_devenv.report import print_devenv_report_text", setup_engine_source)
        self.assertNotIn("from .devenv_report import", setup_engine_source)
        self.assertIn("from base_devenv.report import build_devenv_report", facade_source)
        self.assertNotIn("def build_devenv_report", facade_source)
        self.assertNotIn("@dataclass", facade_source)

    def test_trust_store_uses_focused_git_modules(self) -> None:
        trust_store_source = Path(trust_store.__file__).read_text(encoding="utf-8")

        self.assertNotIn("from base_setup import git_remote", trust_store_source)
        self.assertIn("from base_setup.git_commands import run_git", trust_store_source)
        self.assertIn("from base_setup.git_remote_parse import parse_origin_remote", trust_store_source)


if __name__ == "__main__":
    unittest.main()
