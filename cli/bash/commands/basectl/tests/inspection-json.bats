#!/usr/bin/env bats

load ./basectl_helpers.bash

assert_json() {
    local document="$1"
    shift

    printf '%s\n' "$document" | jq -e "$@" >/dev/null
}

run_inspection_basectl() {
    run --separate-stderr env \
        HOME="$TEST_HOME" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" "$@"
}

write_inspection_issue_gh_mock() {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "issue" && "$2" == "view" ]]; then
    if [[ "${BASE_GH_TEST_FAIL_ISSUE_VIEW:-0}" == "1" ]]; then
        printf 'upstream unavailable\n' >&2
        exit 7
    fi
    if [[ "$*" == *"--json body --jq .body"* ]]; then
        cat "${BASE_GH_TEST_STATE_DIR:?}/issue-body"
        exit 0
    fi
    if [[ "$*" == *"--json labels --jq .labels[].name"* ]]; then
        [[ "${BASE_GH_TEST_EMPTY_METADATA:-0}" == "1" ]] || printf 'enhancement\nagent-ready\n'
        exit 0
    fi
    if [[ "$*" == *"--json assignees --jq .assignees[].login"* ]]; then
        [[ "${BASE_GH_TEST_EMPTY_METADATA:-0}" == "1" ]] || printf 'codeforester\n'
        exit 0
    fi
fi
if [[ "$1" == "project" && "$2" == "item-list" ]]; then
    if [[ "${BASE_GH_TEST_PROJECT_MISSING:-0}" == "1" ]]; then
        printf 'Ready\037P2\037\037CLI\037\n'
    else
        printf 'Ready\037P2\037M\037CLI\037Contract Hardening\n'
    fi
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"
}

write_complete_inspection_issue_body() {
    cat > "$TEST_STATE_DIR/issue-body" <<'EOF'
## Goal
Provide stable JSON.

## Background
Automation must not parse prose.

## Scope
- Add inspection payloads.

## Acceptance Criteria
- Payloads are versioned.

## Validation
- Run focused tests.

## Non-Goals
- Do not change policy.

## Project Fields
- Status, Priority, Size, Area, Initiative.

## Agent Assignment
- Ready for implementation.
EOF
}

@test "shared shell serializer escapes quotes, slashes, whitespace, and control bytes" {
    local expected=$'quote" slash\\ newline\n tab\t control\001 unicode-café'

    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/inspection_json.sh"
            value=$'\''quote" slash\\ newline\n tab\t control\001 unicode-café'\''
            printf -v data "{\"value\":%s}" "$(base_inspection_json_string "$value")"
            base_inspection_json_envelope "repo check" ok "$data" null
        '

    [ "$status" -eq 0 ]
    assert_json "$output" --arg expected "$expected" '.data.value == $expected'
}

@test "shared shell serializer converts invalid UTF-8 bytes to valid JSON escapes" {
    local expected=$'\302\200'

    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/inspection_json.sh"
            value=$(printf "\200")
            printf -v data "{\"value\":%s}" "$(base_inspection_json_string "$value")"
            base_inspection_json_envelope "repo check" ok "$data" null
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *'\u0080'* ]]
    assert_json "$output" --arg expected "$expected" '.data.value == $expected'
}

@test "JSON-selected usage failures stay structured after a later invalid format" {
    run_inspection_basectl repo check . --format json --format yaml

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" '.command == "repo check" and .error.type == "usage_error"'

    run_inspection_basectl gh branch stale --format json --format yaml

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" '.command == "gh branch stale" and .error.type == "usage_error"'

    run_inspection_basectl gh issue readiness 123 --format json --format yaml

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" '.command == "gh issue readiness" and .error.type == "usage_error"'
}

@test "repo check JSON reports success with escaped paths" {
    local repo_dir="$TEST_TMPDIR/demo-\"quoted\""

    run_basectl repo init demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]

    run_inspection_basectl repo check "$repo_dir" --format json

    [ "$status" -eq 0 ]
    [ -z "$stderr" ]
    assert_json "$output" \
        '.schema_version == 1 and .command == "repo check" and .status == "ok" and .error == null'
    assert_json "$output" \
        'keys == ["command","data","error","schema_version","status"] and
         (.data | keys) == ["checks","path","summary"] and
         (.data.summary | keys) == ["checks","failed","passed"] and
         (.data.checks[0] | keys) == ["missing_files","name","not_executable_files","present_count","required_count","status"]'
    assert_json "$output" --arg path "$repo_dir" ".data.path == \$path"
    assert_json "$output" \
        '.data.summary == {"checks":1,"passed":1,"failed":0} and .data.checks[0].missing_files == []'
}

@test "repo check JSON reports inspection findings without an execution error" {
    local repo_dir="$TEST_TMPDIR/incomplete"
    local text_status

    mkdir -p "$repo_dir"
    printf '# Incomplete\n' > "$repo_dir/README.md"

    run_inspection_basectl repo check "$repo_dir" --agent-ready --release
    text_status="$status"

    run_inspection_basectl repo check "$repo_dir" --format json --agent-ready --release

    [ "$status" -eq "$text_status" ]
    [ "$status" -eq 1 ]
    [ -z "$stderr" ]
    assert_json "$output" \
        '.status == "error" and .error == null and .data.summary.failed == 3'
    assert_json "$output" \
        '.data.checks[0].name == "baseline" and (.data.checks[0].missing_files | index("VERSION")) != null'
    assert_json "$output" \
        '.data.checks[1].name == "release" and .data.checks[2].name == "agent_readiness"'
    assert_json "$output" \
        '(.data.checks[1] | keys) == ["manifest_declared","manifest_path","name","process_document_path","process_document_present","status"] and
         (.data.checks[2] | keys) == ["missing_files","name","present_count","required_count","status"]'
}

@test "repo check JSON usage failures use a controlled error object" {
    run_inspection_basectl repo check --format json --unknown

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" \
        '.status == "error" and .data == {} and .error.type == "usage_error"'
}

@test "gh issue readiness JSON covers ready and empty metadata" {
    write_inspection_issue_gh_mock
    write_complete_inspection_issue_body

    BASE_GH_TEST_EMPTY_METADATA=1 run_inspection_basectl \
        gh issue readiness 00123 --repo basefoundry/base \
        --project-owner basefoundry --project-number 010 --format json

    [ "$status" -eq 0 ]
    [ -z "$stderr" ]
    assert_json "$output" \
        '.command == "gh issue readiness" and .status == "ok" and .error == null'
    assert_json "$output" \
        '.data.issue_number == 123 and .data.project.number == 10 and .data.readiness == "ready" and .data.labels == [] and .data.assignees == []'
    assert_json "$output" \
        '.data.body.missing_sections == [] and .data.project.fields.size == "M"'
    assert_json "$output" \
        '(.data | keys) == ["assignees","body","issue_number","labels","project","readiness","repository"] and
         (.data.body | keys) == ["missing_sections","status"] and
         (.data.project | keys) == ["fields","missing_fields","number","owner","requested","status"] and
         (.data.project.fields | keys) == ["area","initiative","priority","size","status"]'
}

@test "gh issue readiness JSON represents partial and missing-field findings" {
    local text_status

    write_inspection_issue_gh_mock
    write_complete_inspection_issue_body

    run_inspection_basectl gh issue readiness 123 --repo basefoundry/base
    text_status="$status"

    run_inspection_basectl gh issue readiness 123 --repo basefoundry/base --format json

    [ "$status" -eq "$text_status" ]
    [ "$status" -eq 1 ]
    assert_json "$output" \
        '.status == "warn" and .error == null and .data.readiness == "partial" and .data.project.status == "skipped"'

    BASE_GH_TEST_PROJECT_MISSING=1 run_inspection_basectl \
        gh issue readiness 123 --repo basefoundry/base \
        --project-owner basefoundry --project-number 10 --format json

    [ "$status" -eq 1 ]
    assert_json "$output" \
        '.status == "error" and .error == null and .data.readiness == "not_ready"'
    assert_json "$output" \
        '(.data.project.missing_fields | index("Size")) != null and (.data.project.missing_fields | index("Initiative")) != null'
}

@test "gh issue readiness JSON controls usage and upstream failures" {
    write_inspection_issue_gh_mock
    write_complete_inspection_issue_body

    run_inspection_basectl gh issue readiness nope --format json --repo basefoundry/base

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" '.error.type == "usage_error" and .data == {}'

    BASE_GH_TEST_FAIL_ISSUE_VIEW=1 run_inspection_basectl \
        gh issue readiness 123 --repo basefoundry/base --format json

    [ "$status" -eq 7 ]
    [[ "$stderr" == *"GitHub command failed"* ]]
    assert_json "$output" \
        '.status == "error" and .data == {} and .error.type == "upstream_error" and .error.details.operation == "issue_view_body"'
}

@test "gh branch stale JSON covers findings and empty results" {
    local repo="$TEST_TMPDIR/repo"

    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    cd "$repo"
    run_inspection_basectl gh branch stale --days 000 --format json

    [ "$status" -eq 0 ]
    [ -z "$stderr" ]
    assert_json "$output" \
        '.command == "gh branch stale" and .status == "warn" and .error == null and (.data.branches | length) >= 1'
    assert_json "$output" \
        '(.data | keys) == ["branches","days","inspected_at_unix"] and
         (.data.branches[0] | keys) == ["age_days","last_commit","last_commit_unix","name","scope"] and
         (.data.branches[0] | (.name | type == "string") and
          (.scope == "local" or .scope == "remote") and
          (.age_days | type == "number") and (.last_commit | type == "string") and
          (.last_commit_unix | type == "number"))'

    run_inspection_basectl gh branch stale --days 999999 --format json

    [ "$status" -eq 0 ]
    assert_json "$output" '.status == "ok" and .data.branches == []'
}

@test "gh branch stale JSON controls invalid input and git failures" {
    local repo="$TEST_TMPDIR/repo"

    init_git_repo "$repo"
    cd "$repo"

    run_inspection_basectl gh branch stale --format json --days nope

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" '.error.type == "usage_error" and .data == {}'

    run_inspection_basectl gh branch stale \
        --format json --days 999999999999999999999999999999999999

    [ "$status" -eq 2 ]
    [ -z "$stderr" ]
    assert_json "$output" \
        '.error.type == "usage_error" and (.error.message | contains("integer range"))'

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            git() {
                if [[ "${1:-}" == "for-each-ref" ]]; then
                    printf "git refs unavailable\n" >&2
                    return 9
                fi
                command git "$@"
            }
            base_gh_subcommand_main branch stale --format json
        ' bash "$repo"

    [ "$status" -eq 9 ]
    [[ "$stderr" == *"git refs unavailable"* ]]
    assert_json "$output" '.error.type == "upstream_error" and .error.details.operation == "git_for_each_ref"'
}
