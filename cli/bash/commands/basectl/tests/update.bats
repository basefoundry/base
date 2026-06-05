#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl update prints help" {
    run_basectl update --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl update [options]"* ]]
    [[ "$output" == *"Update the Base repository from Git"* ]]
    [[ "$output" == *"Tracked Base files must be clean"* ]]
}

@test "basectl update dry-run reports planned update and setup" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" master; }
            base_update_default_branch() { printf "%s\n" master; }
            base_update_worktree_clean() { return 0; }
            base_update_has_untracked_files() { return 1; }
            base_update_subcommand_main --dry-run
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would update Base repository at '$BASE_REPO_ROOT'."* ]]
    [[ "$output" == *"[DRY-RUN] Would run 'basectl setup' after updating."* ]]
}

@test "basectl update refuses dirty worktrees before pulling" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" master; }
            base_update_default_branch() { printf "%s\n" master; }
            base_update_worktree_clean() { return 1; }
            base_update_source_git_library() { printf "git library should not load\n"; return 99; }
            git_update_repo() { printf "git update should not run\n"; return 99; }
            base_update_run_setup() { printf "setup should not run\n"; return 99; }
            base_update_subcommand_main
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base repository has tracked local changes."* ]]
    [[ "$output" != *"git library should not load"* ]]
    [[ "$output" != *"git update should not run"* ]]
    [[ "$output" != *"setup should not run"* ]]
}

@test "basectl update allows untracked files before pulling" {
    local repo="$TEST_TMPDIR/repo"

    init_git_repo "$repo"
    repo="$(cd "$repo" && pwd -P)"
    printf 'base\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    cp "$BASE_REPO_ROOT/base_init.sh" "$repo/base_init.sh"
    cp -R "$BASE_REPO_ROOT/cli" "$repo/cli"
    cp -R "$BASE_REPO_ROOT/lib" "$repo/lib"
    mkdir -p "$repo/bin"
    printf 'notes\n' > "$repo/local-notes.md"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$repo" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() { printf "%s\n" abc1234; }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base repository has untracked files. Continuing because tracked files are clean."* ]]
    [[ "$output" == *"git update repo=$repo branch=master"* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Base update is complete."* ]]
}

@test "basectl update refuses non-default branches" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" feature/example; }
            base_update_default_branch() { printf "%s\n" main; }
            base_update_worktree_clean() { printf "clean should not run\n"; return 99; }
            base_update_run_setup() { printf "setup should not run\n"; return 99; }
            base_update_subcommand_main
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base update only runs on default branch 'main'; current branch is 'feature/example'."* ]]
    [[ "$output" != *"clean should not run"* ]]
    [[ "$output" != *"setup should not run"* ]]
}

@test "basectl update reports already up-to-date repositories" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" master; }
            base_update_default_branch() { printf "%s\n" master; }
            base_update_worktree_clean() { return 0; }
            base_update_has_untracked_files() { return 1; }
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() { printf "%s\n" abc1234; }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating Base repository at '$BASE_REPO_ROOT'."* ]]
    [[ "$output" == *"Base repository is already up to date on 'master' at 'abc1234'."* ]]
    [[ "$output" == *"Running basectl setup after update."* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Base update is complete."* ]]
}

@test "basectl update reports changed revisions" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_AFTER_UPDATE="$TEST_TMPDIR/after-update" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" main; }
            base_update_default_branch() { printf "%s\n" main; }
            base_update_worktree_clean() { return 0; }
            base_update_has_untracked_files() { return 1; }
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() {
                if [[ -f "$BASE_TEST_AFTER_UPDATE" ]]; then
                    printf "%s\n" new5678
                else
                    touch "$BASE_TEST_AFTER_UPDATE"
                    printf "%s\n" old1234
                fi
            }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"git update repo=$BASE_REPO_ROOT branch=main"* ]]
    [[ "$output" == *"Base repository updated from 'old1234' to 'new5678' on 'main'."* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Base update is complete."* ]]
}
