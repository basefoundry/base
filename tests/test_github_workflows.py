import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
FULL_COMMIT_SHA_ACTION_REF = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def load_workflow(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


def workflow_steps(path: Path) -> list[tuple[str, int, dict]]:
    workflow = load_workflow(path)
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict), f"{path} jobs did not parse as a YAML mapping"

    steps: list[tuple[str, int, dict]] = []
    for job_name, job in jobs.items():
        assert isinstance(job, dict), f"{path} job {job_name} did not parse as a YAML mapping"
        job_steps = job.get("steps", [])
        assert isinstance(job_steps, list), f"{path} job {job_name} steps did not parse as a list"
        steps.extend(
            (job_name, index, step)
            for index, step in enumerate(job_steps)
            if isinstance(step, dict)
        )
    return steps


def workflow_action_references_without_full_sha() -> list[str]:
    unpinned: list[str] = []
    for path in workflow_files():
        for job_name, index, step in workflow_steps(path):
            uses = step.get("uses")
            if not isinstance(uses, str) or uses.startswith("./"):
                continue
            if not FULL_COMMIT_SHA_ACTION_REF.match(uses):
                unpinned.append(f"{path.name}:{job_name}:steps[{index}] uses {uses}")
    return unpinned


def workflow_step_by_name(job: dict, name: str) -> dict:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    matches = [step for step in steps if isinstance(step, dict) and step.get("name") == name]
    assert len(matches) == 1, f"Expected exactly one workflow step named {name!r}, found {len(matches)}."
    return matches[0]


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


def test_all_workflow_action_uses_are_pinned_to_full_commit_sha() -> None:
    unpinned = workflow_action_references_without_full_sha()

    assert not unpinned, unpinned


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


def test_macos_smoke_tests_cover_bootstrap_dry_run_routes() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    macos_job = workflow["jobs"]["macos"]
    bootstrap_step = workflow_step_by_name(macos_job, "Run bootstrap dry-run install-route checks")
    run_command = bootstrap_step["run"]

    assert "./bootstrap.sh --dry-run --brew" in run_command
    assert './bootstrap.sh --dry-run --source --install-dir "$GITHUB_WORKSPACE"' in run_command
    assert "basectl setup" in run_command
    assert "basectl update-profile" in run_command


def test_project_intake_requires_base_project_token() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "project-intake.yml")
    sync_job = workflow["jobs"]["sync"]
    reconcile_step = workflow_step_by_name(sync_job, "Reconcile Project item")
    run_command = reconcile_step["run"]

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
