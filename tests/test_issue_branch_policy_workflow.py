"""Contract tests for the issue-backed branch-policy workflow."""

from pathlib import Path

from tests.github_workflow_test_support import (
    issue_branch_policy_run_command,
    load_workflow,
    run_issue_branch_policy_script,
    workflow_steps,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
ISSUE_BRANCH_POLICY_WORKFLOW = WORKFLOW_DIR / "issue-branch-policy.yml"
ISSUE_BRANCH_POLICY_TEMPLATE = REPO_ROOT / "templates" / "issue-branch-policy.yml"


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
