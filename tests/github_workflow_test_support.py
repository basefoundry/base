"""Process and CLI mocks shared by the GitHub workflow tests."""

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import subprocess

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
ISSUE_BRANCH_POLICY_WORKFLOW = WORKFLOW_DIR / "issue-branch-policy.yml"


def _workflow_step_run_command(path: Path, job_name: str, step_name: str) -> str:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = workflow["jobs"][job_name]["steps"]
    matches = [step for step in steps if step.get("name") == step_name]
    assert len(matches) == 1, (
        f"Expected exactly one workflow step named {step_name!r}, found {len(matches)}."
    )
    return matches[0]["run"]


def project_intake_run_command() -> str:
    return _workflow_step_run_command(
        WORKFLOW_DIR / "project-intake.yml",
        "sync",
        "Reconcile Project item",
    )


def issue_branch_policy_run_command() -> str:
    return _workflow_step_run_command(
        ISSUE_BRANCH_POLICY_WORKFLOW,
        "policy",
        "Validate issue-backed branch",
    )


@dataclass(frozen=True)
class IssueBranchPolicyScenario:
    """Inputs and mocked API state for one branch-policy workflow run."""

    branch: str = "enhancement/117-20260714-valid-branch"
    issue_json: str = '{"number":117,"labels":[{"name":"enhancement"}]}'
    issue_missing: bool = False
    issue_event_label: str = ""
    issue_event_number: str = ""
    event_name: str = "pull_request_target"
    event_head_sha: str = "a" * 40
    dispatch_head_sha: str = ""
    previous_head_sha: str = ""
    open_pull_requests: str = ""
    open_pull_request_heads: str = ""
    pull_request_number: str = "41"
    pull_request_sha: str = "a" * 40
    pull_request_state: str = "open"
    pull_request_missing: bool = False
    dispatch_fails: bool = False
    pending_status_fails: bool = False
    secondary_branch: str = "enhancement/117-20260714-second-valid-branch"
    secondary_pull_request_number: str = ""
    secondary_pull_request_state: str = "open"
    secondary_sha: str = "b" * 40


def _write_issue_branch_policy_gh_mock(tmp_path: Path) -> Path:
    mockbin = tmp_path / "bin"
    mockbin.mkdir()
    gh_mock = mockbin / "gh"
    gh_mock.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${ISSUE_BRANCH_POLICY_STATE:?}/gh.log"

case "${2:-}" in
  repos/*/pulls\\?state=open*)
    if [[ "$*" == *".head.ref"* ]]; then
      printf '%s\\n' "${ISSUE_BRANCH_POLICY_OPEN_PULL_REQUESTS:-}"
    else
      printf '%s\\n' "${ISSUE_BRANCH_POLICY_OPEN_PULL_REQUEST_HEADS:-}"
    fi
    ;;
  repos/*/pulls/*)
    if [[ "${ISSUE_BRANCH_POLICY_PULL_REQUEST_MISSING:-}" == "1" ]]; then
      printf 'not found\\n' >&2
      exit 1
    fi
    pull_request_number="${2##*/}"
    if [[ -n "${ISSUE_BRANCH_POLICY_SECONDARY_PULL_REQUEST_NUMBER:-}" &&
          "$pull_request_number" == "$ISSUE_BRANCH_POLICY_SECONDARY_PULL_REQUEST_NUMBER" ]]; then
      printf '%s\\n' "${ISSUE_BRANCH_POLICY_SECONDARY_PULL_REQUEST_JSON:?}"
    else
      printf '%s\\n' "${ISSUE_BRANCH_POLICY_PULL_REQUEST_JSON:?}"
    fi
    ;;
  repos/*/statuses/*)
    printf '%s\\n' "$*" >> "${ISSUE_BRANCH_POLICY_STATE:?}/statuses.log"
    if [[ "${ISSUE_BRANCH_POLICY_PENDING_STATUS_FAIL:-}" == "1" &&
          "$*" == *"state=pending"* ]]; then
      printf 'status unavailable\\n' >&2
      exit 1
    fi
    ;;
  repos/*/actions/workflows/issue-branch-policy.yml/dispatches)
    if [[ "${ISSUE_BRANCH_POLICY_DISPATCH_FAIL:-}" == "1" ]]; then
      printf 'dispatch unavailable\\n' >&2
      exit 1
    fi
    ;;
  repos/*/issues/*)
    if [[ "${ISSUE_BRANCH_POLICY_ISSUE_MISSING:-}" == "1" ]]; then
      printf 'not found\\n' >&2
      exit 1
    fi
    printf '%s\\n' "${ISSUE_BRANCH_POLICY_ISSUE_JSON:?}"
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
    return mockbin


def run_issue_branch_policy_script(
    tmp_path: Path,
    scenario: IssueBranchPolicyScenario | None = None,
    **overrides: object,
) -> subprocess.CompletedProcess[str]:
    """Run the policy step with a scenario plus concise per-test overrides."""
    scenario = replace(scenario or IssueBranchPolicyScenario(), **overrides)
    mockbin = _write_issue_branch_policy_gh_mock(tmp_path)
    env = os.environ.copy()
    pull_request = {
        "number": int(scenario.pull_request_number or "41"),
        "state": scenario.pull_request_state,
        "head": {"ref": scenario.branch, "sha": scenario.pull_request_sha},
    }
    secondary_pull_request = {
        "number": int(scenario.secondary_pull_request_number or "42"),
        "state": scenario.secondary_pull_request_state,
        "head": {"ref": scenario.secondary_branch, "sha": scenario.secondary_sha},
    }
    env.update(
        {
            "DEFAULT_BRANCH": "main",
            "GH_TOKEN": "test-token",
            "GITHUB_REPOSITORY": "basefoundry/base",
            "GITHUB_RUN_ID": "1234",
            "GITHUB_SERVER_URL": "https://github.com",
            "EVENT_NAME": scenario.event_name,
            "EVENT_HEAD_SHA": scenario.event_head_sha,
            "DISPATCH_HEAD_SHA": scenario.dispatch_head_sha,
            "PREVIOUS_HEAD_SHA": scenario.previous_head_sha,
            "ISSUE_EVENT_LABEL": scenario.issue_event_label,
            "ISSUE_EVENT_NUMBER": scenario.issue_event_number,
            "ISSUE_BRANCH_POLICY_ISSUE_JSON": scenario.issue_json,
            "ISSUE_BRANCH_POLICY_ISSUE_MISSING": "1" if scenario.issue_missing else "0",
            "ISSUE_BRANCH_POLICY_PULL_REQUEST_MISSING": (
                "1" if scenario.pull_request_missing else "0"
            ),
            "ISSUE_BRANCH_POLICY_DISPATCH_FAIL": "1" if scenario.dispatch_fails else "0",
            "ISSUE_BRANCH_POLICY_PENDING_STATUS_FAIL": (
                "1" if scenario.pending_status_fails else "0"
            ),
            "ISSUE_BRANCH_POLICY_OPEN_PULL_REQUESTS": scenario.open_pull_requests,
            "ISSUE_BRANCH_POLICY_OPEN_PULL_REQUEST_HEADS": scenario.open_pull_request_heads,
            "ISSUE_BRANCH_POLICY_PULL_REQUEST_JSON": json.dumps(pull_request, separators=(",", ":")),
            "ISSUE_BRANCH_POLICY_SECONDARY_PULL_REQUEST_JSON": json.dumps(
                secondary_pull_request,
                separators=(",", ":"),
            ),
            "ISSUE_BRANCH_POLICY_SECONDARY_PULL_REQUEST_NUMBER": (
                scenario.secondary_pull_request_number
            ),
            "ISSUE_BRANCH_POLICY_STATE": str(tmp_path),
            "PATH": f"{mockbin}:{env['PATH']}",
            "POLICY_CONTEXT": "base/issue-branch-policy",
            "PULL_REQUEST_NUMBER": scenario.pull_request_number,
            "RUN_SHA": "c" * 40,
        }
    )
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", issue_branch_policy_run_command()],
        check=False,
        capture_output=True,
        env=env,
        text=True,
        timeout=30,
    )


def _write_project_intake_mocks(tmp_path: Path) -> Path:
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


def _project_intake_env(tmp_path: Path, mockbin: Path) -> dict[str, str]:
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


def run_project_intake_script(
    tmp_path: Path,
    **env_overrides: str,
) -> subprocess.CompletedProcess[str]:
    mockbin = _write_project_intake_mocks(tmp_path)
    env = _project_intake_env(tmp_path, mockbin)
    env.update(env_overrides)

    return subprocess.run(
        ["bash", "-c", project_intake_run_command()],
        check=False,
        capture_output=True,
        env=env,
        text=True,
        timeout=30,
    )
