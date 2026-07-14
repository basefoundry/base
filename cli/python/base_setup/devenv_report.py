from __future__ import annotations

from base_devenv.report import CLASSIFICATIONS
from base_devenv.report import DevenvCompatibilityReport
from base_devenv.report import DevenvFieldClassification
from base_devenv.report import add_artifact_fields
from base_devenv.report import add_ide_fields
from base_devenv.report import add_project_owned_fields
from base_devenv.report import add_python_fields
from base_devenv.report import build_devenv_report
from base_devenv.report import devenv_report_to_json
from base_devenv.report import dumps_devenv_report_json
from base_devenv.report import field_to_json
from base_devenv.report import print_devenv_report_text
from base_devenv.report import summary_counts


# Compatibility exports for callers that imported Nix/devenv report helpers from
# base_setup before the focused base_devenv package existed.
__all__ = (
    "CLASSIFICATIONS",
    "DevenvCompatibilityReport",
    "DevenvFieldClassification",
    "add_artifact_fields",
    "add_ide_fields",
    "add_project_owned_fields",
    "add_python_fields",
    "build_devenv_report",
    "devenv_report_to_json",
    "dumps_devenv_report_json",
    "field_to_json",
    "print_devenv_report_text",
    "summary_counts",
)
