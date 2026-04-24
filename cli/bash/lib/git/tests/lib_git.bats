#!/usr/bin/env bats

load ../../../tests/test_helper.bash

setup() {
    setup_test_tmpdir
    source "$BANYAN_BASH_DIR/lib/std/lib_std.sh"
    source "$BANYAN_BASH_DIR/lib/git/lib_git.sh"
}

@test "git_get_current_branch returns the current branch name" {
    local repo="$TEST_TMPDIR/repo"
    local branch=""

    init_git_repo "$repo"
    git_get_current_branch "$repo" branch

    [ "$branch" = "master" ]
}

@test "git_get_current_branch reports detached head" {
    local repo="$TEST_TMPDIR/repo"
    local branch=""

    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" checkout --detach >/dev/null 2>&1

    git_get_current_branch "$repo" branch

    [ "$branch" = "detached head" ]
}

@test "git_update_repo skips dirty repositories when no dirty path is allowed" {
    local repo="$TEST_TMPDIR/repo"

    init_git_repo "$repo"
    printf 'base\n' > "$repo/data.txt"
    commit_all "$repo" "Initial commit"
    printf 'local change\n' > "$repo/data.txt"
    set_log_level DEBUG

    bats_run git_update_repo "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"has local changes; skipping auto-update"* ]]
}

@test "check_script_up_to_date reports success for an up-to-date tracked script" {
    local repo="$TEST_TMPDIR/repo"
    local remote="$TEST_TMPDIR/remote.git"
    local script_path="$repo/scripts/tool.sh"

    create_tracked_repo_with_upstream "$repo" "$remote" "scripts/tool.sh" "#!/usr/bin/env bash"

    bats_run check_script_up_to_date "$script_path"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository is up to date with origin/master."* ]]
}

@test "check_script_up_to_date returns 3 for a dirty tracked script" {
    local repo="$TEST_TMPDIR/repo"
    local remote="$TEST_TMPDIR/remote.git"
    local script_path="$repo/scripts/tool.sh"

    create_tracked_repo_with_upstream "$repo" "$remote" "scripts/tool.sh" "#!/usr/bin/env bash"
    printf 'echo dirty\n' >> "$script_path"

    bats_run check_script_up_to_date "$script_path"

    [ "$status" -eq 3 ]
    [[ "$output" == *"has local modifications"* ]]
}
