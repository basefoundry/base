from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints
from unittest import mock

from base_setup import python_policy
from base_setup.manifest import BaseManifest
from base_setup.manifest import PythonConfig
from base_setup.python_policy import PythonInterpreter
from base_setup.python_policy import PythonSpecifier
from base_setup.python_policy import python_interpreter_availability_check
from base_setup.python_policy import python_requirement_policy_check
from base_setup.python_policy import python_requirement_checks
from base_setup.python_policy import specifier_allows_version


def manifest_with_python_requirement(requirement: str | None) -> BaseManifest:
    return BaseManifest(
        path=Path("base_manifest.yaml"),
        project_name="demo",
        brewfile=None,
        artifacts=(),
        python=PythonConfig(requires_python=requirement),
    )


class PythonPolicyTests(unittest.TestCase):

    def test_default_python_requirement_has_no_policy_check(self) -> None:
        self.assertIsNone(python_requirement_policy_check(manifest_with_python_requirement(None)))

    def test_supported_exact_python_minor_requirements_are_ok(self) -> None:
        for requirement in ("3.10", "3.11", "3.12", "3.13"):
            with self.subTest(requirement=requirement):
                check = python_requirement_policy_check(manifest_with_python_requirement(requirement))

            self.assertIsNotNone(check)
            assert check is not None
            self.assertTrue(check.ok)
            self.assertEqual(check.finding_id, "BASE-P170")
            self.assertEqual(check.details["requested"], requirement)
            self.assertEqual(check.details["selected_version"], requirement)
            self.assertIn(f"selects supported Python {requirement}", check.message)

    def test_supported_python_range_selects_highest_supported_minor(self) -> None:
        check = python_requirement_policy_check(manifest_with_python_requirement(">=3.11,<3.14"))

        self.assertIsNotNone(check)
        assert check is not None
        self.assertTrue(check.ok)
        self.assertEqual(check.details["requested"], ">=3.11,<3.14")
        self.assertEqual(check.details["selected_version"], "3.13")

    def test_rejects_python_requirements_below_supported_window(self) -> None:
        for requirement in ("3.9", "<3.10"):
            with self.subTest(requirement=requirement):
                check = python_requirement_policy_check(manifest_with_python_requirement(requirement))

            self.assertIsNotNone(check)
            assert check is not None
            self.assertFalse(check.ok)
            self.assertEqual(check.finding_id, "BASE-P170")
            self.assertIn("older than Base supports", check.message)
            self.assertIn("3.10 through 3.13", check.fix)

    def test_rejects_python_requirements_above_supported_window(self) -> None:
        check = python_requirement_policy_check(manifest_with_python_requirement(">=3.14"))

        self.assertIsNotNone(check)
        assert check is not None
        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P170")
        self.assertIn("newer than Base supports", check.message)
        self.assertIn("3.10 through 3.13", check.fix)

    def test_invalid_python_requirement_reports_policy_error(self) -> None:
        check = python_requirement_policy_check(manifest_with_python_requirement("=>3.11"))

        self.assertIsNotNone(check)
        assert check is not None
        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P170")
        self.assertIn("cannot parse", check.message)

    def test_interpreter_availability_reports_supported_but_missing_python(self) -> None:
        check = python_interpreter_availability_check(
            manifest_with_python_requirement("3.12"),
            resolve_interpreter=lambda _selected_version: None,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertFalse(check.ok)
        self.assertEqual(check.finding_id, "BASE-P171")
        self.assertIn("Python 3.12 is not available", check.message)
        self.assertIn("Install Python 3.12", check.fix)

    def test_interpreter_availability_reports_supported_python_path(self) -> None:
        python_path = Path("/opt/homebrew/opt/python@3.11/bin/python3.11")
        check = python_interpreter_availability_check(
            manifest_with_python_requirement("3.11"),
            resolve_interpreter=lambda _selected_version: PythonInterpreter(
                path=python_path,
                version=(3, 11),
            ),
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertTrue(check.ok)
        self.assertEqual(check.finding_id, "BASE-P171")
        self.assertEqual(check.details["python"], str(python_path))
        self.assertEqual(check.details["selected_version"], "3.11")

    def test_resolve_interpreter_annotations_allow_none_default(self) -> None:
        requirement_hints = get_type_hints(python_policy.python_requirement_checks)
        availability_hints = get_type_hints(python_policy.python_interpreter_availability_check)

        self.assertEqual(
            requirement_hints["resolve_interpreter"],
            python_policy.ResolvePythonInterpreter | None,
        )
        self.assertEqual(
            availability_hints["resolve_interpreter"],
            python_policy.ResolvePythonInterpreter | None,
        )

    def test_interpreter_availability_uses_explicit_guard_for_missing_selected_version(self) -> None:
        policy = SimpleNamespace(ok=True, selected_version=None)

        with mock.patch("base_setup.python_policy.evaluate_python_requirement", return_value=policy):
            with self.assertRaisesRegex(ValueError, "selected Python version"):
                python_interpreter_availability_check(manifest_with_python_requirement("3.12"))

    def test_specifier_allows_version_rejects_unsupported_operator_with_value_error(self) -> None:
        specifier = PythonSpecifier("~=", (3, 11, 0))

        with self.assertRaisesRegex(ValueError, "unsupported Python specifier operator"):
            specifier_allows_version(specifier, (3, 11, 0))

    def test_python_requirement_checks_include_policy_and_interpreter_availability(self) -> None:
        checks = python_requirement_checks(
            manifest_with_python_requirement("3.10"),
            resolve_interpreter=lambda _selected_version: PythonInterpreter(
                path=Path("/usr/local/bin/python3.10"),
                version=(3, 10),
            ),
        )

        self.assertEqual([check.finding_id for check in checks], ["BASE-P170", "BASE-P171"])
        self.assertTrue(all(check.ok for check in checks))
