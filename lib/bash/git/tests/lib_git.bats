#!/usr/bin/env bats

load ../../tests/test_helper.sh

setup() {
    setup_test_tmpdir
    source "$BASE_BASH_DIR/std/lib_std.sh"
    source "$BASE_BASH_DIR/git/lib_git.sh"
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

@test "git_update_repo accepts main as the detected update branch" {
    local repo="$TEST_TMPDIR/repo"

    init_git_repo "$repo"
    git -C "$repo" checkout -B main >/dev/null 2>&1
    printf 'base\n' > "$repo/data.txt"
    commit_all "$repo" "Initial commit"
    printf 'local change\n' > "$repo/data.txt"
    set_log_level DEBUG

    bats_run git_update_repo "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == *"has local changes; skipping auto-update"* ]]
    [[ "$output" != *"not 'master'"* ]]
}

@test "_git_expected_update_branch returns main when origin has main" {
    local repo="$TEST_TMPDIR/repo"
    local branch

    init_git_repo "$repo"
    printf 'base\n' > "$repo/data.txt"
    commit_all "$repo" "Initial commit"
    git -C "$repo" update-ref refs/remotes/origin/main HEAD
    git -C "$repo" checkout --detach >/dev/null 2>&1
    git -C "$repo" branch -D master >/dev/null 2>&1

    pushd "$repo" >/dev/null
    branch="$(_git_expected_update_branch)"
    popd >/dev/null

    [ "$branch" = "main" ]
}

@test "_git_expected_update_branch returns master when origin only has master" {
    local repo="$TEST_TMPDIR/repo"
    local branch

    init_git_repo "$repo"
    printf 'base\n' > "$repo/data.txt"
    commit_all "$repo" "Initial commit"
    git -C "$repo" update-ref refs/remotes/origin/master HEAD
    git -C "$repo" checkout --detach >/dev/null 2>&1
    git -C "$repo" branch -D master >/dev/null 2>&1

    pushd "$repo" >/dev/null
    branch="$(_git_expected_update_branch)"
    popd >/dev/null

    [ "$branch" = "master" ]
}

@test "_git_expected_update_branch falls back to master without main or master refs" {
    local repo="$TEST_TMPDIR/repo"
    local branch

    init_git_repo "$repo"

    pushd "$repo" >/dev/null
    branch="$(_git_expected_update_branch)"
    popd >/dev/null

    [ "$branch" = "master" ]
}

@test "_git_only_path_dirty accepts multiple dirty files under an allowed directory" {
    local repo="$TEST_TMPDIR/repo"
    local rc

    init_git_repo "$repo"
    mkdir -p "$repo/shared"
    printf 'one\n' > "$repo/shared/one.txt"
    printf 'two\n' > "$repo/shared/two.txt"
    commit_all "$repo" "Initial commit"
    printf 'local one\n' > "$repo/shared/one.txt"
    printf 'local two\n' > "$repo/shared/two.txt"

    pushd "$repo" >/dev/null
    _git_only_path_dirty "shared"
    rc=$?
    popd >/dev/null

    [ "$rc" -eq 0 ]
}

@test "_git_only_path_dirty does not treat sibling path prefixes as allowed" {
    local repo="$TEST_TMPDIR/repo"
    local rc

    init_git_repo "$repo"
    mkdir -p "$repo/shared"
    printf 'one\n' > "$repo/shared/one.txt"
    printf 'other\n' > "$repo/shared-other.txt"
    commit_all "$repo" "Initial commit"
    printf 'local one\n' > "$repo/shared/one.txt"
    printf 'local other\n' > "$repo/shared-other.txt"

    pushd "$repo" >/dev/null
    set +e
    _git_only_path_dirty "shared"
    rc=$?
    set -e
    popd >/dev/null

    [ "$rc" -eq 1 ]
}

@test "git_update_repo cleans up temp log without changing RETURN trap" {
    local repo="$TEST_TMPDIR/repo"
    local temp_dir="$TEST_TMPDIR/git-temp"
    local return_trap

    mkdir -p "$temp_dir"
    init_git_repo "$repo"
    printf 'base\n' > "$repo/data.txt"
    commit_all "$repo" "Initial commit"
    printf 'local change\n' > "$repo/data.txt"

    trap 'printf "outer return trap\n"' RETURN
    TMPDIR="$temp_dir" bats_run git_update_repo "$repo"
    return_trap="$(trap -p RETURN)"
    trap - RETURN

    [ "$status" -eq 0 ]
    [[ "$return_trap" == *"outer return trap"* ]]
    ! compgen -G "$temp_dir/git_log.*" >/dev/null
}

@test "_git_update_repo_finish removes temp log after success" {
    local git_log="$TEST_TMPDIR/git.log"

    printf 'pull output\n' > "$git_log"

    bats_run _git_update_repo_finish "$git_log" false 0

    [ "$status" -eq 0 ]
    [ ! -e "$git_log" ]
}

@test "_git_update_repo_finish preserves an existing RETURN trap" {
    local git_log="$TEST_TMPDIR/git.log"
    local return_trap

    printf 'pull output\n' > "$git_log"
    trap 'printf "outer return trap\n"' RETURN

    bats_run _git_update_repo_finish "$git_log" false 0
    return_trap="$(trap -p RETURN)"
    trap - RETURN

    [ "$status" -eq 0 ]
    [[ "$return_trap" == *"outer return trap"* ]]
    [ ! -e "$git_log" ]
}

@test "_git_pull_with_retry retries once after a transient pull failure" {
    local git_log="$TEST_TMPDIR/git.log"
    local pull_count="$TEST_TMPDIR/pull-count"

    printf '0\n' > "$pull_count"
    git() {
        local count

        if [[ "${1:-}" == "pull" ]]; then
            count="$(cat "$pull_count")"
            count=$((count + 1))
            printf '%s\n' "$count" > "$pull_count"
            printf 'pull attempt %s\n' "$count" >&2
            [[ "$count" -ge 2 ]]
            return $?
        fi
        command git "$@"
    }

    bats_run _git_pull_with_retry "$git_log"
    unset -f git

    [ "$status" -eq 0 ]
    [ "$(cat "$pull_count")" = "2" ]
    [[ "$output" == *"git pull failed on attempt 1; retrying once."* ]]
    [ "$(cat "$git_log")" = "pull attempt 2" ]
}

@test "_git_pull_with_retry fails after two pull attempts" {
    local git_log="$TEST_TMPDIR/git.log"
    local pull_count="$TEST_TMPDIR/pull-count"

    printf '0\n' > "$pull_count"
    git() {
        local count

        if [[ "${1:-}" == "pull" ]]; then
            count="$(cat "$pull_count")"
            count=$((count + 1))
            printf '%s\n' "$count" > "$pull_count"
            printf 'pull attempt %s\n' "$count" >&2
            return 1
        fi
        command git "$@"
    }

    bats_run _git_pull_with_retry "$git_log"
    unset -f git

    [ "$status" -eq 1 ]
    [ "$(cat "$pull_count")" = "2" ]
    [[ "$output" == *"git pull failed on attempt 1; retrying once."* ]]
    [ "$(cat "$git_log")" = "pull attempt 2" ]
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
