from __future__ import annotations

import os
import subprocess
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


class PythonPolicyDiscoveryTests(unittest.TestCase):

    def test_requirement_parser_accepts_patch_versions_and_whitespace(self) -> None:
        cases = (
            ("3.11.7", (3, 11)),
            (" >=3.11, <3.14 ", (3, 13)),
            (" 3.12 ", (3, 12)),
        )
        for requirement, expected_version in cases:
            with self.subTest(requirement=requirement):
                policy = python_policy.evaluate_python_requirement(requirement)

            self.assertTrue(policy.ok)
            self.assertEqual(policy.selected_version, expected_version)

    def test_requirement_parser_rejects_invalid_forms(self) -> None:
        for requirement in ("", "3", "=>3.11", ">=3.11,", "~=3.11"):
            with self.subTest(requirement=requirement):
                policy = python_policy.evaluate_python_requirement(requirement)

            self.assertFalse(policy.ok)
            self.assertIsNone(policy.selected_version)
            self.assertEqual(policy.reason, "invalid")
            self.assertEqual(policy.error, "cannot parse this Python requirement")

    def test_requirement_parser_covers_supported_comparison_operators(self) -> None:
        cases = (
            ("==3.10.1", (3, 10)),
            (">=3.10.0", (3, 13)),
            ("<=3.13.9", (3, 13)),
            (">3.12.9", (3, 13)),
            ("<3.11.0", (3, 10)),
        )
        for requirement, expected_version in cases:
            with self.subTest(requirement=requirement):
                policy = python_policy.evaluate_python_requirement(requirement)

            self.assertTrue(policy.ok)
            self.assertEqual(policy.selected_version, expected_version)

    def test_requirement_parser_reports_stable_boundary_reasons(self) -> None:
        cases = (
            ("<3.10", "asks for Python older than Base supports"),
            (">3.13", "asks for Python newer than Base supports"),
        )
        for requirement, expected_reason in cases:
            with self.subTest(requirement=requirement):
                policy = python_policy.evaluate_python_requirement(requirement)

            self.assertFalse(policy.ok)
            self.assertEqual(policy.error, expected_reason)

    def test_interpreter_candidates_prioritize_explicit_override(self) -> None:
        override = Path("/custom/python")
        with mock.patch.dict(os.environ, {"BASE_PROJECT_PYTHON_BIN": str(override)}):
            with mock.patch.object(python_policy.shutil, "which", return_value=None):
                with mock.patch.object(python_policy.sys, "executable", "/current/python"):
                    candidates = python_policy.python_interpreter_candidates((3, 12))

        self.assertEqual(candidates[0], override)
        self.assertEqual(candidates[-1], Path("/current/python"))

    def test_interpreter_candidates_include_homebrew_prefix_and_path_fallbacks(self) -> None:
        prefix = Path("/custom/homebrew/opt/python@3.12")

        def which(command: str) -> str | None:
            if command == "brew":
                return "/custom/homebrew/bin/brew"
            return f"/path/{command}"

        with mock.patch.dict(os.environ, {"BASE_PROJECT_PYTHON_BIN": ""}):
            with mock.patch.object(python_policy.shutil, "which", side_effect=which):
                with mock.patch.object(
                    python_policy,
                    "homebrew_formula_prefix",
                    return_value=prefix,
                ) as prefix_lookup:
                    candidates = python_policy.python_interpreter_candidates((3, 12))

        prefix_lookup.assert_called_once_with("/custom/homebrew/bin/brew", "python@3.12")
        self.assertIn(prefix / "bin" / "python3.12", candidates)
        self.assertIn(Path("/path/python3.12"), candidates)
        self.assertIn(Path("/path/python3"), candidates)

    def test_resolve_interpreter_deduplicates_candidates_in_order(self) -> None:
        duplicate = Path("/custom/python")
        fallback = Path("/fallback/python")
        found = PythonInterpreter(path=fallback, version=(3, 12))
        with mock.patch.object(
            python_policy,
            "python_interpreter_candidates",
            return_value=(duplicate, duplicate, fallback),
        ):
            with mock.patch.object(
                python_policy,
                "inspect_python_interpreter",
                side_effect=[None, found],
            ) as inspect:
                resolved = python_policy.resolve_python_interpreter((3, 12))

        self.assertEqual(resolved, found)
        self.assertEqual(inspect.call_args_list, [mock.call(duplicate), mock.call(fallback)])

    def test_homebrew_prefix_probe_handles_timeout_and_failure(self) -> None:
        with mock.patch.object(
            python_policy.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired("brew", 5),
        ):
            self.assertIsNone(python_policy.homebrew_formula_prefix("brew", "python@3.12"))

        failed = subprocess.CompletedProcess(
            args=["brew", "--prefix", "python@3.12"],
            returncode=1,
            stdout="",
        )
        with mock.patch.object(python_policy.subprocess, "run", return_value=failed):
            self.assertIsNone(python_policy.homebrew_formula_prefix("brew", "python@3.12"))

    def test_inspect_interpreter_handles_subprocess_failures_and_malformed_output(self) -> None:
        candidate = Path("/fake/python")
        with mock.patch.object(Path, "is_file", return_value=True):
            with mock.patch.object(python_policy.os, "access", return_value=True):
                with mock.patch.object(
                    python_policy.subprocess,
                    "run",
                    side_effect=OSError("cannot execute"),
                ):
                    self.assertIsNone(python_policy.inspect_python_interpreter(candidate))

                with mock.patch.object(
                    python_policy.subprocess,
                    "run",
                    side_effect=subprocess.TimeoutExpired(str(candidate), 5),
                ):
                    self.assertIsNone(python_policy.inspect_python_interpreter(candidate))

                malformed = subprocess.CompletedProcess(
                    args=[str(candidate)],
                    returncode=0,
                    stdout="not-a-version\n",
                )
                with mock.patch.object(
                    python_policy.subprocess,
                    "run",
                    return_value=malformed,
                ):
                    self.assertIsNone(python_policy.inspect_python_interpreter(candidate))

    def test_resolve_interpreter_rejects_discovered_version_mismatch(self) -> None:
        candidate = Path("/custom/python3.12")
        discovered = PythonInterpreter(path=candidate, version=(3, 11))
        with mock.patch.object(
            python_policy,
            "python_interpreter_candidates",
            return_value=(candidate,),
        ):
            with mock.patch.object(
                python_policy,
                "inspect_python_interpreter",
                return_value=discovered,
            ):
                self.assertIsNone(python_policy.resolve_python_interpreter((3, 12)))

    def test_interpreter_availability_reports_discovered_version_mismatch(self) -> None:
        check = python_interpreter_availability_check(
            manifest_with_python_requirement("3.12"),
            resolve_interpreter=lambda _selected_version: PythonInterpreter(
                path=Path("/custom/python3.11"),
                version=(3, 11),
            ),
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertFalse(check.ok)
        self.assertIn("reports Python 3.11", check.message)
        self.assertEqual(check.details["actual_version"], "3.11")

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
