import ast
import inspect
import re
from pathlib import Path

import yaml

from tests.github_workflow_test_support import (
    issue_branch_policy_run_command,
    project_intake_run_command,
    run_issue_branch_policy_script,
    run_project_intake_script,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
COPILOT_INSTRUCTIONS = REPO_ROOT / ".github" / "copilot-instructions.md"
COPILOT_SETUP_WORKFLOW = WORKFLOW_DIR / "copilot-setup-steps.yml"
BASE_CHECK_WORKFLOW = WORKFLOW_DIR / "base-check.yml"
BASE_PROJECT_CONFIG = REPO_ROOT / ".github" / "base-project.yml"
ISSUE_BRANCH_POLICY_WORKFLOW = WORKFLOW_DIR / "issue-branch-policy.yml"
ISSUE_BRANCH_POLICY_TEMPLATE = REPO_ROOT / "templates" / "issue-branch-policy.yml"
IMPLEMENTATION_ISSUE_TEMPLATE = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "implementation.yml"
FULL_COMMIT_SHA_ACTION_REF = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def load_workflow(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


def load_yaml_mapping(path: Path) -> dict:
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


def test_issue_branch_policy_workflow_is_trusted_and_template_backed() -> None:
    workflow = load_workflow(ISSUE_BRANCH_POLICY_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)
    job = workflow["jobs"]["policy"]
    run_command = issue_branch_policy_run_command()

    assert ISSUE_BRANCH_POLICY_WORKFLOW.read_text(encoding="utf-8") == (
        ISSUE_BRANCH_POLICY_TEMPLATE.read_text(encoding="utf-8")
    )
    assert set(triggers) == {"pull_request_target", "issues", "workflow_dispatch"}
    assert triggers["pull_request_target"] == {
        "types": ["opened", "reopened", "synchronize", "closed"]
    }
    assert triggers["issues"] == {"types": ["labeled", "unlabeled"]}
    assert triggers["workflow_dispatch"]["inputs"] == {
        "pull_request_number": {
            "description": "Pull request number to validate",
            "required": True,
            "type": "string",
        },
        "head_sha": {
            "description": "Head commit SHA used for same-commit concurrency",
            "required": True,
            "type": "string",
        },
    }
    assert workflow["permissions"] == {
        "actions": "write",
        "contents": "read",
        "issues": "read",
        "pull-requests": "read",
        "statuses": "write",
    }
    concurrency_group = workflow["concurrency"]["group"]
    assert "github.event.issue.number" in concurrency_group
    assert "github.event.label.name" in concurrency_group
    assert "github.event.pull_request.head.sha" in concurrency_group
    assert "inputs.head_sha" in concurrency_group
    assert "github.event.pull_request.number" not in concurrency_group
    assert "inputs.pull_request_number" not in concurrency_group
    assert job["name"] == "Publish issue branch policy"
    assert job["timeout-minutes"] == 5
    assert not any("uses" in step for _, _, step in workflow_steps(ISSUE_BRANCH_POLICY_WORKFLOW))
    assert "actions/checkout" not in run_command
    assert "pull_request.head.ref" not in run_command
    assert "${{" not in run_command
    assert "base/issue-branch-policy" in job["env"]["POLICY_CONTEXT"]
    assert job["env"]["EVENT_NAME"] == "${{ github.event_name }}"
    assert job["env"]["EVENT_HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert job["env"]["DISPATCH_HEAD_SHA"] == "${{ inputs.head_sha }}"
    assert job["env"]["PREVIOUS_HEAD_SHA"] == "${{ github.event.before }}"
    assert job["env"]["RUN_SHA"] == "${{ github.sha }}"


def test_issue_branch_policy_accepts_matching_issue_category(tmp_path: Path) -> None:
    result = run_issue_branch_policy_script(tmp_path)
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "Validated enhancement/117-20260714-valid-branch" in result.stdout
    assert "-f state=pending" in statuses
    assert "-f state=success" in statuses
    assert "-f context=base/issue-branch-policy" in statuses
    assert f"statuses/{'a' * 40}" in statuses
    assert f"statuses/{'c' * 40}" not in statuses


def test_issue_branch_policy_validates_after_current_pending_status_failure(
    tmp_path: Path,
) -> None:
    result = run_issue_branch_policy_script(tmp_path, pending_status_fails=True)
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "Unable to publish the pending branch policy status" in result.stderr
    assert "Validated enhancement/117-20260714-valid-branch" in result.stdout
    assert "-f state=pending" in statuses
    assert "-f state=success" in statuses


def test_issue_branch_policy_workflow_dispatch_bootstraps_closed_pr_readiness(
    tmp_path: Path,
) -> None:
    result = run_issue_branch_policy_script(
        tmp_path,
        event_name="workflow_dispatch",
        dispatch_head_sha="a" * 40,
        pull_request_state="closed",
    )
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert f"statuses/{'a' * 40}" in statuses
    assert f"statuses/{'c' * 40}" in statuses
    assert "Issue branch policy workflow is ready" in statuses


def test_issue_branch_policy_stale_dispatch_publishes_no_status_or_readiness(
    tmp_path: Path,
) -> None:
    result = run_issue_branch_policy_script(
        tmp_path,
        event_name="workflow_dispatch",
        dispatch_head_sha="b" * 40,
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "Skipping stale workflow_dispatch for pull request #41" in result.stdout
    assert "pulls/41" in gh_log
    assert "pulls?state=open" not in gh_log
    assert "statuses/" not in gh_log
    assert not (tmp_path / "statuses.log").exists()


def test_issue_branch_policy_fetch_failure_posts_failure_on_known_target(
    tmp_path: Path,
) -> None:
    event_result = run_issue_branch_policy_script(
        tmp_path,
        pull_request_missing=True,
    )
    event_statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert event_result.returncode == 1
    assert f"statuses/{'a' * 40}" in event_statuses
    assert "-f state=failure" in event_statuses

    dispatch_path = tmp_path / "dispatch"
    dispatch_path.mkdir()
    dispatch_result = run_issue_branch_policy_script(
        dispatch_path,
        event_name="workflow_dispatch",
        dispatch_head_sha="b" * 40,
        pull_request_missing=True,
    )
    dispatch_statuses = (dispatch_path / "statuses.log").read_text(encoding="utf-8")

    assert dispatch_result.returncode == 1
    assert f"statuses/{'b' * 40}" in dispatch_statuses
    assert f"statuses/{'a' * 40}" not in dispatch_statuses
    assert f"statuses/{'c' * 40}" not in dispatch_statuses
    assert "-f state=failure" in dispatch_statuses
    assert "Issue branch policy workflow is ready" not in dispatch_statuses


def test_issue_branch_policy_stale_pr_event_repairs_old_sha_without_touching_live_sha(
    tmp_path: Path,
) -> None:
    previous_sha = "a" * 40
    event_sha = "b" * 40
    live_sha = "d" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        event_head_sha=event_sha,
        previous_head_sha=previous_sha,
        pull_request_sha=live_sha,
        open_pull_request_heads=f"42\t{previous_sha}\n41\t{live_sha}",
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "Queued previous-commit validation for pull request #42" in result.stdout
    assert "Skipping stale pull request event" in result.stdout
    assert "inputs[pull_request_number]=42" in gh_log
    assert f"inputs[head_sha]={previous_sha}" in gh_log
    assert f"statuses/{previous_sha}" in statuses
    assert "-f state=pending" in statuses
    assert "-f state=success" not in statuses
    assert "-f state=failure" not in statuses
    assert f"statuses/{event_sha}" not in statuses
    assert f"statuses/{live_sha}" not in statuses


def test_issue_branch_policy_rejects_category_mismatch(tmp_path: Path) -> None:
    result = run_issue_branch_policy_script(
        tmp_path,
        branch="bug/117-20260714-wrong-category",
    )
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 1
    assert "branch category does not match issue #117" in result.stderr
    assert "-f state=failure" in statuses
    assert "-f state=success" not in statuses


def test_issue_branch_policy_fails_shared_sha_when_any_open_pr_is_invalid(
    tmp_path: Path,
) -> None:
    shared_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        open_pull_request_heads=f"42\t{shared_sha}\n41\t{shared_sha}",
        secondary_branch="bug/117-20260714-wrong-category",
        secondary_pull_request_number="42",
        secondary_sha=shared_sha,
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 1
    assert "Pull request #42: branch category does not match issue #117" in result.stderr
    assert "Validated enhancement/117-20260714-valid-branch" in result.stdout
    assert "pulls/42" in gh_log
    assert "pulls/41" in gh_log
    assert statuses.count("-f state=pending") == 1
    assert statuses.count("-f state=failure") == 1
    assert "-f state=success" not in statuses


def test_issue_branch_policy_closed_event_revalidates_remaining_shared_prs(
    tmp_path: Path,
) -> None:
    shared_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        branch="bug/117-20260714-closed-invalid-duplicate",
        pull_request_state="closed",
        open_pull_request_heads=f"42\t{shared_sha}",
        secondary_pull_request_number="42",
        secondary_sha=shared_sha,
    )
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "Validated enhancement/117-20260714-second-valid-branch" in result.stdout
    assert "closed-invalid-duplicate" not in result.stdout
    assert "-f state=success" in statuses
    assert "-f state=failure" not in statuses
    assert f"statuses/{'c' * 40}" not in statuses


def test_issue_branch_policy_synchronize_queues_old_sha_before_new_sha_failure(
    tmp_path: Path,
) -> None:
    previous_sha = "b" * 40
    current_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        branch="bug/117-20260714-invalid-new-head",
        previous_head_sha=previous_sha,
        open_pull_request_heads=f"42\t{previous_sha}\n41\t{current_sha}",
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 1
    assert "Queued previous-commit validation for pull request #42" in result.stdout
    assert "issue-branch-policy.yml/dispatches" in gh_log
    assert "inputs[pull_request_number]=42" in gh_log
    assert f"inputs[head_sha]={previous_sha}" in gh_log
    assert "-f ref=main" in gh_log
    assert gh_log.index("issue-branch-policy.yml/dispatches") < gh_log.index("issues/117")
    assert "branch category does not match issue #117" in result.stderr
    assert "-f state=failure" in statuses
    assert "-f state=success" not in statuses


def test_issue_branch_policy_previous_dispatch_failure_fails_old_and_current_sha(
    tmp_path: Path,
) -> None:
    previous_sha = "b" * 40
    current_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        previous_head_sha=previous_sha,
        open_pull_request_heads=f"42\t{previous_sha}\n41\t{current_sha}",
        dispatch_fails=True,
    )
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8").splitlines()

    assert result.returncode == 1
    assert any(f"statuses/{previous_sha}" in line and "state=pending" in line for line in statuses)
    assert any(f"statuses/{previous_sha}" in line and "state=failure" in line for line in statuses)
    assert any(f"statuses/{current_sha}" in line and "state=failure" in line for line in statuses)
    assert not any(f"statuses/{current_sha}" in line and "state=success" in line for line in statuses)


def test_issue_branch_policy_previous_pending_failure_still_dispatches_and_validates(
    tmp_path: Path,
) -> None:
    previous_sha = "b" * 40
    current_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        previous_head_sha=previous_sha,
        open_pull_request_heads=f"42\t{previous_sha}\n41\t{current_sha}",
        pending_status_fails=True,
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "dispatching anyway" in result.stderr
    assert "issue-branch-policy.yml/dispatches" in gh_log
    assert f"inputs[head_sha]={previous_sha}" in gh_log
    assert "Validated enhancement/117-20260714-valid-branch" in result.stdout
    assert "-f state=success" in statuses


def test_issue_branch_policy_rejects_impossible_calendar_date(tmp_path: Path) -> None:
    result = run_issue_branch_policy_script(
        tmp_path,
        branch="enhancement/117-20260231-invalid-date",
    )
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 1
    assert "branch date is not a valid YYYYMMDD date" in result.stderr
    assert "-f state=failure" in statuses
    assert "issues/117" not in (tmp_path / "gh.log").read_text(encoding="utf-8")


def test_issue_branch_policy_revalidates_all_open_prs_for_category_label_change(
    tmp_path: Path,
) -> None:
    result = run_issue_branch_policy_script(
        tmp_path,
        event_name="issues",
        issue_event_label="bug",
        issue_event_number="117",
        issue_json=(
            '{"number":117,"labels":['
            '{"name":"bug"},{"name":"enhancement"}'
            "]}"
        ),
        open_pull_requests=(
            f"41\tenhancement/117-20260714-valid-branch\t{'a' * 40}\n"
            f"42\tenhancement/117-20260714-second-valid-branch\t{'b' * 40}\n"
            f"43\tenhancement/118-20260714-unrelated-branch\t{'c' * 40}"
        ),
        pull_request_number="",
        secondary_pull_request_number="42",
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "pulls?state=open&per_page=100 --paginate" in gh_log
    assert gh_log.count("issue-branch-policy.yml/dispatches") == 2
    assert "inputs[pull_request_number]=41" in gh_log
    assert "inputs[pull_request_number]=42" in gh_log
    assert "inputs[pull_request_number]=43" not in gh_log
    assert f"inputs[head_sha]={'a' * 40}" in gh_log
    assert f"inputs[head_sha]={'b' * 40}" in gh_log
    assert f"inputs[head_sha]={'c' * 40}" not in gh_log
    assert "-f ref=main" in gh_log
    assert "Queued branch-policy revalidation for pull request #41" in result.stdout
    assert statuses.count("-f state=pending") == 2
    assert f"statuses/{'a' * 40}" in statuses
    assert f"statuses/{'b' * 40}" in statuses
    assert f"statuses/{'c' * 40}" not in statuses
    assert "-f state=failure" not in statuses
    assert "-f state=success" not in statuses


def test_issue_branch_policy_relabel_dispatch_failure_fails_candidate_sha(
    tmp_path: Path,
) -> None:
    candidate_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        event_name="issues",
        issue_event_label="bug",
        issue_event_number="117",
        open_pull_requests=(
            f"41\tenhancement/117-20260714-valid-branch\t{candidate_sha}"
        ),
        pull_request_number="",
        dispatch_fails=True,
    )
    statuses = (tmp_path / "statuses.log").read_text(encoding="utf-8").splitlines()

    assert result.returncode == 1
    assert any(f"statuses/{candidate_sha}" in line and "state=pending" in line for line in statuses)
    assert any(f"statuses/{candidate_sha}" in line and "state=failure" in line for line in statuses)
    assert not any("state=success" in line for line in statuses)


def test_issue_branch_policy_relabel_dispatches_after_pending_status_failure(
    tmp_path: Path,
) -> None:
    candidate_sha = "a" * 40
    result = run_issue_branch_policy_script(
        tmp_path,
        event_name="issues",
        issue_event_label="bug",
        issue_event_number="117",
        open_pull_requests=(
            f"41\tenhancement/117-20260714-valid-branch\t{candidate_sha}"
        ),
        pull_request_number="",
        pending_status_fails=True,
    )
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")

    assert result.returncode == 1
    assert "Unable to publish pending status for pull request #41" in result.stderr
    assert "issue-branch-policy.yml/dispatches" in gh_log
    assert "inputs[pull_request_number]=41" in gh_log
    assert f"inputs[head_sha]={candidate_sha}" in gh_log


def test_issue_branch_policy_skips_unrelated_issue_label_change(tmp_path: Path) -> None:
    result = run_issue_branch_policy_script(
        tmp_path,
        issue_event_label="needs-demo",
        issue_event_number="117",
        pull_request_number="",
    )
    assert result.returncode == 0, result.stderr
    assert "does not affect the branch category policy" in result.stdout
    assert not (tmp_path / "gh.log").exists()


def test_issue_branch_policy_rejects_invalid_or_missing_issue(tmp_path: Path) -> None:
    invalid_branch = run_issue_branch_policy_script(
        tmp_path,
        branch="117-short-branch",
    )

    assert invalid_branch.returncode == 1
    assert "branch name is not canonical" in invalid_branch.stderr
    assert "issues/117" not in (tmp_path / "gh.log").read_text(encoding="utf-8")

    missing_path = tmp_path / "missing"
    missing_path.mkdir()
    missing_issue = run_issue_branch_policy_script(missing_path, issue_missing=True)

    assert missing_issue.returncode == 1
    assert "referenced issue #117 does not exist" in missing_issue.stderr
    assert "-f state=failure" in (missing_path / "statuses.log").read_text(encoding="utf-8")


def test_issue_branch_policy_rejects_ambiguous_labels_and_pull_requests(tmp_path: Path) -> None:
    ambiguous = run_issue_branch_policy_script(
        tmp_path,
        issue_json=(
            '{"number":117,"labels":['
            '{"name":"bug"},{"name":"enhancement"}'
            "]}"
        ),
    )

    assert ambiguous.returncode == 1
    assert "issue #117 needs exactly one category label" in ambiguous.stderr

    pull_request_path = tmp_path / "pull-request"
    pull_request_path.mkdir()
    pull_request = run_issue_branch_policy_script(
        pull_request_path,
        issue_json=(
            '{"number":117,"pull_request":{},'
            '"labels":[{"name":"enhancement"}]}'
        ),
    )

    assert pull_request.returncode == 1
    assert "#117 is a pull request, not an issue" in pull_request.stderr


def test_issue_branch_policy_does_not_execute_branch_name_input(tmp_path: Path) -> None:
    marker = tmp_path / "branch-input-executed"
    branch = f"enhancement/117-20260714-$(touch$IFS{marker})"

    result = run_issue_branch_policy_script(tmp_path, branch=branch)

    assert result.returncode == 1
    assert "branch name is not canonical" in result.stderr
    assert not marker.exists()


def test_reusable_base_check_workflow_contract() -> None:
    workflow = load_workflow(BASE_CHECK_WORKFLOW)
    ci_docs = (REPO_ROOT / "docs" / "basectl-ci.md").read_text(encoding="utf-8")
    triggers = workflow.get("on") or workflow.get(True)
    workflow_call = triggers["workflow_call"]
    inputs = workflow_call["inputs"]
    job = workflow["jobs"]["base-check"]
    steps = job["steps"]
    run_commands = "\n".join(step.get("run", "") for step in steps if isinstance(step, dict))

    assert workflow["name"] == "Reusable Base Check"
    assert workflow["permissions"] == {"contents": "read"}
    assert "concurrency" in workflow
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == 20
    assert inputs["project"] == {
        "description": "Base project name to check.",
        "required": True,
        "type": "string",
    }
    assert inputs["manifest-path"]["default"] == "base_manifest.yaml"
    assert inputs["setup-mode"]["default"] == "source-checkout"
    assert inputs["base-ref"]["default"] == ""
    assert "base-bash-libs-ref" not in inputs
    assert inputs["output-format"]["default"] == "json"
    assert inputs["python-version"]["default"] == "3.13"
    assert "source-checkout|preinstalled" in run_commands
    assert "args=(check --ci \"$BASE_CHECK_PROJECT\" --format \"$BASE_CHECK_OUTPUT_FORMAT\")" in run_commands
    assert "BASE_BASH_LIBS_DIR" in run_commands
    assert "basefoundry/base-bash-libs" in str(steps)
    assert "189ed0be4a71602de2be0f75107288e39eddf7a7" in str(steps)
    assert "${{ inputs.base-ref || github.workflow_sha }}" in str(steps)
    assert "uses: basefoundry/base/.github/workflows/base-check.yml@<base-ref-or-sha>" in ci_docs
    assert "| `setup-mode` | `source-checkout` |" in ci_docs


def test_copilot_repository_instructions_stay_anchored_to_base_guidance() -> None:
    text = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

    assert "AGENTS.md" in text
    assert "CONTRIBUTING.md" in text
    assert "STANDARDS.md" in text
    assert ".ai-context/" in text
    assert "issue-backed" in text
    assert "Base focused as the shared developer workspace control plane" in text
    assert "Do not require GitHub Copilot" in text


def test_copilot_setup_steps_are_bounded_to_cloud_agent_setup() -> None:
    workflow = load_workflow(COPILOT_SETUP_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)
    jobs = workflow["jobs"]
    setup_job = jobs["copilot-setup-steps"]

    assert workflow["name"] == "Copilot setup steps"
    assert triggers == {
        "workflow_dispatch": None,
        "push": {"paths": [".github/workflows/copilot-setup-steps.yml"]},
        "pull_request": {"paths": [".github/workflows/copilot-setup-steps.yml"]},
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert set(jobs) == {"copilot-setup-steps"}
    assert setup_job["runs-on"] == "ubuntu-latest"
    assert setup_job["timeout-minutes"] == 15

    run_commands = "\n".join(
        step.get("run", "")
        for step in setup_job["steps"]
        if isinstance(step, dict)
    )
    assert "python -m pip install -r requirements-dev.txt" in run_commands
    assert "python -m compileall -q cli/python lib/python tests" in run_commands
    assert "python -m pytest tests/test_github_workflows.py tests/test_bootstrap_docs.py -q" in run_commands
    assert "BASE_BASH_LIBS_DIR" not in run_commands
    assert "secrets." not in run_commands


def test_implementation_issue_template_is_copilot_ready_and_project_aligned() -> None:
    template = load_yaml_mapping(IMPLEMENTATION_ISSUE_TEMPLATE)
    project_config = load_yaml_mapping(BASE_PROJECT_CONFIG)["project"]
    fields = {
        field["id"]: field
        for field in template["body"]
        if isinstance(field, dict) and "id" in field
    }

    assert template["name"] == "Implementation issue"
    assert template["labels"] == ["enhancement"]
    assert template["assignees"] == ["codeforester"]
    assert {"goal", "background", "scope", "acceptance_criteria", "validation", "non_goals"} <= fields.keys()
    assert fields["priority"]["attributes"]["options"] == ["P0", "P1", "P2", "P3"]
    assert fields["size"]["attributes"]["options"] == ["T", "S", "M", "L"]
    assert fields["area"]["attributes"]["options"] == project_config["areas"]
    assert fields["initiative"]["attributes"]["options"] == project_config["initiatives"]
    assert "assign this issue to Copilot" in fields["agent_assignment"]["attributes"]["description"]


def test_agentic_coding_platform_initiative_is_documented() -> None:
    project_config = load_yaml_mapping(BASE_PROJECT_CONFIG)["project"]
    implementation_template = load_yaml_mapping(IMPLEMENTATION_ISSUE_TEMPLATE)
    workflow_docs = (REPO_ROOT / "docs" / "github-workflow.md").read_text(encoding="utf-8")
    workflow_context = (REPO_ROOT / ".ai-context" / "WORKFLOWS.md").read_text(encoding="utf-8")
    initiative_fields = [
        field
        for field in implementation_template["body"]
        if isinstance(field, dict) and field.get("id") == "initiative"
    ]

    assert "Agentic Coding Platform" in project_config["initiatives"]
    assert len(initiative_fields) == 1
    assert "Agentic Coding Platform" in initiative_fields[0]["attributes"]["options"]
    assert "Agentic Coding Platform" in workflow_docs
    assert "agent-ready repo baselines" in workflow_docs
    assert "agent-ready repo baselines" in workflow_context


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


def test_ubuntu_apt_jobs_remove_flaky_runner_third_party_sources() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    jobs = workflow["jobs"]

    for job_name in ("bats", "integration", "ubuntu-source-checkout", "security"):
        steps = jobs[job_name]["steps"]
        first_apt_update_index = next(
            index
            for index, step in enumerate(steps)
            if isinstance(step, dict) and "sudo apt-get update" in step.get("run", "")
        )
        setup_commands = "\n".join(
            step.get("run", "")
            for step in steps[:first_apt_update_index]
            if isinstance(step, dict)
        )

        assert "/etc/apt/sources.list.d/azure-cli.sources" in setup_commands
        assert "/etc/apt/sources.list.d/microsoft-prod.list" in setup_commands


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


def test_skills_workflow_create_pr_is_issue_backed() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "skills.yml")
    triggers = workflow.get("on") or workflow.get(True)
    create_job = workflow["jobs"]["create"]
    commit_step = next(
        step for step in create_job["steps"] if step.get("name") == "Commit and push starter file"
    )
    run_commands = "\n".join(
        step.get("run", "")
        for step in create_job["steps"]
        if isinstance(step, dict)
    )

    assert triggers["workflow_dispatch"]["inputs"]["issue_number"] == {
        "description": "Issue number the generated pull request will close (required with create_pr)",
        "required": False,
        "type": "string",
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert create_job["permissions"] == {
        "contents": "write",
        "issues": "read",
        "pull-requests": "write",
    }
    assert create_job["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert create_job["env"]["ISSUE_NUMBER"] == "${{ inputs.issue_number }}"
    assert '[[ ! "$ISSUE_NUMBER" =~ ^[1-9][0-9]*$ ]]' in run_commands
    assert 'gh issue view "$ISSUE_NUMBER"' in run_commands
    assert 'Issue #$ISSUE_NUMBER must have exactly one Base category label.' in run_commands
    assert 'date_stamp="$(date -u +%Y%m%d)"' in run_commands
    assert commit_step["env"]["ISSUE_CATEGORY"] == "${{ steps.issue.outputs.category }}"
    assert 'branch="${ISSUE_CATEGORY}/${ISSUE_NUMBER}-${date_stamp}-create-skills-md"' in run_commands
    assert "codex/create-skills-md" not in run_commands
    assert '"[codex] Add skills.md"' not in run_commands
    assert '--title "Add skills.md"' in run_commands
    assert "printf '\\nCloses #%s\\n' \"$ISSUE_NUMBER\" >> pr-body.md" in run_commands
    assert "${{ inputs.issue_number }}" not in run_commands
