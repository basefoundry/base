from __future__ import annotations

import unittest
from unittest import mock

from base_dev import profile_output
from base_dev.checks import DevCheck


class ProfileCheckOutputTests(unittest.TestCase):
    def test_text_output_routes_findings_by_status_and_preserves_exit_status(self) -> None:
        warning_check = DevCheck(
            name="optional-tool",
            ok=False,
            message="Optional developer tool is not installed.",
            fix="Install the optional developer tool.",
            status="warn",
        )
        error_check = DevCheck(
            name="required-tool",
            ok=False,
            message="Required developer tool is not installed.",
            fix="Install the required developer tool.",
        )

        warning_ctx = mock.Mock()
        warning_status = profile_output.print_check_results(
            warning_ctx,
            (warning_check,),
            output_format="text",
            profiles=("dev",),
        )

        self.assertEqual(warning_status, 0)
        warning_ctx.log.warning.assert_called_once_with(warning_check.message)
        warning_ctx.log.error.assert_not_called()

        error_ctx = mock.Mock()
        error_status = profile_output.print_check_results(
            error_ctx,
            (error_check,),
            output_format="text",
            profiles=("dev",),
        )

        self.assertEqual(error_status, 1)
        error_ctx.log.error.assert_called_once_with(error_check.message)
        error_ctx.log.warning.assert_not_called()


if __name__ == "__main__":
    unittest.main()
