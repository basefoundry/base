from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

from base_cli.command_protocol import dumps_record
from base_cli.command_protocol import dumps_records


def project_command_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "project_name": "demo",
        "project_root": "/tmp/work space/demo",
        "manifest_path": "/tmp/work space/demo/base_manifest.yaml",
        "project_venv_dir": "/tmp/work space/demo/.venv",
        "uses_uv_manager": False,
        "manifest_command_trust_required": True,
        "command": "printf 'tab=\t unicode=λ newline=\n control=\x01'",
        "runner": None,
    }
    record.update(overrides)
    return record


class BaseCliCommandProtocolBashTests(unittest.TestCase):
    def test_python_project_list_framing_is_consumed_by_standalone_completion_reader(self) -> None:
        payload = dumps_records(
            "project-list-entry",
            [
                {"project_name": "base", "project_root": "/tmp/base"},
                {"project_name": "demo", "project_root": "/tmp/work space/λ demo"},
            ],
        )
        repo_root = Path(__file__).resolve().parents[1]
        completion_script = repo_root / "lib" / "shell" / "completions" / "basectl_completion.sh"
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                'source "$COMPLETION_SCRIPT"; '
                '_base_basectl_completion_project_names_from_protocol "$PAYLOAD" || exit; '
                'printf "%s\\n" "$_BASE_BASECTL_COMPLETION_PROJECT_NAMES_DECODED"',
            ],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "COMPLETION_SCRIPT": str(completion_script), "PAYLOAD": payload},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "base\ndemo\n")

    def test_python_command_framing_is_consumed_by_runtime_bash_decoder(self) -> None:
        command = "printf 'tab=\t unicode=λ newline=\n control=\x01'"
        payload = dumps_record(
            "project-command",
            project_command_record(command=command),
        )
        repo_root = Path(__file__).resolve().parents[1]
        decoder_script = repo_root / "lib" / "bash" / "runtime" / "command_protocol.sh"
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$DECODER_SCRIPT"; '
                'base_command_protocol_decode_one project-command "$PAYLOAD" || exit; '
                '[[ "${BASE_COMMAND_PROTOCOL_FIELDS[command]}" == "$EXPECTED_COMMAND" ]] || exit 2; '
                '[[ "${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}" == "/tmp/work space/demo" ]] || exit 3; '
                '[[ "${BASE_COMMAND_PROTOCOL_NULL_FIELDS[runner]:-}" == 1 ]] || exit 4; '
                'printf "decoded\\n"',
            ],
            check=False,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "DECODER_SCRIPT": str(decoder_script),
                "EXPECTED_COMMAND": command,
                "PAYLOAD": payload,
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "decoded\n")


if __name__ == "__main__":
    unittest.main()
