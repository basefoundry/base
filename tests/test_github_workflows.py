import ast
import inspect
import os
import re
import subprocess
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


def project_intake_run_command() -> str:
    workflow = load_workflow(WORKFLOW_DIR / "project-intake.yml")
    sync_job = workflow["jobs"]["sync"]
    reconcile_step = workflow_step_by_name(sync_job, "Reconcile Project item")

    return reconcile_step["run"]


def write_project_intake_mocks(tmp_path: Path) -> Path:
    mockbin = tmp_path / "bin"
    mockbin.mkdir()

    gh_mock = mockbin / "gh"
    gh_mock.write_text(
        """#!/usr/bin/env bash
set -u

printf '%s\\n' "$*" >> "${PROJECT_INTAKE_STATE:?}/gh.log"

case "${1:-} ${2:-}" in
  "issue view")
    count_file="${PROJECT_INTAKE_STATE:?}/issue-view-count"
    count=0
    [[ ! -f "$count_file" ]] || count="$(cat "$count_file")"
    count=$((count + 1))
    printf '%s\\n' "$count" > "$count_file"

    if [[ "${PROJECT_INTAKE_AUTH_FAIL:-}" == "1" ]]; then
      printf '401 Unauthorized: Bad credentials\\n' >&2
      exit 1
    fi

    if [[ "${PROJECT_INTAKE_RATE_LIMIT_ONCE:-}" == "1" && "$count" == "1" ]]; then
      printf 'GraphQL: API rate limit already exceeded\\n' >&2
      printf 'Retry-After: 7\\n' >&2
      exit 1
    fi

    if [[ "${PROJECT_INTAKE_WARN_ON_SUCCESS:-}" == "1" ]]; then
      printf 'warning: gh emitted a non-fatal notice\\n' >&2
    fi

    printf '{"state":"OPEN","url":"https://github.com/basefoundry/base/issues/1311"}\\n'
    ;;
  "project list")
    printf '{"projects":[{"title":"base","number":1}]}\\n'
    ;;
  "project view")
    printf 'PVT_project\\n'
    ;;
  "project item-add")
    printf 'PVTI_item\\n'
    ;;
  "project item-list")
    printf '{"items":[{"id":"PVTI_item"}]}\\n'
    ;;
  "project field-list")
    cat <<'JSON'
{"fields":[
  {"name":"Status","id":"F_status","options":[{"name":"Backlog","id":"O_backlog"},{"name":"Done","id":"O_done"}]},
  {"name":"Priority","id":"F_priority","options":[{"name":"P2","id":"O_p2"}]},
  {"name":"Size","id":"F_size","options":[{"name":"S","id":"O_s"}]},
  {"name":"Area","id":"F_area","options":[{"name":"Product","id":"O_product"}]},
  {"name":"Initiative","id":"F_initiative","options":[{"name":"Adoption Polish","id":"O_adoption"}]}
]}
JSON
    ;;
  "project item-edit")
    printf '%s\\n' "$*" >> "${PROJECT_INTAKE_STATE:?}/edits.log"
    ;;
  *)
    printf 'unexpected gh command: %s\\n' "$*" >&2
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    gh_mock.chmod(0o755)

    sleep_mock = mockbin / "sleep"
    sleep_mock.write_text(
        """#!/usr/bin/env bash
set -u

printf '%s\\n' "$*" >> "${PROJECT_INTAKE_STATE:?}/sleep.log"
""",
        encoding="utf-8",
    )
    sleep_mock.chmod(0o755)

    return mockbin


def project_intake_env(tmp_path: Path, mockbin: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "BASE_PROJECT_OWNER": "basefoundry",
            "BASE_PROJECT_TITLE": "base",
            "BASE_PROJECT_ISSUE_NUMBER": "1311",
            "BASE_PROJECT_DEFAULT_OPEN_STATUS": "Backlog",
            "BASE_PROJECT_DEFAULT_CLOSED_STATUS": "Done",
            "BASE_PROJECT_DEFAULT_PRIORITY": "P2",
            "BASE_PROJECT_DEFAULT_SIZE": "S",
            "BASE_PROJECT_DEFAULT_AREA": "Product",
            "BASE_PROJECT_DEFAULT_INITIATIVE": "Adoption Polish",
            "GH_TOKEN": "test-token",
            "GITHUB_REPOSITORY": "basefoundry/base",
            "PROJECT_INTAKE_STATE": str(tmp_path),
            "PATH": f"{mockbin}:{env['PATH']}",
        }
    )
    return env


def run_project_intake_script(tmp_path: Path, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    mockbin = write_project_intake_mocks(tmp_path)
    env = project_intake_env(tmp_path, mockbin)
    env.update(env_overrides)

    return subprocess.run(
        ["bash", "-c", project_intake_run_command()],
        check=False,
        capture_output=True,
        env=env,
        text=True,
        timeout=30,
    )


def test_project_intake_script_runner_uses_subprocess_timeout() -> None:
    tree = ast.parse(inspect.getsource(run_project_intake_script))
    subprocess_run_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
    ]

    assert len(subprocess_run_calls) == 1
    assert any(keyword.arg == "timeout" for keyword in subprocess_run_calls[0].keywords)


def test_all_workflows_cancel_superseded_runs() -> None:
    missing = [path.name for path in workflow_files() if "concurrency" not in load_workflow(path)]

    assert not missing, missing


def test_all_workflows_declare_top_level_permissions() -> None:
    missing = [path.name for path in workflow_files() if "permissions" not in load_workflow(path)]

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
    run_command = project_intake_run_command()

    assert sync_job["env"]["GH_TOKEN"] == "${{ secrets.BASE_PROJECT_TOKEN }}"
    assert "github.token" not in run_command
    assert "BASE_PROJECT_TOKEN secret is required for Project Intake." in run_command
    assert "gh auth token | gh secret set BASE_PROJECT_TOKEN --repo $GITHUB_REPOSITORY" in run_command


def test_project_intake_classifies_rate_limits_and_auth_failures() -> None:
    run_command = project_intake_run_command()

    assert "project_intake_gh()" in run_command
    assert "project_intake_is_retryable_api_failure()" in run_command
    assert "project_intake_retry_delay_seconds()" in run_command
    assert "Retry-After" in run_command
    assert "x-ratelimit-reset" in run_command
    assert "retrying once" in run_command
    assert 'sleep "$retry_delay"' in run_command
    assert "Bad credentials" in run_command
    assert "Rotate BASE_PROJECT_TOKEN and rerun this workflow_dispatch" in run_command
    assert 'project_intake_gh "view issue" gh issue view' in run_command
    assert 'project_intake_gh "list Projects" gh project list' in run_command
    assert 'project_intake_gh "add Project item" gh project item-add' in run_command
    assert 'project_intake_gh "set Project field $field_name" gh project item-edit' in run_command


def test_project_intake_retries_rate_limited_operations_once(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_RATE_LIMIT_ONCE="1")

    assert result.returncode == 0, result.stderr
    assert "GitHub API pressure during Project Intake: view issue" in result.stderr
    assert "retrying once" in result.stderr
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "7\n"
    assert (tmp_path / "issue-view-count").read_text(encoding="utf-8") == "2\n"
    assert "Synced issue #1311 into Project base." in result.stdout


def test_project_intake_keeps_success_stderr_out_of_json_stdout(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_WARN_ON_SUCCESS="1")

    assert result.returncode == 0, result.stderr
    assert "warning: gh emitted a non-fatal notice" in result.stderr
    assert "warning: gh emitted a non-fatal notice" not in result.stdout
    assert "Synced issue #1311 into Project base." in result.stdout


def test_project_intake_auth_failures_do_not_retry(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_AUTH_FAIL="1")

    assert result.returncode != 0
    assert "GitHub authentication failed during Project Intake: view issue" in result.stderr
    assert "Rotate BASE_PROJECT_TOKEN and rerun this workflow_dispatch" in result.stderr
    assert "Bad credentials" in result.stderr
    assert "retrying once" not in result.stderr
    assert not (tmp_path / "sleep.log").exists()
    assert (tmp_path / "issue-view-count").read_text(encoding="utf-8") == "1\n"


def test_skills_workflow_generates_current_guidance_without_indent_stripping() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "skills.yml")
    create_steps = workflow["jobs"]["create"]["steps"]
    run_commands = "\n".join(step.get("run", "") for step in create_steps if isinstance(step, dict))

    assert "AI_CONTEXT.md" not in run_commands
    assert ".ai-context/README.md" in run_commands
    assert "sed -i 's/^" not in run_commands
