#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl gh prints help" {
    run_basectl gh --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"<category>/<issue>-<YYYYMMDD>-<slug>"* ]]
    [[ "$output" == *"assigned to codeforester"* ]]
}

@test "basectl gh issue create applies category label and assignee" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status" ]]; then
    exit 0
fi
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
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
            base_gh_subcommand_main issue create --category bug --title "Repair branch pruning"
        '

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Repair branch pruning --label bug --assignee codeforester" ]
}

@test "basectl gh issue list reports missing gh authentication clearly" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status" ]]; then
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
    [[ "$output" == *"GitHub CLI authentication is not ready."* ]]
    [[ "$output" == *"gh auth login -h github.com"* ]]
    [[ "$output" != *"unexpected gh args"* ]]
}

@test "basectl gh issue start creates convention branch from issue metadata" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status" ]]; then
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
    [[ "$output" == "enhancement/117-"*"-add-basectl-gh-workflow-for-issues" ]]
    [ "$(git -C "$repo" branch --show-current)" = "$output" ]
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
    [[ "$output" == "enhancement/117-"*"-prune-merged-branches" ]]
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
    [[ "$output" == *"[DRY-RUN] Local branches merged into"* ]]
    [[ "$output" == *"merged-work"* ]]
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
    [[ "$output" == *"Deleted branch merged-work"* ]]
    ! git -C "$repo" show-ref --verify --quiet refs/heads/merged-work
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
if [[ "$*" == "auth status" ]]; then
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
    [[ "$(cat "$TEST_STATE_DIR/gh-args")" == pr\ create\ --fill\ --body-file* ]]
    [ "$(cat "$TEST_STATE_DIR/body")" = "Fixes #117" ]
}

@test "basectl gh todo import dry-run classifies TODO items" {
    local todo_file

    todo_file="$TEST_TMPDIR/TODO.md"
    cat > "$todo_file" <<'EOF'
## P0 — Security And Correctness

- [ ] Detect outdated Xcode Command Line Tools in `basectl doctor`.

## P1 — Product Core And Composability

- [ ] Add first-class `mise` integration.
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main todo import --dry-run --file "$1"
        ' bash "$todo_file"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'bug\tDetect outdated Xcode Command Line Tools in `basectl doctor`'* ]]
    [[ "$output" == *$'enhancement\tAdd first-class `mise` integration'* ]]
}
