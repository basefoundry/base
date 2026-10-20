from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import jsonschema
from base_matrix.runner import Step
from base_matrix.runner import _run_step


REPO_ROOT = Path(__file__).resolve().parents[4]
SCENARIO = REPO_ROOT / "tests/fixtures/macos_matrix/trivial.json"
SCENARIO_SCHEMA = REPO_ROOT / "docs/schemas/macos-matrix-scenario.json"
RESULT_SCHEMA = REPO_ROOT / "docs/schemas/macos-matrix-result.json"


def _environment(stub_dir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PATH"] = f"{stub_dir}{os.pathsep}{environment['PATH']}"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "cli/python"), str(REPO_ROOT / "lib/python"), environment.get("PYTHONPATH", "")]
    )
    return environment


def _write_sudo_stub(directory: Path) -> None:
    script = directory / "sudo"
    script.write_text(
        "#!/bin/sh\n"
        "if [ \"${BASE_MATRIX_STUB_MODE:-pass}\" = blocked ]; then exit 1; fi\n"
        "while [ \"$1\" != \"--\" ]; do shift; done\n"
        "shift\n"
        "exec \"$@\"\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


def _run(tmp_path: Path, *args: str, mode: str = "pass") -> subprocess.CompletedProcess[str]:
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir(exist_ok=True)
    _write_sudo_stub(stub_dir)
    environment = _environment(stub_dir)
    environment["BASE_MATRIX_STUB_MODE"] = mode
    return subprocess.run(
        [sys.executable, "-m", "base_matrix", *args],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_validate_accepts_trivial_scenario() -> None:
    scenario_schema = json.loads(SCENARIO_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(scenario_schema).validate(json.loads(SCENARIO.read_text(encoding="utf-8")))
    result = subprocess.run(
        [sys.executable, "-m", "base_matrix", "validate", "--scenario", str(SCENARIO)],
        cwd=REPO_ROOT,
        env=_environment(Path("/nonexistent")),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Scenario valid: trivial v1" in result.stdout


def test_runner_emits_schema_valid_result_for_all_cells(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "run",
        "--scenario",
        str(SCENARIO),
        "--cells",
        "all",
        "--output-dir",
        str(tmp_path / "results"),
    )

    assert result.returncode == 0, result.stderr
    assert sum(
        line.startswith(f"{cell}: passed")
        for line in result.stdout.splitlines()
        for cell in ("source-bash", "source-zsh", "brew-bash", "brew-zsh")
    ) == 4
    run_dir = next((tmp_path / "results").iterdir())
    schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    for cell in ("source-bash", "source-zsh", "brew-bash", "brew-zsh"):
        payload = json.loads((run_dir / f"{cell}.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)
        assert payload["status"] == "passed"
        assert payload["account"].endswith(cell.split("-", 1)[1])
        assert (run_dir / cell / payload["steps"][0]["log_path"]).exists()


def test_runner_refuses_non_matrix_account(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "run",
        "--scenario",
        str(SCENARIO),
        "--cells",
        "source-bash",
        "--user",
        "outside-matrix",
        "--output-dir",
        str(tmp_path / "results"),
    )

    assert result.returncode == 2
    assert "Refusing non-matrix account 'outside-matrix'" in result.stderr


def test_runner_blocks_when_passwordless_runas_is_unavailable(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "run",
        "--scenario",
        str(SCENARIO),
        "--cells",
        "source-bash",
        "--output-dir",
        str(tmp_path / "results"),
        mode="blocked",
    )

    assert result.returncode == 1
    assert "source-bash: blocked" in result.stdout
    run_dir = next((tmp_path / "results").iterdir())
    payload = json.loads((run_dir / "source-bash.json").read_text(encoding="utf-8"))
    assert payload["status"] == "blocked"
    assert payload["preconditions"][0]["finding_ids"] == ["matrix.runas.unavailable"]
    assert payload["steps"] == []


def test_runner_redacts_step_output_in_persistent_log(tmp_path: Path) -> None:
    scenario = tmp_path / "secret.json"
    scenario.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "redaction",
                "version": "1",
                "preconditions": [],
                "steps": [
                    {
                        "id": "secret-output",
                        "command": ["/usr/bin/printf", "TOKEN=ghp_matrix_secret\\n"],
                        "expected_exit": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = _run(
        tmp_path,
        "run",
        "--scenario",
        str(scenario),
        "--cells",
        "source-bash",
        "--output-dir",
        str(tmp_path / "results"),
    )

    assert result.returncode == 0, result.stderr
    run_dir = next((tmp_path / "results").iterdir())
    log_path = run_dir / "source-bash" / "logs" / "01-secret-output.log"
    log_text = log_path.read_text(encoding="utf-8")
    assert "ghp_matrix_secret" not in log_text
    assert "TOKEN=[REDACTED]" in log_text


def test_runner_records_os_error_as_failed_step(tmp_path: Path, monkeypatch) -> None:
    def raise_os_error(*_args, **_kwargs):
        raise OSError("runner unavailable")

    monkeypatch.setattr("base_matrix.runner.subprocess.run", raise_os_error)
    step = Step("missing-runner", ("/bin/true",), 0, (), (), (), (), (), 1.0, None)

    result, passed = _run_step(step, "base-source-bash", REPO_ROOT, tmp_path, "logs/01-step.log")

    assert not passed
    assert result["status"] == "failed"
    assert result["error"] == "runner unavailable"
    assert (tmp_path / "logs/01-step.log").exists()
