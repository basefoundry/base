from __future__ import annotations

import unittest

from base_setup.prerequisites import HomebrewPackageCheckRequest


class HomebrewPackageCheckRequestTests(unittest.TestCase):
    def test_for_artifact_builds_stable_homebrew_messages(self) -> None:
        request = HomebrewPackageCheckRequest.for_artifact(
            project="demo",
            name="terraform",
            manager="apt",
            version="1.8.5",
            package="terraform",
            timeout_seconds=11,
            details={"target": "system"},
        )

        self.assertEqual(request.name, "terraform")
        self.assertEqual(request.manager, "apt")
        self.assertEqual(request.version, "1.8.5")
        self.assertEqual(request.package, "terraform")
        self.assertEqual(request.timeout_seconds, 11)
        self.assertEqual(request.unsupported_manager_message, "Artifact manager 'apt' is not implemented.")
        self.assertEqual(request.unsupported_manager_fix, "basectl setup demo")
        self.assertEqual(request.unsupported_manager_finding_id, "BASE-P030")
        self.assertEqual(
            request.unsupported_version_message,
            "Homebrew artifact 'terraform' specifies version '1.8.5', "
            "but Base only supports Homebrew artifact version 'latest' right now.",
        )
        self.assertEqual(
            request.unsupported_version_fix,
            "Update 'terraform' in the project manifest to use version 'latest'.",
        )
        self.assertEqual(request.unsupported_version_finding_id, "BASE-P031")
        self.assertEqual(request.missing_homebrew_message, "Homebrew is required to check artifact 'terraform'.")
        self.assertEqual(request.missing_homebrew_fix, "basectl setup")
        self.assertEqual(request.missing_homebrew_finding_id, "BASE-P032")
        self.assertEqual(request.timeout_message, "Homebrew check for artifact 'terraform' timed out after 11 seconds.")
        self.assertEqual(request.timeout_fix, "Retry 'basectl doctor demo' or inspect Homebrew with 'brew doctor'.")
        self.assertEqual(request.timeout_finding_id, "BASE-P033")
        self.assertEqual(request.outdated_message, "Artifact 'terraform' is outdated via Homebrew package 'terraform'.")
        self.assertEqual(request.outdated_fix, "basectl setup demo")
        self.assertEqual(request.package_finding_id, "BASE-P033")
        self.assertEqual(
            request.installed_message,
            "Artifact 'terraform' is installed via Homebrew package 'terraform' and is current.",
        )
        self.assertEqual(
            request.missing_package_message,
            "Artifact 'terraform' is not installed via Homebrew package 'terraform'.",
        )
        self.assertEqual(request.missing_package_fix, "basectl setup demo")
        self.assertEqual(request.details, {"target": "system"})
