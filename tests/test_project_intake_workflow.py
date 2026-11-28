import ast
import inspect
from pathlib import Path

import yaml
import pytest

from tests.project_field_identity_support import FIXTURES, run_identity_intake

from tests.github_workflow_test_support import (
    project_intake_run_command,
    run_project_intake_script,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def load_workflow(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


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


def test_project_intake_requires_base_project_token() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "project-intake.yml")
    sync_job = workflow["jobs"]["sync"]
    run_command = project_intake_run_command()

    assert workflow["name"] == "Project Intake metadata (advisory)"
    assert sync_job["name"] == "Project metadata sync (advisory)"
    assert sync_job["env"]["GH_TOKEN"] == "${{ secrets.BASE_PROJECT_TOKEN }}"
    assert "github.token" not in run_command
    assert "BASE_PROJECT_TOKEN secret is required for Project Intake." in run_command
    assert "gh auth token | gh secret set BASE_PROJECT_TOKEN --repo $GITHUB_REPOSITORY" in (
        run_command
    )


def test_project_intake_template_matches_repository_workflow() -> None:
    assert (REPO_ROOT / "templates" / "project-intake.yml").read_text(encoding="utf-8") == (
        WORKFLOW_DIR / "project-intake.yml"
    ).read_text(encoding="utf-8")


def test_project_intake_uses_by_id_graphql_reads_in_both_workflow_copies() -> None:
    template = load_workflow(REPO_ROOT / "templates" / "project-intake.yml")
    template_run = template["jobs"]["sync"]["steps"][0]["run"]

    for run_command in (project_intake_run_command(), template_run):
        assert "gh project item-list" not in run_command
        assert run_command.count('project_intake_graphql_read_item_by_id "$item_id"') == 2
        assert "query($id: ID!)" in run_command
        assert "node(id: $id)" in run_command


def test_project_intake_issue_fields_mode_sets_only_missing_issue_defaults(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_FIELD_SOURCE="issue_fields")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "issue-priority").read_text(encoding="utf-8") == "Medium\n"
    assert (tmp_path / "issue-effort").read_text(encoding="utf-8") == "Small\n"
    payload = yaml.safe_load((tmp_path / "issue-field-values-posts.log").read_text(encoding="utf-8"))
    assert payload == {
        "issue_field_values": [
            {"field_id": 43373537, "value": "Medium"},
            {"field_id": 43373540, "value": "Small"},
        ]
    }
    assert not (tmp_path / "priority").exists()
    assert not (tmp_path / "size").exists()


def test_project_intake_issue_fields_mode_preserves_existing_values(tmp_path: Path) -> None:
    (tmp_path / "issue-priority").write_text("Low\n", encoding="utf-8")
    (tmp_path / "issue-effort").write_text("Large\n", encoding="utf-8")

    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_FIELD_SOURCE="issue_fields")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "issue-priority").read_text(encoding="utf-8") == "Low\n"
    assert (tmp_path / "issue-effort").read_text(encoding="utf-8") == "Large\n"
    assert not (tmp_path / "issue-field-values-posts.log").exists()


def test_project_intake_uses_project_defaults_when_repository_config_is_missing(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_CONFIG_MISSING="1")

    assert result.returncode == 0, result.stderr
    assert "Repository Project config was not found; using the existing Project-field defaults." in result.stderr
    assert "Synced issue #1311 into Project base" in result.stdout
    assert not (tmp_path / "issue-field-values-posts.log").exists()
    assert "P2" in (tmp_path / "priority").read_text(encoding="utf-8")
    assert "S" in (tmp_path / "size").read_text(encoding="utf-8")


def test_project_intake_project_fields_mode_uses_legacy_project_fields(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_FIELD_SOURCE="project_fields")

    assert result.returncode == 0, result.stderr
    assert "Project-fields rollback" in result.stdout
    payload = yaml.safe_load((tmp_path / "rest-patches.log").read_text(encoding="utf-8"))
    updates = {entry["id"]: entry["value"] for entry in payload["fields"]}
    assert updates == {10: "O_backlog", 11: "O_p2", 12: "O_s", 13: "O_product", 14: "O_adoption"}
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "issue-field-values" not in gh_log


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
    assert 'project_intake_gh "view issue" gh api' in run_command
    assert '"list Projects" gh project list' in run_command
    assert '"add Project item" gh project item-add' in run_command
    assert '"set Project field $field_name" gh project item-edit' in run_command
    assert "project_intake_is_project_transport_failure()" in run_command
    assert "unknown owner type" in run_command
    assert "Falling back to the REST Projects API." in run_command
    assert "project_intake_is_transport_failure()" in run_command
    assert "project_intake_record_advisory()" in run_command
    assert "advisory, non-product condition" in run_command
    assert 'project_intake_gh "update REST Project fields" gh api --method PATCH' in run_command


def test_project_intake_retries_rate_limited_operations_once(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_RATE_LIMIT_ONCE="1")

    assert result.returncode == 0, result.stderr
    assert "GitHub API pressure during Project Intake: view issue" in result.stderr
    assert "retrying once" in result.stderr
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "7\n"
    assert (tmp_path / "issue-view-count").read_text(encoding="utf-8") == "2\n"
    assert "Synced issue #1311 into Project base via GraphQL." in result.stdout


def test_project_intake_keeps_success_stderr_out_of_json_stdout(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_WARN_ON_SUCCESS="1")

    assert result.returncode == 0, result.stderr
    assert "warning: gh emitted a non-fatal notice" in result.stderr
    assert "warning: gh emitted a non-fatal notice" not in result.stdout
    assert "Synced issue #1311 into Project base via GraphQL." in result.stdout


def test_project_intake_auth_failures_do_not_retry(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_AUTH_FAIL="1")

    assert result.returncode != 0
    assert "GitHub authentication failed during Project Intake: view issue" in result.stderr
    assert "Rotate BASE_PROJECT_TOKEN and rerun this workflow_dispatch" in result.stderr
    assert "Bad credentials" in result.stderr
    assert "retrying once" not in result.stderr
    assert not (tmp_path / "sleep.log").exists()
    assert (tmp_path / "issue-view-count").read_text(encoding="utf-8") == "1\n"


def test_project_intake_persistent_quota_is_advisory_and_does_not_fail_product_ci(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "summary.md"
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_REST_FAIL_OPERATION="owner",
        GITHUB_STEP_SUMMARY=str(summary_path),
    )

    assert result.returncode == 0, result.stderr
    assert "category=quota" in result.stderr
    assert "Core product validation is unaffected" in summary_path.read_text(encoding="utf-8")
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "7\n"
    assert "Synced issue" not in result.stdout


def test_project_intake_transport_failure_is_advisory_after_retry(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.md"
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_REST_FAIL_OPERATION="transport-owner",
        GITHUB_STEP_SUMMARY=str(summary_path),
    )

    assert result.returncode == 0, result.stderr
    assert "category=transport" in result.stderr
    assert "Core product validation is unaffected" in summary_path.read_text(encoding="utf-8")
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "3\n"


def test_project_intake_falls_back_to_rest_for_graphql_quota_exhaustion(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_GRAPHQL_FAILURE="quota")

    assert result.returncode == 0, result.stderr
    assert "GraphQL Project transport failed during Project Intake: list Project fields" in (
        result.stderr
    )
    assert "Falling back to the REST Projects API." in result.stderr
    assert "Synced issue #1311 into Project base via REST fallback." in result.stdout
    assert not (tmp_path / "sleep.log").exists()
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "api orgs/basefoundry/projectsV2?per_page=100" in gh_log
    assert "api --method PATCH orgs/basefoundry/projectsV2/1/items/101 --input -" in gh_log


def test_project_intake_falls_back_to_user_rest_for_unknown_owner(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="unknown-owner",
        PROJECT_INTAKE_OWNER_TYPE="User",
    )

    assert result.returncode == 0, result.stderr
    assert "unknown owner type" in result.stderr
    assert "Synced issue #1311 into Project base via REST fallback." in result.stdout
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "api users/basefoundry/projectsV2?per_page=100" in gh_log
    assert "api --method PATCH users/basefoundry/projectsV2/1/items/101 --input -" in gh_log


def test_project_intake_rest_fallback_preserves_existing_nonempty_fields(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_EXISTING_PRIORITY="P1",
        PROJECT_INTAKE_EXISTING_AREA="Security",
    )

    assert result.returncode == 0, result.stderr
    payload = (tmp_path / "rest-patches.log").read_text(encoding="utf-8")
    updates = {entry["id"]: entry["value"] for entry in yaml.safe_load(payload)["fields"]}
    assert updates == {
        10: "O_backlog",
        12: "O_s",
        14: "O_adoption",
    }
    assert (tmp_path / "priority").exists() is False
    assert (tmp_path / "area").exists() is False


def test_project_intake_primary_path_is_idempotent_for_complete_fields(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_EXISTING_STATUS="Backlog",
        PROJECT_INTAKE_EXISTING_PRIORITY="P1",
        PROJECT_INTAKE_EXISTING_SIZE="M",
        PROJECT_INTAKE_EXISTING_AREA="Security",
        PROJECT_INTAKE_EXISTING_INITIATIVE="Contract Hardening",
    )

    assert result.returncode == 0, result.stderr
    assert "via GraphQL" in result.stdout
    assert not (tmp_path / "edits.log").exists()


def test_project_intake_retries_graphql_item_visibility_after_add(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_DELAYED_ITEM_VISIBILITY="1",
    )

    assert result.returncode == 0, result.stderr
    assert "not visible after it was added" in result.stderr
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "1\n"
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert gh_log.count("project item-add") == 1
    assert gh_log.count("api graphql") == 4
    assert "project item-list" not in gh_log


def test_project_intake_graphql_item_never_visible_is_advisory(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "summary.md"
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_ITEM_NEVER_VISIBLE="1",
        GITHUB_STEP_SUMMARY=str(summary_path),
    )

    assert result.returncode == 0, result.stderr
    assert "category=visibility" in result.stderr
    assert "Core product validation is unaffected" in summary_path.read_text(encoding="utf-8")
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "1\n2\n"
    assert (tmp_path / "graphql-node-count").read_text(encoding="utf-8") == "3\n"
    assert "Synced issue" not in result.stdout


def test_project_intake_finds_item_beyond_first_thousand_by_id_and_verifies_graphql(
    tmp_path: Path,
) -> None:
    (tmp_path / "priority").write_text("P1\n", encoding="utf-8")
    (tmp_path / "area").write_text("Security\n", encoding="utf-8")
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_CAPPED_ITEM_LIST="1",
    )

    assert result.returncode == 0, result.stderr
    assert "Synced issue #1311 into Project base via GraphQL." in result.stdout
    assert "visibility" not in result.stderr
    assert "Falling back to the REST Projects API." not in result.stderr
    assert not (tmp_path / "sleep.log").exists()
    assert (tmp_path / "status").read_text(encoding="utf-8") == "Backlog\n"
    assert (tmp_path / "priority").read_text(encoding="utf-8") == "P1\n"
    assert (tmp_path / "size").read_text(encoding="utf-8") == "S\n"
    assert (tmp_path / "area").read_text(encoding="utf-8") == "Security\n"
    assert (tmp_path / "initiative").read_text(encoding="utf-8") == "Adoption Polish\n"
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert gh_log.count("api graphql") == 3
    assert gh_log.count("-F id=PVTI_item") == 2
    assert "project item-list" not in gh_log
    edits = (tmp_path / "edits.log").read_text(encoding="utf-8")
    assert "F_priority" not in edits
    assert "F_area" not in edits


def test_project_intake_field_validation_remains_fail_closed(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_MISSING_FIELD_OPTION="1",
    )

    assert result.returncode != 0
    assert "Project field validation failed" in result.stderr
    assert "Synced issue" not in result.stdout


def test_project_intake_rest_fallback_applies_closed_status(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_ISSUE_STATE="closed",
    )

    assert result.returncode == 0, result.stderr
    payload = yaml.safe_load((tmp_path / "rest-patches.log").read_text(encoding="utf-8"))
    updates = {entry["id"]: entry["value"] for entry in payload["fields"]}
    assert updates[10] == "O_done"
    assert (tmp_path / "status").read_text(encoding="utf-8") == "Done\n"


def test_project_intake_rest_fallback_adds_a_missing_exact_item(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_ITEM_EXISTS="0",
    )

    assert result.returncode == 0, result.stderr
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "api --method POST orgs/basefoundry/projectsV2/1/items -f type=Issue -F id=1311" in (
        gh_log
    )


def test_project_intake_rest_fallback_accepts_live_add_response_after_delay(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_ITEM_EXISTS="0",
        PROJECT_INTAKE_REST_ADD_RESPONSE="top-level",
        PROJECT_INTAKE_REST_ITEM_GET_DELAYED="1",
    )

    assert result.returncode == 0, result.stderr
    assert "via REST fallback" in result.stdout
    assert "not visible after it was added" in result.stderr
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "1\n"
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert gh_log.count("api --method POST orgs/basefoundry/projectsV2/1/items") == 1
    assert gh_log.count("api --method GET orgs/basefoundry/projectsV2/1/items/101 -f") == 4
    assert (tmp_path / "rest-item-get-count").read_text(encoding="utf-8") == "4\n"


def test_project_intake_rest_fallback_recovers_duplicate_add_after_search_race(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_ITEM_EXISTS="0",
        PROJECT_INTAKE_REST_DUPLICATE_ADD="1",
    )

    assert result.returncode == 0, result.stderr
    assert "already exists during Project Intake" in result.stderr
    assert "via REST fallback" in result.stdout
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert gh_log.count("api --method POST orgs/basefoundry/projectsV2/1/items") == 1
    assert gh_log.count("api --method GET orgs/basefoundry/projectsV2/1/items -f") == 3
    assert not (tmp_path / "rest-item-added").exists()


def test_project_intake_rest_failures_remain_fail_closed(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_REST_FAIL_OPERATION="update",
    )

    assert result.returncode != 0
    assert "GitHub API command failed during Project Intake: update REST Project fields" in (
        result.stderr
    )
    assert "REST field update failed" in result.stderr
    assert "Synced issue" not in result.stdout


# The full #2713 matrix uses one isolated simulator for both shipped workflow copies.


@pytest.mark.parametrize('workflow', ['.github/workflows/project-intake.yml', 'templates/project-intake.yml'])
@pytest.mark.parametrize('mode,fallback', [('unset', False), ('project_fields', False), ('unset', True)])
@pytest.mark.parametrize('case', list(FIXTURES))
@pytest.mark.parametrize('preserve', [False, True])
# pylint: disable=too-many-arguments,too-many-positional-arguments
def test_intake_project_field_identity_matrix(tmp_path, workflow, mode, fallback, case, preserve):
    result, state, calls = run_identity_intake(tmp_path, case=case, mode=mode, fallback=fallback,
                                              preserve=preserve, workflow=workflow)
    expected = FIXTURES[case]['expected']
    if expected is None:
        assert result.returncode != 0
        assert 'Project field validation failed' in result.stderr
        assert not state.get('edits')
    else:
        assert result.returncode == 0, result.stderr
        assert state['values']['11'] == ('P1' if preserve else 'P2')
        assert state['values']['12'] == ('M' if preserve else 'S')
        edits = state.get('edits', [])
        assert not {'900','111','112'} & set(edits)
        if preserve:
            assert not {'11','12','13','14'} & set(edits)
        assert state['issue_values'] == ({'Priority':'High','Effort':'Large'} if preserve else {})
    if mode == 'project_fields':
        assert not any(c[:2] == ['api','graphql'] for c in calls)
    elif fallback:
        assert any('projectsV2' in ' '.join(c) for c in calls)


@pytest.mark.parametrize('workflow', ['.github/workflows/project-intake.yml', 'templates/project-intake.yml'])
@pytest.mark.parametrize('fallback', [False, True])
@pytest.mark.parametrize('preserve', [False, True])
def test_intake_issue_fields_identity_regression(tmp_path, workflow, fallback, preserve):
    result, state, _ = run_identity_intake(tmp_path, case='B1', mode='issue_fields', fallback=fallback,
                                          preserve=preserve, workflow=workflow)
    assert result.returncode == 0, result.stderr
    expected = {'Priority':'High','Effort':'Large'} if preserve else {'Priority':'Medium','Effort':'Small'}
    assert state['issue_values'] == expected
    assert state['values']['10'] == 'Backlog'
    assert state['values']['13'] == ('CLI' if preserve else 'Product')
    assert state['values']['14'] == ('Contract Hardening' if preserve else 'Adoption Polish')
    assert not {'11','12','900'} & set(state.get('edits', []))


@pytest.mark.parametrize('workflow', ['.github/workflows/project-intake.yml', 'templates/project-intake.yml'])
def test_intake_issue_value_cannot_satisfy_legacy_readback(tmp_path, workflow):
    result, _, _ = run_identity_intake(tmp_path, case='B1', mode='unset', workflow=workflow, bad_readback=True)
    assert result.returncode != 0
    assert 'validation failed after the GraphQL update' in result.stderr
