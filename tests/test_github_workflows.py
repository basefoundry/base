from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def load_workflow(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


def test_all_workflows_cancel_superseded_runs() -> None:
    missing = [path.name for path in workflow_files() if "concurrency" not in load_workflow(path)]

    assert not missing, missing


def test_all_workflow_jobs_have_timeouts() -> None:
    missing: list[str] = []
    for path in workflow_files():
        jobs = load_workflow(path).get("jobs")
        assert isinstance(jobs, dict), f"{path} jobs did not parse as a YAML mapping"
        for job_name, job in jobs.items():
            assert isinstance(job, dict), f"{path} job {job_name} did not parse as a YAML mapping"
            if "timeout-minutes" not in job:
                missing.append(f"{path.name}:{job_name}")

    assert not missing, missing


def test_python_tests_run_on_supported_minor_versions() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    python_job = workflow["jobs"]["python"]

    assert python_job["strategy"]["matrix"]["python-version"] == [
        "3.10",
        "3.11",
        "3.12",
        "3.13",
    ]
    setup_steps = [
        step
        for step in python_job["steps"]
        if isinstance(step, dict) and step.get("uses", "").startswith("actions/setup-python@")
    ]

    assert len(setup_steps) == 1
    assert setup_steps[0]["name"] == "Set up Python"
    assert setup_steps[0]["with"] == {"python-version": "${{ matrix.python-version }}"}


def test_macos_smoke_tests_cover_shell_compatibility_surfaces() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    macos_job = workflow["jobs"]["macos"]
    run_commands = "\n".join(
        step.get("run", "")
        for step in macos_job["steps"]
        if isinstance(step, dict)
    )

    assert "lib/bash/version/tests/lib_version.bats" in run_commands
    assert "lib/shell/completions/tests/completions.bats" in run_commands
