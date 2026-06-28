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


def test_project_intake_requires_base_project_token() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "project-intake.yml")
    sync_job = workflow["jobs"]["sync"]
    run_command = sync_job["steps"][0]["run"]

    assert sync_job["env"]["GH_TOKEN"] == "${{ secrets.BASE_PROJECT_TOKEN }}"
    assert "github.token" not in run_command
    assert "BASE_PROJECT_TOKEN secret is required for Project Intake." in run_command
    assert "gh auth token | gh secret set BASE_PROJECT_TOKEN --repo $GITHUB_REPOSITORY" in run_command


def test_skills_workflow_generates_current_guidance_without_indent_stripping() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "skills.yml")
    create_steps = workflow["jobs"]["create"]["steps"]
    run_commands = "\n".join(step.get("run", "") for step in create_steps if isinstance(step, dict))

    assert "AI_CONTEXT.md" not in run_commands
    assert ".ai-context/README.md" in run_commands
    assert "sed -i 's/^" not in run_commands
