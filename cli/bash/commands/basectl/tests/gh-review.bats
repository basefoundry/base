#!/usr/bin/env bats

load ./basectl_helpers.bash

create_review_repo() {
    local repo="$TEST_TMPDIR/review-repo"
    local remote="$TEST_TMPDIR/review-remote.git"

    init_git_repo "$repo"
    printf 'base\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git init --bare "$remote" >/dev/null 2>&1
    git -C "$repo" remote add origin "$remote"
    git -C "$repo" push -u origin master >/dev/null 2>&1

    git -C "$repo" switch -c review-source >/dev/null 2>&1
    printf 'review\n' >> "$repo/README.md"
    commit_all "$repo" "Review commit"
    BASE_REVIEW_TEST_HEAD_SHA="$(git -C "$repo" rev-parse HEAD)"
    export BASE_REVIEW_TEST_HEAD_SHA
    git -C "$repo" push origin HEAD:refs/pull/2621/head >/dev/null 2>&1
    git -C "$repo" switch master >/dev/null 2>&1
    BASE_REVIEW_TEST_REPO="$repo"
    export BASE_REVIEW_TEST_REPO
}

write_review_gh_mock() {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == api && "$2" == repos/basefoundry/base/pulls/2621 ]]; then
    state="${BASE_REVIEW_TEST_STATE:-open}"
    case "$state" in
        fail)
            printf 'gh: Not Found (HTTP 404)\n' >&2
            exit 1
            ;;
        merged)
            printf '{"base":{"repo":{"full_name":"basefoundry/base"}},"head":{"sha":"%s"},"state":"closed","merged_at":"2026-10-20T00:00:00Z"}\n' "$BASE_REVIEW_TEST_HEAD_SHA"
            ;;
        closed_unmerged)
            printf '{"base":{"repo":{"full_name":"basefoundry/base"}},"head":{"sha":"%s"},"state":"closed","merged_at":null}\n' "$BASE_REVIEW_TEST_HEAD_SHA"
            ;;
        mismatch)
            printf '{"base":{"repo":{"full_name":"basefoundry/base"}},"head":{"sha":"0000000000000000000000000000000000000001"},"state":"open","merged_at":null}\n'
            ;;
        *)
            printf '{"base":{"repo":{"full_name":"basefoundry/base"}},"head":{"sha":"%s"},"state":"open","merged_at":null}\n' "$BASE_REVIEW_TEST_HEAD_SHA"
            ;;
    esac
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"
}

run_review() {
    local repo="$1"
    shift
    local bash_libs_dir

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        BASE_REVIEW_TEST_HEAD_SHA="$BASE_REVIEW_TEST_HEAD_SHA" \
        BASE_REVIEW_TEST_STATE="${BASE_REVIEW_TEST_STATE:-open}" \
        BASE_GH_TEST_CWD="$repo" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$BASE_GH_TEST_CWD"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_infer_github_repo() { printf "basefoundry/base\\n"; }
            base_gh_subcommand_main review "$@"
        ' bash "$@"
}

review_metadata_path() {
    local repo="$1"
    local common_dir

    common_dir="$(git -C "$repo" rev-parse --git-common-dir)"
    if [[ "$common_dir" != /* ]]; then
        common_dir="$repo/$common_dir"
    fi
    printf '%s/base-review/worktrees/pr-2621-stale-worktree.json\n' "$common_dir"
}

@test "review fetch creates a detached namespaced worktree without a pr branch" {
    local repo review_root worktree metadata

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    mkdir -p "$TEST_TMPDIR/review-worktrees"
    review_root="$(cd "$TEST_TMPDIR/review-worktrees" && pwd -P)"
    write_review_gh_mock

    run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root"

    [ "$status" -eq 0 ]
    [[ "$output" == *"CREATED $review_root/pr-2621-stale-worktree"* ]]
    [[ "$output" == *"Ref:   refs/base-review/pr/2621/stale-worktree"* ]]
    worktree="$review_root/pr-2621-stale-worktree"
    metadata="$(review_metadata_path "$repo")"
    [ -d "$worktree" ]
    ! git -C "$worktree" symbolic-ref --quiet HEAD
    git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2621/stale-worktree
    ! git -C "$repo" show-ref --verify --quiet refs/heads/pr-2621-stale-worktree
    jq -e '.pull_request == 2621 and .slug == "stale-worktree" and .head_sha == env.BASE_REVIEW_TEST_HEAD_SHA' "$metadata" >/dev/null
}

@test "review fetch rejects a nested worktree root before GitHub or Git mutation" {
    local repo nested_root

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    nested_root="$repo/review-worktrees"

    run_review "$repo" fetch 2621 --name nested-root --root "$nested_root"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Refusing review worktree root"* ]]
    [[ "$output" == *"inside repository root"* ]]
    [ ! -e "$nested_root" ]
    ! git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2621/nested-root
}

@test "review fetch rejects a symlinked nested worktree root" {
    local repo nested_link

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    nested_link="$TEST_TMPDIR/review-worktrees-link"
    ln -s "$repo" "$nested_link"

    run_review "$repo" fetch 2621 --name symlinked-root --root "$nested_link/children"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Refusing review worktree root"* ]]
    [[ "$output" == *"inside repository root"* ]]
    ! git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2621/symlinked-root
}

@test "review prune removes only a verified merged review checkout" {
    local repo review_root worktree metadata

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    mkdir -p "$TEST_TMPDIR/review-worktrees"
    review_root="$(cd "$TEST_TMPDIR/review-worktrees" && pwd -P)"
    write_review_gh_mock
    run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root"
    [ "$status" -eq 0 ]
    worktree="$review_root/pr-2621-stale-worktree"
    metadata="$(review_metadata_path "$repo")"

    BASE_REVIEW_TEST_STATE=merged run_review "$repo" prune --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] REMOVE $worktree"* ]]
    [ -d "$worktree" ]

    BASE_REVIEW_TEST_STATE=merged run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"REMOVE $worktree"* ]]
    [ ! -e "$worktree" ]
    ! git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2621/stale-worktree
    [ ! -e "$metadata" ]

    BASE_REVIEW_TEST_STATE=merged run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Summary: 0 removed"* ]]
}

@test "review prune retains dirty, open, and closed-unmerged checkouts unless explicitly selected" {
    local repo review_root worktree

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    mkdir -p "$TEST_TMPDIR/review-worktrees"
    review_root="$(cd "$TEST_TMPDIR/review-worktrees" && pwd -P)"
    write_review_gh_mock
    run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root"
    [ "$status" -eq 0 ]
    worktree="$review_root/pr-2621-stale-worktree"

    printf 'local changes\n' > "$worktree/local.txt"
    BASE_REVIEW_TEST_STATE=open run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"dirty worktree; retained"* ]]
    [ -d "$worktree" ]

    rm "$worktree/local.txt"
    BASE_REVIEW_TEST_STATE=closed_unmerged run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"closed unmerged PR; retained"* ]]
    [ -d "$worktree" ]

    BASE_REVIEW_TEST_STATE=closed_unmerged run_review "$repo" prune --closed-unmerged --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [ ! -e "$worktree" ]
}

@test "review prune retains stale heads and orphaned metadata or refs" {
    local repo review_root worktree metadata

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    mkdir -p "$TEST_TMPDIR/review-worktrees"
    review_root="$(cd "$TEST_TMPDIR/review-worktrees" && pwd -P)"
    write_review_gh_mock
    run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root"
    [ "$status" -eq 0 ]
    worktree="$review_root/pr-2621-stale-worktree"
    metadata="$(review_metadata_path "$repo")"

    git -C "$worktree" reset --hard HEAD^ >/dev/null 2>&1
    BASE_REVIEW_TEST_STATE=merged run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"review head/ref is stale or mismatched; retained"* ]]
    [ -d "$worktree" ]
    [ -e "$metadata" ]

    rm -rf "$worktree"
    BASE_REVIEW_TEST_STATE=merged run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"worktree missing; metadata and ref retained"* ]]
    [ -e "$metadata" ]

    git -C "$repo" update-ref refs/base-review/pr/2622/orphan "$BASE_REVIEW_TEST_HEAD_SHA"
    BASE_REVIEW_TEST_STATE=merged run_review "$repo" prune --yes --root "$review_root"
    [ "$status" -eq 0 ]
    [[ "$output" == *"refs/base-review/pr/2622/orphan  no review metadata; retained"* ]]
    git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2622/orphan
}

@test "review refresh does not discard an existing checkout when GitHub lookup fails" {
    local repo review_root worktree

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    mkdir -p "$TEST_TMPDIR/review-worktrees"
    review_root="$(cd "$TEST_TMPDIR/review-worktrees" && pwd -P)"
    write_review_gh_mock
    run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root"
    [ "$status" -eq 0 ]
    worktree="$review_root/pr-2621-stale-worktree"

    BASE_REVIEW_TEST_STATE=fail run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root" --refresh
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unable to read pull request #2621"* ]]
    [ -d "$worktree" ]
    ! git -C "$worktree" symbolic-ref --quiet HEAD
    git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2621/stale-worktree
}

@test "review fetch removes the fetched ref when the API head SHA is stale" {
    local repo review_root

    create_review_repo
    repo="$BASE_REVIEW_TEST_REPO"
    mkdir -p "$TEST_TMPDIR/review-worktrees"
    review_root="$(cd "$TEST_TMPDIR/review-worktrees" && pwd -P)"
    write_review_gh_mock

    BASE_REVIEW_TEST_STATE=mismatch run_review "$repo" fetch 2621 --name stale-worktree --repo basefoundry/base --root "$review_root"
    [ "$status" -eq 1 ]
    [[ "$output" == *"did not match the GitHub head SHA"* ]]
    [ ! -e "$review_root/pr-2621-stale-worktree" ]
    ! git -C "$repo" show-ref --verify --quiet refs/base-review/pr/2621/stale-worktree
}

@test "review fetch validates names and exposes command-scoped help" {
    run_basectl gh review fetch --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl gh review fetch <number> --name <slug> [options]"* ]]

    run_basectl gh review fetch 2621 --name Bad_Name
    [ "$status" -eq 2 ]
    [[ "$output" == *"Review name must be lower-case kebab-case."* ]]

    run_basectl gh review fetch 2621 --name ../escape
    [ "$status" -eq 2 ]
    [[ "$output" == *"Review name must be lower-case kebab-case."* ]]
}

@test "review prune rejects conflicting execution flags" {
    run_basectl gh review prune --dry-run --yes

    [ "$status" -eq 2 ]
    [[ "$output" == *"Options '--dry-run' and '--yes' cannot be used together"* ]]
}
