from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from base_setup import ci_json


class BinaryStdout:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()


class BaseCiRendererTests(unittest.TestCase):
    def test_compact_setup_output_lines_strips_log_prefixes(self) -> None:
        self.assertEqual(
            ci_json.compact_setup_output_lines(
                [
                    "2026-06-10 10:15:32 INFO    setup_common.sh:122 Homebrew is already installed.",
                    "",
                    "plain detail",
                    "2026-06-10 10:15:33 ERROR   setup_common.sh:801 Python project setup layer failed.",
                ]
            ),
            [
                "Homebrew is already installed.",
                "plain detail",
                "Python project setup layer failed.",
            ],
        )

    def test_error_payload_prefers_stderr_and_includes_output_lines(self) -> None:
        payload = ci_json.build_setup_payload(
            project="demo",
            exit_code=17,
            stdout_lines=["stdout fallback"],
            stderr_lines=[
                "2026-06-10 10:15:32 INFO    setup_common.sh:122 Homebrew is already installed.",
                "2026-06-10 10:15:33 ERROR   setup_common.sh:801 Python project setup layer failed.",
            ],
        )

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["output"], "Python project setup layer failed.")
        self.assertEqual(
            payload["output_lines"],
            [
                "Homebrew is already installed.",
                "Python project setup layer failed.",
            ],
        )

    def test_success_payload_omits_output_lines(self) -> None:
        payload = ci_json.build_setup_payload(
            project="demo",
            exit_code=0,
            stdout_lines=["Project setup finished."],
            stderr_lines=[],
        )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["output"], "Project setup finished.")
        self.assertNotIn("output_lines", payload)

    def test_serialized_payload_preserves_utf8_characters(self) -> None:
        payload = ci_json.build_setup_payload(
            project="démo",
            exit_code=17,
            stdout_lines=[],
            stderr_lines=["2026-06-10 10:15:33 ERROR   setup_common.sh:801 Café setup failed for 東京."],
        )

        rendered = ci_json.serialize_payload(payload)

        self.assertIn('"project": "démo"', rendered)
        self.assertIn('"output": "Café setup failed for 東京."', rendered)
        self.assertNotIn("\\u00e9", rendered)
        self.assertNotIn("\\u6771", rendered)
        self.assertEqual(json.loads(rendered), payload)

    def test_main_renders_payload_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stdout_file = Path(tmpdir) / "stdout.log"
            stderr_file = Path(tmpdir) / "stderr.log"
            stdout_file.write_text("ignored stdout\n", encoding="utf-8")
            stderr_file.write_text(
                "2026-06-10 10:15:33 ERROR   setup_common.sh:801 Café setup failed for 東京.\n",
                encoding="utf-8",
            )
            stdout = BinaryStdout()

            original_stdout = ci_json.sys.stdout
            try:
                ci_json.sys.stdout = stdout  # type: ignore[assignment]
                status = ci_json.main(
                    [
                        "setup-json",
                        "--project",
                        "démo",
                        "--exit-code",
                        "17",
                        "--stdout-file",
                        str(stdout_file),
                        "--stderr-file",
                        str(stderr_file),
                    ]
                )
            finally:
                ci_json.sys.stdout = original_stdout

        self.assertEqual(status, 0)
        payload = json.loads(stdout.buffer.getvalue().decode("utf-8"))
        self.assertEqual(payload["project"], "démo")
        self.assertEqual(payload["output"], "Café setup failed for 東京.")


if __name__ == "__main__":
    unittest.main()
