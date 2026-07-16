#!/usr/bin/env bats

load ./basectl_helpers.bash

write_gh_args_recorder() {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"
}

add_github_origin() {
    git -C "$1" remote add origin https://github.com/basefoundry/base.git
}

write_branch_issue_gh_mock() {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${BASE_GH_TEST_STATE_DIR:?}/gh-calls"
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == repos/*/issues/117 ]]; then
    case "${BASE_GH_TEST_ISSUE_MODE:-valid}" in
        nonexistent)
            printf 'gh: Not Found (HTTP 404)\n' >&2
            exit 1
            ;;
        pull-request)
            printf 'pull_request\n'
            exit 0
            ;;
    esac
    if [[ "$*" == *".title"* ]]; then
        printf 'issue\n%s\n' "${BASE_GH_TEST_ISSUE_TITLE:-Add basectl gh workflow for issues}"
        exit 0
    fi
    if [[ "$*" == *".labels[].name"* ]]; then
        printf 'issue\n'
        case "${BASE_GH_TEST_ISSUE_MODE:-valid}" in
            valid)
                printf 'enhancement\nneeds-demo\n'
                ;;
            missing-category)
                printf 'needs-demo\n'
                ;;
            multiple-categories)
                printf 'bug\nenhancement\n'
                ;;
            *)
                printf 'unexpected issue mode: %s\n' "$BASE_GH_TEST_ISSUE_MODE" >&2
                exit 98
                ;;
        esac
        exit 0
    fi
    printf 'unexpected issue api args: %s\n' "$*" >&2
    exit 98
fi
if [[ "$1" == "pr" && "$2" == "create" ]]; then
    printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
    body_file=""
    while (($#)); do
        if [[ "$1" == "--body-file" ]]; then
            body_file="$2"
            break
        fi
        shift
    done
    [[ -z "$body_file" ]] || cat "$body_file" > "${BASE_GH_TEST_STATE_DIR:?}/body"
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"
}

create_branch_pr_repo() {
    local branch="$2"
    local repo="$1"

    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "$branch" >/dev/null
    write_branch_issue_gh_mock
}

run_branch_pr_create() {
    local issue_mode="$2"
    local repo="$1"
    shift 2

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_ISSUE_MODE="$issue_mode" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            shift
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create "$@"
        ' bash "$repo" --no-fixes "$@"
}

write_issue_readiness_gh_mock() {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "issue" && "$2" == "view" ]]; then
    if [[ "${BASE_GH_TEST_FAIL_ISSUE_VIEW:-0}" == "1" ]]; then
        printf 'GraphQL: Could not resolve to an Issue\n' >&2
        exit 1
    fi
    if [[ "$*" == *"--json body --jq .body"* ]]; then
        cat "${BASE_GH_TEST_STATE_DIR:?}/issue-body"
        exit 0
    fi
    if [[ "$*" == *"--json labels --jq .labels[].name"* ]]; then
        printf 'enhancement\nagent-ready\n'
        exit 0
    fi
    if [[ "$*" == *"--json assignees --jq .assignees[].login"* ]]; then
        printf 'codeforester\n'
        exit 0
    fi
fi
if [[ "$1" == "project" && "$2" == "item-list" ]]; then
    case "${BASE_GH_TEST_PROJECT_MODE:-complete}" in
        complete)
            printf 'Ready\037P2\037M\037CLI\037Agentic Coding Platform\n'
            ;;
        missing)
            printf 'Ready\037P2\037\037CLI\037\n'
            ;;
        none)
            ;;
    esac
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"
}

write_complete_issue_readiness_body() {
    cat > "$TEST_STATE_DIR/issue-body" <<'EOF'
## Goal
Make agent assignment deterministic.

## Background
Base needs issue context before a coding agent starts.

## Scope
- Add a read-only readiness check.

## Acceptance Criteria
- Complete issues report ready.

## Validation
- Run focused BATS coverage.

## Non-Goals
- Do not assign issues.

## Project Fields
- Priority, Status, Size, Area, Initiative are required.

## Agent Assignment
- Assign to codeforester after readiness passes.
EOF
}

write_incomplete_issue_readiness_body() {
    cat > "$TEST_STATE_DIR/issue-body" <<'EOF'
## Goal
Make agent assignment deterministic.

## Background
Base needs issue context before a coding agent starts.

## Scope
- Add a read-only readiness check.
EOF
}

run_gh_subcommand() {
    local cwd="${BASE_GH_TEST_CWD:-$TEST_HOME}"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_CWD="$cwd" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_GH_PROJECT_WRAPPER="${BASE_GH_PROJECT_WRAPPER:-}" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$BASE_GH_TEST_CWD"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main "$@"
        ' bash "$@"
}

@test "basectl gh imports reusable GitHub CLI helpers" {
    local bash_libs_dir

    bash_libs_dir="$(base_bash_libs_fixture_dir)"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            [[ "$(type -t gh_require_cli)" == "function" ]]
            [[ "$(type -t gh_auth_status_diagnostics)" == "function" ]]
            [[ "$(type -t gh_run)" == "function" ]]
            [[ "$(type -t git_detect_default_branch)" == "function" ]]
            [[ "$(type -t gh_infer_repo_from_origin)" == "function" ]]
            [[ "$(type -t git_worktree_path_for_branch)" == "function" ]]
            [[ "$(type -t git_branch_merged_to_ref)" == "function" ]]
        '

    [ "$status" -eq 0 ]
}

@test "basectl gh default branch and repo inference delegate to reusable gh helpers" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            git_detect_default_branch() {
                printf -v "$2" "%s" "develop"
            }
            gh_infer_repo_from_origin() {
                printf -v "$2" "%s" "owner/repo"
            }
            printf "default=%s\n" "$(base_gh_default_branch)"
            printf "repo=%s\n" "$(base_gh_infer_github_repo)"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"default=develop"* ]]
    [[ "$output" == *"repo=owner/repo"* ]]
}

@test "basectl gh joins CSV output through reusable string helper" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            str_join() {
                printf "%s\n" "$*" > "${BASE_GH_TEST_STATE_DIR:?}/str-join"
                printf -v "$1" "%s" "joined-by-helper"
            }
            base_gh_join_csv Status Priority Area
        '

    [ "$status" -eq 0 ]
    [ "$output" = "joined-by-helper" ]
    [ "$(cat "$TEST_STATE_DIR/str-join")" = "joined ,  values" ]
}

@test "basectl gh prints help" {
    run_basectl gh --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"basectl gh project doctor --project <title>"* ]]
    [[ "$output" == *"basectl gh project configure --project <title>"* ]]
    [[ "$output" == *"basectl gh project issue set-fields <number>"* ]]
    [[ "$output" == *"basectl gh worktree prune"* ]]
    [[ "$output" != *"basectl gh todo"* ]]
    [[ "$output" == *"<category>/<issue>-<YYYYMMDD>-<slug>"* ]]
    [[ "$output" == *"sets project.issue_defaults.assignee"* ]]
}

@test "basectl gh issue prints area help" {
    run_basectl gh issue --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh issue list"* ]]
    [[ "$output" == *"basectl gh issue create"* ]]
    [[ "$output" == *"basectl gh issue readiness <number>"* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"Issue create project options:"* ]]
    [[ "$output" == *"--assignee <login>"* ]]
    [[ "$output" == *"--no-assignee"* ]]
    [[ "$output" == *"--size <T|S|M|L>"* ]]
    [[ "$output" == *"--repo, -R <owner/name>"* ]]
    [[ "$output" == *"the explicit option, GH_REPO, then the origin remote"* ]]
    [[ "$output" == *"Default category: enhancement."* ]]
    [[ "$output" == *"Default assignee: none unless project.issue_defaults.assignee is set in .github/base-project.yml."* ]]
    [[ "$output" == *"Categories: bug, enhancement, documentation, ci, security."* ]]
    [[ "$output" != *"basectl gh pr create"* ]]
    [[ "$output" != *"basectl gh worktree prune"* ]]
}

@test "basectl gh issue start prints leaf help without an issue number" {
    run_basectl gh issue start --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"--repo, -R <owner/name>"* ]]
    [[ "$output" == *"--category <category>"* ]]
    [[ "$output" == *"--title <title>"* ]]
    [[ "$output" != *"basectl gh issue create"* ]]
    [[ "$output" != *"ERROR:"* ]]
}

@test "basectl gh issue leaves print command-scoped help" {
    run_basectl gh issue list --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh issue list [gh options...]"* ]]
    [[ "$output" != *"--category"* ]]

    run_basectl gh issue create --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh issue create --title <title> [options]"* ]]
    [[ "$output" == *"--no-project"* ]]
    [[ "$output" != *"--project-number"* ]]

    run_basectl gh issue readiness --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh issue readiness <number> [options]"* ]]
    [[ "$output" == *"--project-number <number>"* ]]
    [[ "$output" != *"--category"* ]]
}

@test "basectl gh issue readiness reports ready when body and Project metadata are complete" {
    write_issue_readiness_gh_mock
    write_complete_issue_readiness_body

    run_gh_subcommand issue readiness 123 --repo basefoundry/base --project-owner basefoundry --project-number 10

    [ "$status" -eq 0 ]
    [[ "$output" == *"Issue #123 readiness: ready"* ]]
    [[ "$output" == *"Repository: basefoundry/base"* ]]
    [[ "$output" == *"Body sections: ok"* ]]
    [[ "$output" == *"Project fields: ok"* ]]
    [[ "$output" == *"Labels: enhancement, agent-ready"* ]]
    [[ "$output" == *"Assignees: codeforester"* ]]
}

@test "basectl gh issue readiness reports partial when Project validation is omitted" {
    write_issue_readiness_gh_mock
    write_complete_issue_readiness_body

    run_gh_subcommand issue readiness 123 --repo basefoundry/base

    [ "$status" -eq 1 ]
    [[ "$output" == *"Issue #123 readiness: partial"* ]]
    [[ "$output" == *"Body sections: ok"* ]]
    [[ "$output" == *"Project fields: skipped"* ]]
    [[ "$output" == *"Pass --project-owner and --project-number to validate Project fields."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-args")" != *"project item-list"* ]]
}

@test "basectl gh issue readiness reports missing body sections with fix hints" {
    write_issue_readiness_gh_mock
    write_incomplete_issue_readiness_body

    run_gh_subcommand issue readiness 123 --repo basefoundry/base --project-owner basefoundry --project-number 10

    [ "$status" -eq 1 ]
    [[ "$output" == *"Issue #123 readiness: not ready"* ]]
    [[ "$output" == *"Body sections: missing Acceptance Criteria, Validation, Non-Goals, Project Fields, Agent Assignment"* ]]
    [[ "$output" == *"Fix hint: add non-empty ## sections for the missing issue context."* ]]
}

@test "basectl gh issue readiness reports missing Project metadata" {
    write_issue_readiness_gh_mock
    write_complete_issue_readiness_body

    BASE_GH_TEST_PROJECT_MODE=missing \
        run_gh_subcommand issue readiness 123 --repo basefoundry/base --project-owner basefoundry --project-number 10

    [ "$status" -eq 1 ]
    [[ "$output" == *"Issue #123 readiness: not ready"* ]]
    [[ "$output" == *"Project fields: missing Size, Initiative"* ]]
    [[ "$output" == *"Fix hint: set missing Project fields before assigning implementation work."* ]]
}

@test "basectl gh issue readiness reports GitHub API failures" {
    write_issue_readiness_gh_mock
    write_complete_issue_readiness_body

    BASE_GH_TEST_FAIL_ISSUE_VIEW=1 \
        run_gh_subcommand issue readiness 123 --repo basefoundry/base

    [ "$status" -eq 1 ]
    [[ "$output" == *"GraphQL: Could not resolve to an Issue"* ]]
    [[ "$output" == *"GitHub command failed: gh issue view 123 --repo basefoundry/base --json body --jq .body"* ]]
}

@test "basectl gh pr prints area help" {
    run_basectl gh pr --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh pr create"* ]]
    [[ "$output" == *"basectl gh pr checks"* ]]
    [[ "$output" == *"basectl gh pr merge"* ]]
    [[ "$output" == *"basectl gh pr create [--no-fixes] [gh options...]"* ]]
    [[ "$output" == *"--no-fixes"* ]]
    [[ "$output" == *"issue-linked PR workflow"* ]]
    [[ "$output" != *"basectl gh issue create"* ]]
    [[ "$output" != *"basectl gh branch prune"* ]]
}

@test "basectl gh pr leaves print command-scoped help" {
    run_basectl gh pr create --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh pr create [gh options...]"* ]]
    [[ "$output" == *"--no-fixes"* ]]
    [[ "$output" != *"basectl gh pr merge"* ]]

    run_basectl gh pr status --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh pr status [gh options...]"* ]]
    [[ "$output" != *"--no-fixes"* ]]
    [[ "$output" != *"basectl gh pr create"* ]]
}

@test "basectl gh project prints area help" {
    run_basectl gh project --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh project doctor --project <title>"* ]]
    [[ "$output" == *"basectl gh project configure --project <title>"* ]]
    [[ "$output" == *"basectl gh project issue set-fields <number>"* ]]
    [[ "$output" == *"Project operations delegate to Base's Python Project engine."* ]]
    [[ "$output" != *"basectl gh issue create"* ]]
    [[ "$output" != *"basectl gh worktree prune"* ]]
}

@test "basectl gh project configure help lists delegated Python options" {
    run_basectl gh project configure --help

    [ "$status" -eq 0 ]
    for flag in "--schema base-project" "--config <path>" "--copy-fields-from <title>" "--replace-project" "--initiative-option <name>" "--dry-run"; do
        [[ "$output" == *"$flag"* ]]
    done
}

@test "basectl gh project and branch leaves print command-scoped help" {
    run_basectl gh project doctor --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh project doctor --project <title> [options]"* ]]
    [[ "$output" == *"--schema base-project"* ]]
    [[ "$output" != *"--dry-run"* ]]
    [[ "$output" != *"basectl gh project configure"* ]]

    run_basectl gh branch stale --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh branch stale [--days <days>]"* ]]
    [[ "$output" != *"--dry-run"* ]]
    [[ "$output" != *"--remote"* ]]

    run_basectl gh branch prune --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh branch prune [options]"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"--remote"* ]]
    [[ "$output" != *"--days"* ]]
}

@test "basectl gh project issue set-fields prints concrete help" {
    run_basectl gh project issue set-fields --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh project issue set-fields <number>"* ]]
    [[ "$output" == *"--status <name>"* ]]
    [[ "$output" == *"--priority <name>"* ]]
    [[ "$output" == *"--area <name>"* ]]
    [[ "$output" == *"--initiative <name>"* ]]
    [[ "$output" == *"--size <T|S|M|L>"* ]]
    [[ "$output" != *"[field options...]"* ]]
    [[ "$output" != *"basectl gh project configure"* ]]
}

@test "basectl gh rejects retired todo area" {
    run_basectl gh todo --help

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown gh area 'todo'."* ]]
    [[ "$output" != *"TODO.md"* ]]
    [[ "$output" != *"basectl gh todo plan"* ]]
}

@test "basectl gh usage errors return status 2" {
    run_basectl gh issue unknown

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown gh issue command 'unknown'."* ]]
    [[ "$output" == *"basectl gh issue create"* ]]

    run_basectl gh issue create

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Missing required --title."* ]]

    run_basectl gh issue create --bad-option

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown option '--bad-option'."* ]]
}

@test "basectl gh slug generation does not require tr or sed" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            tr() { printf "tr should not run\n" >&2; return 97; }
            sed() { printf "sed should not run\n" >&2; return 98; }
            printf "slug=%s\n" "$(base_gh_slug "  A/B: Thing -- #42!  ")"
            printf "fallback=%s\n" "$(base_gh_slug "!!!")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"slug=a-b-thing-42"* ]]
    [[ "$output" == *"fallback=work"* ]]
    [[ "$output" != *"tr should not run"* ]]
    [[ "$output" != *"sed should not run"* ]]
}

@test "basectl gh issue create accepts explicit assignee" {
    write_gh_args_recorder

    run_gh_subcommand issue create --category bug --title "Repair branch pruning" \
        --repo codeforester/base --assignee codeforester --no-project

    [ "$status" -eq 0 ]
    [[ "$output" != *"Using default --category"* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Repair branch pruning --label bug --assignee codeforester --repo codeforester/base" ]
}

@test "basectl gh issue create announces default category without forcing an assignee" {
    write_gh_args_recorder

    run_gh_subcommand issue create --title "Default category issue" \
        --repo codeforester/base --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"Using default --category: enhancement"* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Default category issue --label enhancement --repo codeforester/base" ]
}

@test "basectl gh issue create uses repo config assignee default" {
    write_gh_args_recorder
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
if [[ "$*" == *" base_github_projects project issue defaults "* ]]; then
    printf 'assignee\tcodeforester\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    BASE_GH_TEST_CWD="$BASE_REPO_ROOT" \
        BASE_GH_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        run_gh_subcommand issue create --category bug --title "Base repo issue" \
            --repo basefoundry/base --no-project

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Base repo issue --label bug --assignee codeforester --repo basefoundry/base" ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project issue defaults --config $BASE_REPO_ROOT/.github/base-project.yml" ]
}

@test "basectl gh issue create reads assignee defaults through Python project config" {
    local repo
    local repo_root

    repo="$TEST_TMPDIR/base-like"
    init_git_repo "$repo"
    repo_root="$(cd "$repo" && pwd -P)"
    git -C "$repo" remote add origin git@github.com:basefoundry/base-like.git
    mkdir -p "$repo/.github"
    cat > "$repo/.github/base-project.yml" <<'EOF'
project:
  issue_defaults: {assignee: codeforester}
EOF
    write_gh_args_recorder
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
if [[ "$*" == *" base_github_projects project issue defaults "* ]]; then
    printf 'assignee\tcodeforester\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    BASE_GH_TEST_CWD="$repo" \
        BASE_GH_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        run_gh_subcommand issue create --category bug --title "Base-like repo issue" \
            --repo basefoundry/base-like --no-project

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Base-like repo issue --label bug --assignee codeforester --repo basefoundry/base-like" ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project issue defaults --config $repo_root/.github/base-project.yml" ]
}

@test "basectl gh issue create --no-assignee ignores repo config assignee default" {
    write_gh_args_recorder

    BASE_GH_TEST_CWD="$BASE_REPO_ROOT" \
        run_gh_subcommand issue create --category bug --title "Unassigned Base repo issue" \
            --repo basefoundry/base --no-assignee --no-project

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Unassigned Base repo issue --label bug --repo basefoundry/base" ]
}

@test "basectl gh issue create continues when auth status is transiently unavailable" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    printf 'github.com\n' >&2
    printf '  X failed to reach api.github.com\n' >&2
    exit 1
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "issue" && "$2" == "create" ]]; then
    printf 'https://github.com/codeforester/base/issues/749\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue create --category bug --title "Make auth preflight resilient" --repo codeforester/base --assignee codeforester --no-project
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"https://github.com/codeforester/base/issues/749"* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Make auth preflight resilient --label bug --assignee codeforester --repo codeforester/base" ]
}

@test "basectl gh issue create updates repo project metadata when repo is known" {
    local repo
    local repo_root

    repo="$TEST_TMPDIR/bankbuddy"
    init_git_repo "$repo"
    repo_root="$(cd "$repo" && pwd -P)"
    git -C "$repo" remote add origin git@github.com:codeforester/bankbuddy.git
    mkdir -p "$repo/.github"
    cat > "$repo/.github/base-project.yml" <<'EOF'
project:
  areas:
    - CLI
  initiatives:
    - MVP
  issue_defaults:
    status: Backlog
    priority: P1
    size: M
    area: CLI
    initiative: MVP
EOF
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "issue" && "$2" == "create" ]]; then
    printf 'https://github.com/codeforester/bankbuddy/issues/51\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/gh"
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *" base_github_projects project issue defaults "* ]]; then
    printf 'status\tBacklog\n'
    printf 'priority\tP1\n'
    printf 'size\tM\n'
    printf 'area\tCLI\n'
    printf 'initiative\tMVP\n'
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_GH_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue create --category enhancement --title "Add transaction filter"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"https://github.com/codeforester/bankbuddy/issues/51"* ]]
    [[ "$output" == *"Project 'bankbuddy': Status=Backlog, Priority=P1, Size=M, Area=CLI, Initiative=MVP applied."* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Add transaction filter --label enhancement --repo codeforester/bankbuddy" ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project issue set-fields 51 --project bankbuddy --owner codeforester --repo codeforester/bankbuddy --config $repo_root/.github/base-project.yml" ]
}

@test "basectl gh issue create accepts explicit project size override" {
    local repo
    local repo_root

    repo="$TEST_TMPDIR/bankbuddy"
    init_git_repo "$repo"
    repo_root="$(cd "$repo" && pwd -P)"
    git -C "$repo" remote add origin git@github.com:codeforester/bankbuddy.git
    mkdir -p "$repo/.github"
    cat > "$repo/.github/base-project.yml" <<'EOF'
project:
  issue_defaults:
    status: Backlog
    priority: P2
    size: S
EOF
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "issue" && "$2" == "create" ]]; then
    printf 'https://github.com/codeforester/bankbuddy/issues/52\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/gh"
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *" base_github_projects project issue defaults "* ]]; then
    printf 'status\tBacklog\n'
    printf 'priority\tP2\n'
    printf 'size\tS\n'
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_GH_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue create --category enhancement --title "Fix typo" --size T
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"https://github.com/codeforester/bankbuddy/issues/52"* ]]
    [[ "$output" == *"Project 'bankbuddy': Status=Backlog, Priority=P2, Size=T applied."* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Fix typo --label enhancement --repo codeforester/bankbuddy" ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project issue set-fields 52 --project bankbuddy --owner codeforester --repo codeforester/bankbuddy --config $repo_root/.github/base-project.yml --size T" ]
}

@test "basectl gh issue create warns when project metadata update fails" {
    local repo
    local repo_root

    repo="$TEST_TMPDIR/bankbuddy"
    init_git_repo "$repo"
    repo_root="$(cd "$repo" && pwd -P)"
    git -C "$repo" remote add origin git@github.com:codeforester/bankbuddy.git
    mkdir -p "$repo/.github"
    cat > "$repo/.github/base-project.yml" <<'EOF'
project:
  issue_defaults:
    status: Backlog
    priority: P2
    size: S
EOF
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "issue" && "$2" == "create" ]]; then
    printf 'https://github.com/codeforester/bankbuddy/issues/53\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/gh"
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
printf 'project engine failed\n' >&2
exit 17
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_GH_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue create --category enhancement --title "Fix project metadata warning"
        ' bash "$repo"

    [ "$status" -eq 17 ]
    [[ "$output" == *"https://github.com/codeforester/bankbuddy/issues/53"* ]]
    [[ "$output" == *"project engine failed"* ]]
    [[ "$output" == *"Project field update failed. Set fields manually or rerun:"* ]]
    [[ "$output" == *"basectl gh project issue set-fields 53 --project bankbuddy --owner codeforester --repo codeforester/bankbuddy --config $repo_root/.github/base-project.yml"* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Fix project metadata warning --label enhancement --repo codeforester/bankbuddy" ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project issue set-fields 53 --project bankbuddy --owner codeforester --repo codeforester/bankbuddy --config $repo_root/.github/base-project.yml" ]
}

@test "basectl gh issue create help does not require authentication" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue create --help
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh issue create"* ]]
    [[ "$output" != *"GitHub CLI authentication is not ready."* ]]
    [[ "$output" != *"unexpected gh args"* ]]
}

@test "basectl gh project dispatches to Python engine" {
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
printf '%s\n' "${BASE_CLI_DISPLAY_COMMAND:-}" > "${BASE_GH_TEST_STATE_DIR:?}/display-command"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_GH_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main project doctor --project "Base Roadmap" --owner codeforester
        '

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project doctor --project Base Roadmap --owner codeforester" ]
    [ "$(cat "$TEST_STATE_DIR/display-command")" = "basectl gh" ]
}

@test "basectl gh issue list reports command failure with auth diagnostics" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    printf 'github.com\n' >&2
    printf '  X failed to reach api.github.com\n' >&2
    printf '  - check your internet connection or GitHub API access\n' >&2
    exit 1
fi
if [[ "$*" == "issue list" ]]; then
    printf 'HTTP 401: Bad credentials\n' >&2
    exit 1
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue list
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"HTTP 401: Bad credentials"* ]]
    [[ "$output" == *"GitHub command failed: gh issue list"* ]]
    [[ "$output" == *"gh auth status: github.com"* ]]
    [[ "$output" == *"gh auth status:   X failed to reach api.github.com"* ]]
    [[ "$output" == *"gh auth status:   - check your internet connection or GitHub API access"* ]]
    [[ "$output" != *"unexpected gh args"* ]]
}

@test "basectl gh issue start prints worktree command from issue metadata" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$(printf '%s\n' "$output" | sed -n '1p')" == "enhancement/117-"*"-add-basectl-gh-workflow-for-issues" ]]
    [ "$(printf '%s\n' "$output" | sed -n '2p')" = "" ]
    [ "$(printf '%s\n' "$output" | sed -n '3p')" = "To create a worktree:" ]
    [[ "$(printf '%s\n' "$output" | sed -n '4p')" == "  git worktree add -b enhancement/117-"*"-add-basectl-gh-workflow-for-issues "*"/repo-worktrees/117-add-basectl-gh-workflow-for-issues origin/master" ]]
    [ "$(git -C "$repo" branch --show-current)" = "master" ]
}

@test "basectl gh issue start verifies an explicit category and title against the issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 --category enhancement --title "Prune merged branches"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$(printf '%s\n' "$output" | sed -n '1p')" == "enhancement/117-"*"-prune-merged-branches" ]]
    [ "$(printf '%s\n' "$output" | sed -n '2p')" = "" ]
    [ "$(printf '%s\n' "$output" | sed -n '3p')" = "To create a worktree:" ]
    [[ "$(printf '%s\n' "$output" | sed -n '4p')" == "  git worktree add -b enhancement/117-"*"-prune-merged-branches "*"/repo-worktrees/117-prune-merged-branches origin/master" ]]
    [ "$(git -C "$repo" branch --show-current)" = "master" ]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" == *"api repos/basefoundry/base/issues/117 --jq"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"issue view 117"* ]]
}

@test "basectl gh issue start honors an explicit upstream repository before GH_REPO and origin" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    git -C "$repo" remote add origin https://github.com/fork-owner/base.git
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        GH_REPO="github.com/environment/base" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 -R upstream/base --title "Prune merged branches"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == "enhancement/117-"*"-prune-merged-branches"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" == *"api repos/upstream/base/issues/117 --jq"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"repos/environment/base/issues/117"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"repos/fork-owner/base/issues/117"* ]]
}

@test "basectl gh issue start honors GH_REPO before a fork origin" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    git -C "$repo" remote add origin https://github.com/fork-owner/base.git
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        GH_REPO="github.com/upstream/base" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 --title "Prune merged branches"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == "enhancement/117-"*"-prune-merged-branches"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" == *"api repos/upstream/base/issues/117 --jq"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"repos/fork-owner/base/issues/117"* ]]
}

@test "basectl gh issue start rejects an explicit category that mismatches the issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 --category bug --title "Prune merged branches"
        ' bash "$repo"

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--category bug' does not match issue #117 category 'enhancement'."* ]]
    [[ "$output" != *"To create a worktree:"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" == *"api repos/basefoundry/base/issues/117 --jq"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"issue view 117"* ]]
}

@test "basectl gh issue start gets branch date without date command" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    cat > "$TEST_MOCKBIN/date" <<'EOF'
#!/usr/bin/env bash
printf 'date should not run: %s\n' "$*" >&2
exit 42
EOF
    chmod +x "$TEST_MOCKBIN/date"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 --category enhancement --title "Prune merged branches"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "${lines[0]}" == "enhancement/117-"*"-prune-merged-branches" ]]
    [[ "$output" != *"date should not run"* ]]
}

@test "basectl gh issue start truncates worktree slug without cut or sed" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    write_branch_issue_gh_mock

    for tool in cut sed; do
        cat > "$TEST_MOCKBIN/$tool" <<'EOF'
#!/usr/bin/env bash
printf '%s should not run\n' "$(basename "$0")" >&2
exit 42
EOF
        chmod +x "$TEST_MOCKBIN/$tool"
    done

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 --category enhancement \
                --title "Alpha beta gamma delta epsilon zeta eta theta iota kappa"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"/repo-worktrees/117-alpha-beta-gamma-delta-epsilon-zeta-eta origin/"* ]]
    [[ "$output" != *"cut should not run"* ]]
    [[ "$output" != *"sed should not run"* ]]
}

@test "basectl gh pr create links current branch issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "enhancement/117-20260528-basectl-gh-workflow" >/dev/null
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-linking PR to issue #117 from branch name. Pass --no-fixes to suppress."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-args")" == pr\ create\ --fill\ --body-file* ]]
    [ "$(cat "$TEST_STATE_DIR/body")" = "Fixes #117" ]
}

@test "basectl gh branch policy accepts only canonical issue-backed names" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/github_policy.sh"
            [[ "$(base_github_branch_name enhancement 117 valid-branch 20260528)" == "enhancement/117-20260528-valid-branch" ]] || exit 1
            [[ "$(base_github_branch_name enhancement 117 leap-day 20240229)" == "enhancement/117-20240229-leap-day" ]] || exit 1
            for category in bug enhancement documentation ci security; do
                base_github_branch_category_is_valid "$category" || exit 1
                base_github_branch_name_is_valid "$category/117-20260528-valid-branch" || exit 1
            done
            if base_github_branch_category_is_valid feat; then
                printf "unexpected valid category: feat\n" >&2
                exit 1
            fi
            if base_github_branch_name feat 117 valid-branch 20260528 ||
                base_github_branch_name enhancement 0 valid-branch 20260528 ||
                base_github_branch_name enhancement 117 Invalid-slug 20260528; then
                printf "unexpected canonical branch generation success\n" >&2
                exit 1
            fi
            for branch in \
                117-missing-category \
                feat/117-20260528-wrong-category \
                enhancement/117-missing-date \
                enhancement/0-20260528-zero-issue \
                enhancement/117-2026052-short-date \
                enhancement/117-00000101-zero-year \
                enhancement/117-20260229-non-leap-day \
                enhancement/117-20260431-impossible-day \
                enhancement/117-20261301-impossible-month \
                enhancement/117-20260528-Uppercase-slug \
                enhancement/117-20260528-double--hyphen; do
                if base_github_branch_name_is_valid "$branch"; then
                    printf "unexpected valid branch: %s\n" "$branch" >&2
                    exit 1
                fi
            done
        '

    [ "$status" -eq 0 ]
}

@test "basectl gh pr target repository honors gh selectors before origin" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        GH_REPO="github.com/environment/project" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_infer_github_repo() {
                printf "origin/project\n"
            }

            [[ "$(base_gh_pr_target_repo --repo explicit/value)" == "explicit/value" ]] || exit 1
            [[ "$(base_gh_pr_target_repo --repo=equals/value)" == "equals/value" ]] || exit 1
            [[ "$(base_gh_pr_target_repo -R short/value)" == "short/value" ]] || exit 1
            [[ "$(base_gh_pr_target_repo -R=short-equals/value)" == "short-equals/value" ]] || exit 1
            [[ "$(base_gh_pr_target_repo --title Example)" == "environment/project" ]] || exit 1
            unset GH_REPO
            [[ "$(base_gh_pr_target_repo --title Example)" == "origin/project" ]] || exit 1
        '

    [ "$status" -eq 0 ]
}

@test "basectl gh pr create rejects a noncanonical branch before gh" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "feat/117-20260528-basectl-gh-workflow" >/dev/null

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create --no-fixes
        ' bash "$repo"

    [ "$status" -eq 2 ]
    [[ "$output" == *"Branch 'feat/117-20260528-basectl-gh-workflow' does not follow <category>/<issue>-<YYYYMMDD>-<slug>."* ]]
    [[ "$output" == *"Categories: bug, enhancement, documentation, ci, security."* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" != *"unexpected gh args"* ]]
}

@test "basectl gh pr create rejects a branch category that mismatches the issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    create_branch_pr_repo "$repo" "bug/117-20260528-basectl-gh-workflow"

    run_branch_pr_create "$repo" valid

    [ "$status" -eq 2 ]
    [[ "$output" == *"Branch category 'bug' does not match issue #117 category 'enhancement'."* ]]
    [[ "$output" == *"basectl gh issue start 117"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"pr create"* ]]
}

@test "basectl gh pr create rejects a nonexistent issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    create_branch_pr_repo "$repo" "enhancement/117-20260528-basectl-gh-workflow"

    run_branch_pr_create "$repo" nonexistent

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unable to determine the category label for GitHub issue #117 in 'basefoundry/base'. Confirm that the issue exists and is accessible."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"pr create"* ]]
}

@test "basectl gh pr create rejects a pull request number as its issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    create_branch_pr_repo "$repo" "enhancement/117-20260528-basectl-gh-workflow"

    run_branch_pr_create "$repo" pull-request

    [ "$status" -eq 2 ]
    [[ "$output" == *"GitHub reference #117 in 'basefoundry/base' is a pull request, not an issue."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"pr create"* ]]
}

@test "basectl gh pr create rejects multiple standard issue category labels" {
    local repo

    repo="$TEST_TMPDIR/repo"
    create_branch_pr_repo "$repo" "enhancement/117-20260528-basectl-gh-workflow"

    run_branch_pr_create "$repo" multiple-categories

    [ "$status" -eq 2 ]
    [[ "$output" == *"GitHub issue #117 in 'basefoundry/base' must have exactly one category label: bug, enhancement, documentation, ci, or security."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"pr create"* ]]
}

@test "basectl gh pr create rejects an issue missing a standard category label" {
    local repo

    repo="$TEST_TMPDIR/repo"
    create_branch_pr_repo "$repo" "enhancement/117-20260528-basectl-gh-workflow"

    run_branch_pr_create "$repo" missing-category

    [ "$status" -eq 2 ]
    [[ "$output" == *"GitHub issue #117 in 'basefoundry/base' must have exactly one category label: bug, enhancement, documentation, ci, or security."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"pr create"* ]]
}

@test "basectl gh pr create uses reusable temp helper for PR body" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "enhancement/117-20260528-basectl-gh-workflow" >/dev/null
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            eval "$(declare -f std_make_temp_file | sed "1s/std_make_temp_file/__orig_std_make_temp_file/")"
            std_make_temp_file() {
                printf "%s\n" "$*" >> "${BASE_GH_TEST_STATE_DIR:?}/temp-helper"
                __orig_std_make_temp_file "$@"
            }
            base_gh_subcommand_main pr create
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/temp-helper")" = "body_file basectl-gh-pr" ]
}

@test "basectl gh pr create renders project PR policy body" {
    local repo repo_root

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    repo_root="$(cd "$repo" && pwd -P)"
    mkdir -p "$repo/docs"
    cat > "$repo/base_manifest.yaml" <<'EOF'
project:
  name: demo
github:
  pr:
    required_sections:
      default:
        - Summary
        - Issue
        - Validation
      labels:
        needs-demo:
          - Demo Impact
      paths:
        docs/**:
          - Docs Impact
artifacts: []
EOF
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "enhancement/117-20260528-basectl-gh-workflow" >/dev/null
    printf 'docs\n' > "$repo/docs/workflow.md"
    commit_all "$repo" "Update docs"
    write_branch_issue_gh_mock
    cat > "$TEST_MOCKBIN/base-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
cat <<'BODY'
## Summary

## Issue

Fixes #117

## Validation

## Demo Impact

## Docs Impact
BODY
EOF
    chmod +x "$TEST_MOCKBIN/base-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_PYTHON_WRAPPER="$TEST_MOCKBIN/base-wrapper" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create --repo upstream/project
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-linking PR to issue #117 from branch name. Pass --no-fixes to suppress."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-args")" == pr\ create\ --fill\ --body-file*"--repo upstream/project"* ]]
    [[ "$(cat "$TEST_STATE_DIR/wrapper-args")" == *"base_pr_policy body --manifest $repo_root/base_manifest.yaml --issue 117"* ]]
    [[ "$(cat "$TEST_STATE_DIR/wrapper-args")" == *"--label needs-demo"* ]]
    [[ "$(cat "$TEST_STATE_DIR/wrapper-args")" == *"--path docs/workflow.md"* ]]
    [[ "$(cat "$TEST_STATE_DIR/body")" == *"## Demo Impact"* ]]
    [[ "$(cat "$TEST_STATE_DIR/body")" == *"## Docs Impact"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" == *"api repos/upstream/project/issues/117 --jq"* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-calls")" != *"api repos/basefoundry/base/issues/117"* ]]
}

@test "basectl gh pr create supports no-fixes opt out" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    add_github_origin "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "enhancement/117-20260528-basectl-gh-workflow" >/dev/null
    write_branch_issue_gh_mock

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create --no-fixes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" != *"Auto-linking PR"* ]]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "pr create --fill" ]
    [ ! -e "$TEST_STATE_DIR/body" ]
}

@test "basectl gh pr create help does not require authentication" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create --help
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh pr create"* ]]
    [[ "$output" != *"GitHub CLI authentication is not ready."* ]]
    [[ "$output" != *"unexpected gh args"* ]]
}
