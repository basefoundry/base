#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl gh prints help" {
    run_basectl gh --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"basectl gh project doctor --project <title>"* ]]
    [[ "$output" == *"basectl gh project configure --project <title>"* ]]
    [[ "$output" == *"basectl gh project issue set-fields <number>"* ]]
    [[ "$output" == *"basectl gh worktree prune"* ]]
    [[ "$output" == *"<category>/<issue>-<YYYYMMDD>-<slug>"* ]]
    [[ "$output" == *"assigned to codeforester"* ]]
}

@test "basectl gh issue create applies category label and assignee" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
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
}

@test "basectl gh issue list reports missing gh authentication clearly" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    printf 'github.com\n' >&2
    printf '  X failed to reach api.github.com\n' >&2
    printf '  - check your internet connection or GitHub API access\n' >&2
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
    [[ "$output" == *"GitHub CLI authentication or GitHub API access is not ready."* ]]
    [[ "$output" == *"gh auth status: github.com"* ]]
    [[ "$output" == *"gh auth status:   X failed to reach api.github.com"* ]]
    [[ "$output" == *"gh auth status:   - check your internet connection or GitHub API access"* ]]
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
    [[ "$output" == *"[DRY-RUN] Branch prune preview for default branch master."* ]]
    [[ "$output" == *"Local branches"* ]]
    [[ "$output" == *"[DRY-RUN] DELETE merged-work"* ]]
    [[ "$output" == *"Summary: 1 would delete, 0 skipped worktree, 0 skipped upstream, 0 failed."* ]]
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
    [[ "$output" == *"SKIP   GitHub branch cleanup requires authenticated gh."* ]]
    [[ "$output" == *"Remote tracking refs"* ]]
    [[ "$output" == *"PRUNE origin/stale-branch"* ]]
    [[ "$output" == *"Note: remote-tracking ref cleanup prunes stale local origin/* refs after GitHub branch cleanup."* ]]
    [[ "$output" != *"Pruning origin"* ]]
    [[ "$output" != *"URL:"* ]]
    ! git -C "$repo" show-ref --verify --quiet refs/remotes/origin/stale-branch
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
