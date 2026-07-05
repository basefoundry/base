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
        '

    [ "$status" -eq 0 ]
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
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"Issue create project options:"* ]]
    [[ "$output" == *"--assignee <login>"* ]]
    [[ "$output" == *"--no-assignee"* ]]
    [[ "$output" == *"--size <T|S|M|L>"* ]]
    [[ "$output" == *"Default category: enhancement."* ]]
    [[ "$output" == *"Default assignee: none unless project.issue_defaults.assignee is set in .github/base-project.yml."* ]]
    [[ "$output" == *"Categories: bug, enhancement, documentation, ci, security."* ]]
    [[ "$output" != *"basectl gh pr create"* ]]
    [[ "$output" != *"basectl gh worktree prune"* ]]
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
    run_basectl gh project --help

    [ "$status" -eq 0 ]
    for flag in "--schema base-project" "--config <path>" "--copy-fields-from <title>" "--replace-project" "--initiative-option <name>" "--dry-run"; do
        [[ "$output" == *"$flag"* ]]
    done
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

@test "basectl gh branch prints area help" {
    run_basectl gh branch --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh branch stale [--days <days>]"* ]]
    [[ "$output" == *"basectl gh branch prune [--dry-run] [--yes] [--remote]"* ]]
    [[ "$output" == *"Runs in dry-run mode by default. Pass --yes to apply changes."* ]]
    [[ "$output" == *"--dry-run      Preview branches that would be deleted (default)."* ]]
    [[ "$output" != *"basectl gh issue create"* ]]
    [[ "$output" != *"basectl gh worktree prune"* ]]
}

@test "basectl gh worktree prints area help" {
    run_basectl gh worktree --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh worktree prune [--dry-run] [--yes]"* ]]
    [[ "$output" == *"Prune safe, merged Git worktrees and their local branches."* ]]
    [[ "$output" == *"Runs in dry-run mode by default. Pass --yes to apply changes."* ]]
    [[ "$output" == *"--dry-run      Preview worktrees that would be removed (default)."* ]]
    [[ "$output" != *"basectl gh branch prune"* ]]
    [[ "$output" != *"basectl gh issue create"* ]]
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

    run_basectl gh branch stale --days never

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: --days must be a positive integer."* ]]
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

@test "basectl gh branch cleanup returns merge source without module global" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_branch_merged_to_ref() { return 0; }
            base_gh_branch_github_merged() { return 1; }
            BASE_GH_BRANCH_MERGE_SOURCE=preexisting
            merge_source=unset
            base_gh_branch_cleanup_merged feature main merge_source || exit $?
            printf "merge_source=%s\n" "$merge_source"
            printf "global=%s\n" "${BASE_GH_BRANCH_MERGE_SOURCE:-unset}"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"merge_source=git"* ]]
    [[ "$output" == *"global=preexisting"* ]]
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
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "issue view 117 --json labels --jq .labels[].name | select(. == \"bug\" or . == \"enhancement\" or . == \"documentation\" or . == \"ci\" or . == \"security\")" ]]; then
    printf 'enhancement\n'
    exit 0
fi
if [[ "$*" == "issue view 117 --json title --jq .title" ]]; then
    printf 'Add basectl gh workflow for issues\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
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
            base_gh_subcommand_main issue start 117
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$(printf '%s\n' "$output" | sed -n '1p')" == "enhancement/117-"*"-add-basectl-gh-workflow-for-issues" ]]
    [ "$(printf '%s\n' "$output" | sed -n '2p')" = "" ]
    [ "$(printf '%s\n' "$output" | sed -n '3p')" = "To create a worktree:" ]
    [[ "$(printf '%s\n' "$output" | sed -n '4p')" == "  git worktree add -b enhancement/117-"*"-add-basectl-gh-workflow-for-issues "*"/repo-worktrees/117-add-basectl-gh-workflow-for-issues origin/master" ]]
    [ "$(git -C "$repo" branch --show-current)" = "master" ]
}

@test "basectl gh issue start accepts explicit category and title without gh" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
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
}

@test "basectl gh issue start gets branch date without date command" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    cat > "$TEST_MOCKBIN/date" <<'EOF'
#!/usr/bin/env bash
printf 'date should not run: %s\n' "$*" >&2
exit 42
EOF
    chmod +x "$TEST_MOCKBIN/date"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
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
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

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

@test "basectl gh branch prune falls back to main when default branch is unknown" {
    local repo

    repo="$TEST_TMPDIR/repo"
    git init "$repo" >/dev/null 2>&1

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch prune
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Branch prune preview for default branch main."* ]]
}

@test "basectl gh branch prune defaults to dry-run" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" branch merged-work

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch prune
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Branch prune preview for default branch master."* ]]
    [[ "$output" == *"Local branches"* ]]
    [[ "$output" == *"[DRY-RUN] DELETE merged-work"* ]]
    [[ "$output" == *"Summary: 1 would delete, 0 skipped worktree, 0 skipped upstream, 0 failed."* ]]
    [[ "$output" == *"Run with --yes to apply these changes."* ]]
    git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
}

@test "basectl gh branch prune applies only with yes" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" branch merged-work

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"DELETE merged-work"* ]]
    [[ "$output" == *"Summary: 1 deleted, 0 skipped worktree, 0 skipped upstream, 0 failed."* ]]
    ! git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
}

@test "basectl gh branch prune reports worktree-attached branches as skipped" {
    local repo worktree

    repo="$TEST_TMPDIR/repo"
    worktree="$TEST_TMPDIR/merged-worktree"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" branch merged-work
    git -C "$repo" worktree add "$worktree" merged-work >/dev/null 2>&1

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP   merged-work  attached to worktree "*"/merged-worktree"* ]]
    [[ "$output" == *'Hint: run `basectl gh worktree prune` to inspect stale worktrees.'* ]]
    [[ "$output" == *"Summary: 0 deleted, 1 skipped worktree, 0 skipped upstream, 0 failed."* ]]
    git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
}

@test "basectl gh branch prune reports branches not fully merged to upstream as skipped" {
    local repo remote

    repo="$TEST_TMPDIR/repo"
    remote="$TEST_TMPDIR/remote.git"
    create_tracked_repo_with_upstream "$repo" "$remote" "README.md" "hello"
    git -C "$repo" switch -c merged-work >/dev/null
    git -C "$repo" push -u origin merged-work >/dev/null 2>&1
    printf 'topic change\n' >> "$repo/README.md"
    commit_all "$repo" "Topic change"
    git -C "$repo" switch master >/dev/null
    git -C "$repo" merge --ff-only merged-work >/dev/null

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP   merged-work  not fully merged to upstream origin/merged-work"* ]]
    [[ "$output" == *"Summary: 0 deleted, 0 skipped worktree, 1 skipped upstream, 0 failed."* ]]
    git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
}

@test "basectl gh branch prune --remote prints remote tracking refs separately" {
    local repo remote

    repo="$TEST_TMPDIR/repo"
    remote="$TEST_TMPDIR/remote.git"
    create_tracked_repo_with_upstream "$repo" "$remote" "README.md" "hello"
    git -C "$repo" update-ref refs/remotes/origin/stale-branch HEAD
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    printf 'unexpected auth status preflight\n' >&2
    exit 99
fi
if [[ "$*" == "pr list --head stale-branch --state merged --json number --jq length" ]]; then
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
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch prune --remote --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Local branches"* ]]
    [[ "$output" == *"GitHub branches"* ]]
    [[ "$output" == *"No merged GitHub remote branches found."* ]]
    [[ "$output" == *"Remote tracking refs"* ]]
    [[ "$output" == *"PRUNE origin/stale-branch"* ]]
    [[ "$output" == *"Note: remote-tracking ref cleanup prunes stale local origin/* refs after GitHub branch cleanup."* ]]
    [[ "$output" != *"unexpected auth status preflight"* ]]
    [[ "$output" != *"GitHub branch cleanup requires authenticated gh"* ]]
    [[ "$output" != *"Pruning origin"* ]]
    [[ "$output" != *"URL:"* ]]
    ! git -C "$repo" show-ref --verify --quiet refs/remotes/origin/stale-branch
}

@test "basectl gh branch stale gets current time without date command" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

cat > "$TEST_MOCKBIN/date" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/date"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main branch stale --days 0
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" != *$'\tunknown\tmaster'* ]]
    [[ "$output" == *$'\tmaster'* ]]
}

@test "base_gh_format_unix_date formats timestamps without date command" {
    cat > "$TEST_MOCKBIN/date" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/date"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_format_unix_date 1704110400
        '

    [ "$status" -eq 0 ]
    [ "$output" = "2024-01-01" ]
}

@test "basectl gh branch prune --remote previews safe GitHub branch deletion" {
    local repo remote

    repo="$TEST_TMPDIR/repo"
    remote="$TEST_TMPDIR/remote.git"
    create_tracked_repo_with_upstream "$repo" "$remote" "README.md" "hello"
    git -C "$repo" switch -c squash-remote >/dev/null
    printf 'topic\n' > "$repo/topic.txt"
    commit_all "$repo" "Topic commit"
    git -C "$repo" push -u origin squash-remote >/dev/null 2>&1
    git -C "$repo" switch master >/dev/null
    git -C "$repo" branch -D squash-remote >/dev/null 2>&1

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "pr list --head squash-remote --state merged --json number --jq length" ]]; then
    printf '1\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
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
            base_gh_subcommand_main branch prune --remote
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Branch prune preview for default branch master."* ]]
    [[ "$output" == *"GitHub branches"* ]]
    [[ "$output" == *"[DRY-RUN] DELETE-REMOTE origin/squash-remote  merged GitHub PR"* ]]
    [[ "$output" == *"Summary: 1 would delete remotely, 0 skipped worktree, 0 skipped unmerged, 0 failed."* ]]
    [[ "$output" == *"Run with --yes to apply these changes."* ]]
    git -C "$repo" ls-remote --exit-code --heads origin squash-remote >/dev/null
}

@test "basectl gh branch prune --remote --yes deletes safe GitHub branches" {
    local repo remote

    repo="$TEST_TMPDIR/repo"
    remote="$TEST_TMPDIR/remote.git"
    create_tracked_repo_with_upstream "$repo" "$remote" "README.md" "hello"
    git -C "$repo" switch -c squash-remote >/dev/null
    printf 'topic\n' > "$repo/topic.txt"
    commit_all "$repo" "Topic commit"
    git -C "$repo" push -u origin squash-remote >/dev/null 2>&1
    git -C "$repo" switch master >/dev/null
    git -C "$repo" branch -D squash-remote >/dev/null 2>&1

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "pr list --head squash-remote --state merged --json number --jq length" ]]; then
    printf '1\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
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
            base_gh_subcommand_main branch prune --remote --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"GitHub branches"* ]]
    [[ "$output" == *"DELETE-REMOTE origin/squash-remote"* ]]
    [[ "$output" == *"Summary: 1 deleted remotely, 0 skipped worktree, 0 skipped unmerged, 0 failed."* ]]
    ! git -C "$repo" ls-remote --exit-code --heads origin squash-remote >/dev/null
}

@test "basectl gh branch prune --remote skips branches attached to worktrees" {
    local repo remote worktree

    repo="$TEST_TMPDIR/repo"
    remote="$TEST_TMPDIR/remote.git"
    worktree="$TEST_TMPDIR/squash-worktree"
    create_tracked_repo_with_upstream "$repo" "$remote" "README.md" "hello"
    git -C "$repo" switch -c squash-work >/dev/null
    printf 'topic\n' > "$repo/topic.txt"
    commit_all "$repo" "Topic commit"
    git -C "$repo" push -u origin squash-work >/dev/null 2>&1
    git -C "$repo" switch master >/dev/null
    git -C "$repo" worktree add "$worktree" squash-work >/dev/null 2>&1

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "pr list --head squash-work --state merged --json number --jq length" ]]; then
    printf '1\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
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
            base_gh_subcommand_main branch prune --remote --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP   squash-work  attached to worktree "*"/squash-worktree"* ]]
    [[ "$output" == *"SKIP   origin/squash-work  attached to worktree "*"/squash-worktree"* ]]
    [[ "$output" == *"Summary: 0 deleted remotely, 1 skipped worktree, 0 skipped unmerged, 0 failed."* ]]
    git -C "$repo" ls-remote --exit-code --heads origin squash-work >/dev/null
}

@test "basectl gh branch prune deletes squash-merged branches confirmed by GitHub" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c squash-work >/dev/null
    printf 'topic\n' > "$repo/topic.txt"
    commit_all "$repo" "Topic commit"
    git -C "$repo" switch master >/dev/null

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "pr list --head squash-work --state merged --json number --jq length" ]]; then
    printf '1\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
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
            base_gh_subcommand_main branch prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"DELETE squash-work"* ]]
    [[ "$output" == *"Summary: 1 deleted, 0 skipped worktree, 0 skipped upstream, 0 failed."* ]]
    ! git -C "$repo" show-ref --verify --quiet refs/heads/squash-work
}

@test "basectl gh worktree prune defaults to dry-run" {
    local repo worktree

    repo="$TEST_TMPDIR/repo"
    worktree="$TEST_TMPDIR/merged-worktree"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" branch merged-work
    git -C "$repo" worktree add "$worktree" merged-work >/dev/null 2>&1

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main worktree prune
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Worktree prune preview for default branch master."* ]]
    [[ "$output" == *"[DRY-RUN] REMOVE "*"/merged-worktree (merged-work) and delete local branch"* ]]
    [[ "$output" == *"SKIP   "*"/repo (master)  current worktree"* ]]
    [[ "$output" == *"Summary: 1 would remove, 1 skipped current/default, 0 skipped dirty, 0 skipped unmerged, 0 failed."* ]]
    [[ "$output" == *"Run with --yes to apply these changes."* ]]
    [ -d "$worktree" ]
    git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
}

@test "basectl gh worktree prune removes safe merged worktrees and branch" {
    local repo worktree

    repo="$TEST_TMPDIR/repo"
    worktree="$TEST_TMPDIR/merged-worktree"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" branch merged-work
    git -C "$repo" worktree add "$worktree" merged-work >/dev/null 2>&1

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main worktree prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"REMOVE "*"/merged-worktree (merged-work)"* ]]
    [[ "$output" == *"DELETE merged-work"* ]]
    [[ "$output" == *"Summary: 1 removed, 1 skipped current/default, 0 skipped dirty, 0 skipped unmerged, 0 failed."* ]]
    [ ! -e "$worktree" ]
    ! git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
}

@test "basectl gh worktree prune skips dirty worktrees" {
    local repo worktree

    repo="$TEST_TMPDIR/repo"
    worktree="$TEST_TMPDIR/dirty-worktree"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" branch dirty-work
    git -C "$repo" worktree add "$worktree" dirty-work >/dev/null 2>&1
    printf 'notes\n' > "$worktree/local-notes.md"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main worktree prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP   "*"/dirty-worktree (dirty-work)  dirty worktree"* ]]
    [[ "$output" == *"Summary: 0 removed, 1 skipped current/default, 1 skipped dirty, 0 skipped unmerged, 0 failed."* ]]
    [ -d "$worktree" ]
    git -C "$repo" show-ref --verify --quiet refs/heads/dirty-work
}

@test "basectl gh worktree prune skips unmerged branches" {
    local repo worktree

    repo="$TEST_TMPDIR/repo"
    worktree="$TEST_TMPDIR/unmerged-worktree"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c unmerged-work >/dev/null
    printf 'topic\n' > "$repo/topic.txt"
    commit_all "$repo" "Topic commit"
    git -C "$repo" switch master >/dev/null
    git -C "$repo" worktree add "$worktree" unmerged-work >/dev/null 2>&1

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main worktree prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP   "*"/unmerged-worktree (unmerged-work)  branch is not confirmed merged into master or a merged GitHub PR"* ]]
    [[ "$output" == *"Summary: 0 removed, 1 skipped current/default, 0 skipped dirty, 1 skipped unmerged, 0 failed."* ]]
    [ -d "$worktree" ]
    git -C "$repo" show-ref --verify --quiet refs/heads/unmerged-work
}

@test "basectl gh worktree prune removes squash-merged worktrees confirmed by GitHub" {
    local repo worktree

    repo="$TEST_TMPDIR/repo"
    worktree="$TEST_TMPDIR/squash-worktree"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c squash-work >/dev/null
    printf 'topic\n' > "$repo/topic.txt"
    commit_all "$repo" "Topic commit"
    git -C "$repo" switch master >/dev/null
    git -C "$repo" worktree add "$worktree" squash-work >/dev/null 2>&1

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "pr list --head squash-work --state merged --json number --jq length" ]]; then
    printf '1\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
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
            base_gh_subcommand_main worktree prune --yes
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"REMOVE "*"/squash-worktree (squash-work)"* ]]
    [[ "$output" == *"DELETE squash-work"* ]]
    [[ "$output" == *"Summary: 1 removed, 1 skipped current/default, 0 skipped dirty, 0 skipped unmerged, 0 failed."* ]]
    [ ! -e "$worktree" ]
    ! git -C "$repo" show-ref --verify --quiet refs/heads/squash-work
}

@test "basectl gh pr create links current branch issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "enhancement/117-20260528-basectl-gh-workflow" >/dev/null

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
body_file=""
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_GH_TEST_STATE_DIR:?}/body"
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

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

@test "basectl gh pr create renders project PR policy body" {
    local repo repo_root

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
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

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1 $2 $3" == "issue view 117" ]]; then
    printf 'needs-demo\n'
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
body_file=""
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_GH_TEST_STATE_DIR:?}/body"
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"
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
            base_gh_subcommand_main pr create
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-linking PR to issue #117 from branch name. Pass --no-fixes to suppress."* ]]
    [[ "$(cat "$TEST_STATE_DIR/gh-args")" == pr\ create\ --fill\ --body-file* ]]
    [[ "$(cat "$TEST_STATE_DIR/wrapper-args")" == *"base_pr_policy body --manifest $repo_root/base_manifest.yaml --issue 117"* ]]
    [[ "$(cat "$TEST_STATE_DIR/wrapper-args")" == *"--label needs-demo"* ]]
    [[ "$(cat "$TEST_STATE_DIR/wrapper-args")" == *"--path docs/workflow.md"* ]]
    [[ "$(cat "$TEST_STATE_DIR/body")" == *"## Demo Impact"* ]]
    [[ "$(cat "$TEST_STATE_DIR/body")" == *"## Docs Impact"* ]]
}

@test "basectl gh pr create supports no-fixes opt out" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "enhancement/117-20260528-basectl-gh-workflow" >/dev/null

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
body_file=""
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_GH_TEST_STATE_DIR:?}/body"
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

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
