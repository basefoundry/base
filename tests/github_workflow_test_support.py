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

project_intake_mock_value() {
  local field="$1"
  local state_file="${PROJECT_INTAKE_STATE:?}/${field}"

  if [[ -f "$state_file" ]]; then
    cat "$state_file"
    return 0
  fi

  case "$field" in
    status) printf '%s\\n' "${PROJECT_INTAKE_EXISTING_STATUS:-}" ;;
    priority) printf '%s\\n' "${PROJECT_INTAKE_EXISTING_PRIORITY:-}" ;;
    size) printf '%s\\n' "${PROJECT_INTAKE_EXISTING_SIZE:-}" ;;
    area) printf '%s\\n' "${PROJECT_INTAKE_EXISTING_AREA:-}" ;;
    initiative) printf '%s\\n' "${PROJECT_INTAKE_EXISTING_INITIATIVE:-}" ;;
  esac
}

project_intake_mock_write_option() {
  local field_id="$1"
  local option_id="$2"
  local field_name=''
  local option_name=''

  case "$field_id" in
    F_status|10) field_name=status ;;
    F_priority|11) field_name=priority ;;
    F_size|12) field_name=size ;;
    F_area|13) field_name=area ;;
    F_initiative|14) field_name=initiative ;;
  esac
  case "$option_id" in
    O_backlog) option_name=Backlog ;;
    O_done) option_name=Done ;;
    O_p2) option_name=P2 ;;
    O_s) option_name=S ;;
    O_product) option_name=Product ;;
    O_adoption) option_name='Adoption Polish' ;;
  esac
  [[ -n "$field_name" && -n "$option_name" ]] || {
    printf 'unexpected field update: %s=%s\\n' "$field_id" "$option_id" >&2
    exit 2
  }
  printf '%s\\n' "$option_name" > "${PROJECT_INTAKE_STATE:?}/${field_name}"
}

project_intake_mock_graphql_item() {
  jq -nc \
    --arg status "$(project_intake_mock_value status)" \
    --arg priority "$(project_intake_mock_value priority)" \
    --arg size "$(project_intake_mock_value size)" \
    --arg area "$(project_intake_mock_value area)" \
    --arg initiative "$(project_intake_mock_value initiative)" \
    '{items:[{id:"PVTI_item",status:$status,priority:$priority,size:$size,area:$area,initiative:$initiative}]}'
}

project_intake_mock_rest_item() {
  jq -nc \
    --arg status "$(project_intake_mock_value status)" \
    --arg priority "$(project_intake_mock_value priority)" \
    --arg size "$(project_intake_mock_value size)" \
    --arg area "$(project_intake_mock_value area)" \
    --arg initiative "$(project_intake_mock_value initiative)" \
    '{id:101,content:{id:1311,number:1311,title:"Project Intake test issue"},fields:[
      {id:10,name:"Status",value:{name:{raw:$status}}},
      {id:11,name:"Priority",value:{name:{raw:$priority}}},
      {id:12,name:"Size",value:{name:{raw:$size}}},
      {id:13,name:"Area",value:{name:{raw:$area}}},
      {id:14,name:"Initiative",value:{name:{raw:$initiative}}}
    ] | map(select(.value.name.raw != ""))}'
}

case "$*" in
  "api repos/basefoundry/base/issues/1311")
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
      printf 'API rate limit already exceeded\\n' >&2
      printf 'Retry-After: 7\\n' >&2
      exit 1
    fi

    if [[ "${PROJECT_INTAKE_WARN_ON_SUCCESS:-}" == "1" ]]; then
      printf 'warning: gh emitted a non-fatal notice\\n' >&2
    fi

    printf '%s' \
      '{"id":1311,"number":1311,"state":"'
    printf '%s' "${PROJECT_INTAKE_ISSUE_STATE:-open}"
    printf '%s\\n' \
      '","html_url":"https://github.com/basefoundry/base/issues/1311","title":"Project Intake test issue"}'
    ;;
  "project list --owner basefoundry --format json --limit 100")
    printf '{"projects":[{"title":"base","number":1}]}\\n'
    ;;
  "project view 1 --owner basefoundry --format json --jq .id")
    printf 'PVT_project\\n'
    ;;
  project\\ item-add*)
    printf 'PVTI_item\\n'
    ;;
  project\\ item-list*)
    case "${PROJECT_INTAKE_GRAPHQL_FAILURE:-}" in
      quota)
        printf 'GraphQL: API rate limit already exceeded\\n' >&2
        exit 1
        ;;
      unknown-owner)
        printf 'unknown owner type\\n' >&2
        exit 1
        ;;
    esac
    count_file="${PROJECT_INTAKE_STATE:?}/graphql-item-list-count"
    count=0
    [[ ! -f "$count_file" ]] || count="$(cat "$count_file")"
    count=$((count + 1))
    printf '%s\\n' "$count" > "$count_file"
    if [[ "${PROJECT_INTAKE_ITEM_NEVER_VISIBLE:-0}" == "1" ||
          ( "${PROJECT_INTAKE_DELAYED_ITEM_VISIBILITY:-0}" == "1" && "$count" == "1" ) ]]; then
      printf '{"items":[]}\\n'
    else
      project_intake_mock_graphql_item
    fi
    ;;
  project\\ field-list*)
    if [[ "${PROJECT_INTAKE_MISSING_FIELD_OPTION:-0}" == "1" ]]; then
      cat <<'JSON'
{"fields":[
  {"name":"Status","id":"F_status","options":[{"name":"Backlog","id":"O_backlog"},{"name":"Done","id":"O_done"}]},
  {"name":"Priority","id":"F_priority","options":[{"name":"P2","id":"O_p2"}]},
  {"name":"Size","id":"F_size","options":[{"name":"S","id":"O_s"}]},
  {"name":"Area","id":"F_area","options":[]},
  {"name":"Initiative","id":"F_initiative","options":[{"name":"Adoption Polish","id":"O_adoption"}]}
]}
JSON
    else
      cat <<'JSON'
{"fields":[
  {"name":"Status","id":"F_status","options":[{"name":"Backlog","id":"O_backlog"},{"name":"Done","id":"O_done"}]},
  {"name":"Priority","id":"F_priority","options":[{"name":"P2","id":"O_p2"}]},
  {"name":"Size","id":"F_size","options":[{"name":"S","id":"O_s"}]},
  {"name":"Area","id":"F_area","options":[{"name":"Product","id":"O_product"}]},
  {"name":"Initiative","id":"F_initiative","options":[{"name":"Adoption Polish","id":"O_adoption"}]}
]}
JSON
    fi
    ;;
  project\\ item-edit*)
    printf '%s\\n' "$*" >> "${PROJECT_INTAKE_STATE:?}/edits.log"
    field_id=''
    option_id=''
    while (( $# > 0 )); do
      case "$1" in
        --field-id)
          field_id="$2"
          shift 2
          ;;
        --single-select-option-id)
          option_id="$2"
          shift 2
          ;;
        *) shift ;;
      esac
    done
    project_intake_mock_write_option "$field_id" "$option_id"
    ;;
  "api users/basefoundry")
    if [[ "${PROJECT_INTAKE_REST_FAIL_OPERATION:-}" == "owner" ]]; then
      printf 'API rate limit already exceeded\\n' >&2
      printf 'Retry-After: 7\\n' >&2
      exit 1
    fi
    if [[ "${PROJECT_INTAKE_REST_FAIL_OPERATION:-}" == "transport-owner" ]]; then
      printf '503 Service Unavailable\\n' >&2
      printf 'Retry-After: 3\\n' >&2
      exit 1
    fi
    printf '{"login":"basefoundry","type":"%s"}\\n' "${PROJECT_INTAKE_OWNER_TYPE:-Organization}"
    ;;
  api\\ *projectsV2\\?per_page=100)
    printf '[{"id":1,"number":1,"title":"base"}]\\n'
    ;;
  api\\ *projectsV2/1/fields\\?per_page=100)
    cat <<'JSON'
[
  {"id":10,"name":"Status","options":[
    {"id":"O_backlog","name":{"raw":"Backlog"}},
    {"id":"O_done","name":{"raw":"Done"}}
  ]},
  {"id":11,"name":"Priority","options":[{"id":"O_p2","name":{"raw":"P2"}}]},
  {"id":12,"name":"Size","options":[{"id":"O_s","name":{"raw":"S"}}]},
  {"id":13,"name":"Area","options":[{"id":"O_product","name":{"raw":"Product"}}]},
  {"id":14,"name":"Initiative","options":[{"id":"O_adoption","name":{"raw":"Adoption Polish"}}]}
]
JSON
    ;;
  api\\ --method\\ GET\\ *projectsV2/1/items/101*)
    if [[ "${PROJECT_INTAKE_REST_FAIL_OPERATION:-}" == "read" ]]; then
      printf '403 Forbidden: REST item read failed\\n' >&2
      exit 1
    fi
    count_file="${PROJECT_INTAKE_STATE:?}/rest-item-get-count"
    count=0
    [[ ! -f "$count_file" ]] || count="$(cat "$count_file")"
    count=$((count + 1))
    printf '%s\\n' "$count" > "$count_file"
    if [[ "${PROJECT_INTAKE_REST_ITEM_GET_DELAYED:-0}" == "1" && "$count" == "1" ]]; then
      printf '{}\\n'
    else
      project_intake_mock_rest_item
    fi
    ;;
  api\\ --method\\ GET\\ *projectsV2/1/items*)
    if [[ "${PROJECT_INTAKE_REST_FAIL_OPERATION:-}" == "find" ]]; then
      printf '403 Forbidden: REST item lookup failed\\n' >&2
      exit 1
    fi
    count_file="${PROJECT_INTAKE_STATE:?}/rest-item-search-count"
    count=0
    [[ ! -f "$count_file" ]] || count="$(cat "$count_file")"
    count=$((count + 1))
    printf '%s\\n' "$count" > "$count_file"
    if [[ "${PROJECT_INTAKE_ITEM_EXISTS:-1}" == "1" ||
          ( -f "${PROJECT_INTAKE_STATE:?}/rest-item-added" &&
            "${PROJECT_INTAKE_ITEM_NEVER_VISIBLE:-0}" != "1" &&
            ( "${PROJECT_INTAKE_DELAYED_ITEM_VISIBILITY:-0}" != "1" || "$count" != "2" ) ) ||
          ( -f "${PROJECT_INTAKE_STATE:?}/rest-item-duplicate" && "$count" -ge 3 ) ]]; then
      printf '[{"id":101,"content":{"id":1311,"number":1311,"title":"Project Intake test issue"}}]\\n'
    else
      printf '[]\\n'
    fi
    ;;
  api\\ --method\\ POST\\ *projectsV2/1/items*)
    if [[ "${PROJECT_INTAKE_REST_DUPLICATE_ADD:-0}" == "1" ]]; then
      : > "${PROJECT_INTAKE_STATE:?}/rest-item-duplicate"
      printf 'Content already exists in this project (HTTP 422)\\n' >&2
      exit 1
    fi
    : > "${PROJECT_INTAKE_STATE:?}/rest-item-added"
    if [[ "${PROJECT_INTAKE_REST_ADD_RESPONSE:-nested}" == "top-level" ]]; then
      printf '{"id":101}\\n'
    else
      printf '{"value":{"id":101}}\\n'
    fi
    ;;
  api\\ --method\\ PATCH\\ *projectsV2/1/items/101*)
    payload="$(cat)"
    printf '%s\\n' "$payload" >> "${PROJECT_INTAKE_STATE:?}/rest-patches.log"
    if [[ "${PROJECT_INTAKE_REST_FAIL_OPERATION:-}" == "update" ]]; then
      printf '403 Forbidden: REST field update failed\\n' >&2
      exit 1
    fi
    while IFS=$'\\t' read -r field_id option_id; do
      project_intake_mock_write_option "$field_id" "$option_id"
    done < <(jq -r '.fields[] | [.id, .value] | @tsv' <<<"$payload")
    project_intake_mock_rest_item
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
