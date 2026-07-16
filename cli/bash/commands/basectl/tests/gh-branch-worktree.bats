#!/usr/bin/env bats

load ./basectl_helpers.bash

@test "basectl gh branch and worktree primitives delegate to reusable gh helpers" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            git_worktree_path_for_branch() {
                printf "%s\n" "/tmp/shared-worktree"
            }
            git_branch_upstream() {
                printf "%s\n" "origin/feature"
            }
            git_branch_merged_to_ref() {
                [[ "$2" == "feature" && "$3" == "main" ]]
            }
            git_list_remote_branches() {
                printf "%s\n" "main" "feature"
            }
            git_list_worktree_branches() {
                printf "%s\t%s\n" "/tmp/shared-worktree" "feature"
            }
            remote_branches="$(base_gh_list_remote_branches)"
            printf "worktree=%s\n" "$(base_gh_worktree_path_for_branch feature)"
            printf "upstream=%s\n" "$(base_gh_branch_upstream feature)"
            base_gh_branch_merged_to_ref feature main
            printf "merged=$?\n"
            printf "remote=%s\n" "${remote_branches//$'\''\n'\''/,}"
            printf "worktrees=%s\n" "$(base_gh_list_worktree_branches)"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"worktree=/tmp/shared-worktree"* ]]
    [[ "$output" == *"upstream=origin/feature"* ]]
    [[ "$output" == *"merged=0"* ]]
    [[ "$output" == *"remote=main,feature"* ]]
    [[ "$output" == *$'worktrees=/tmp/shared-worktree\tfeature'* ]]
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

@test "basectl gh branch usage errors return status 2" {
    run_basectl gh branch stale --days never

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: --days must be a positive integer."* ]]
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
