# Common helpers for Bash library BATS suites.

# Preserve BATS' built-in `run` helper before lib_std.sh defines its own.
if declare -f run >/dev/null 2>&1; then
    eval "$(declare -f run | sed '1 s/^run /bats_run /')"
fi

readonly BASE_BASH_TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly BASE_BASH_DIR="$(cd "$BASE_BASH_TESTS_DIR/.." && pwd -P)"
readonly BASE_REPO_ROOT="$(cd "$BASE_BASH_DIR/../.." && pwd -P)"
readonly BASE_TEST_ORIG_PATH="$PATH"

setup_test_tmpdir() {
    TEST_TMPDIR="${BATS_TEST_TMPDIR}/workspace"
    mkdir -p "$TEST_TMPDIR"
}

init_git_repo() {
    local repo_dir="$1"

    mkdir -p "$repo_dir"
    git init "$repo_dir" >/dev/null 2>&1
    git -C "$repo_dir" checkout -B master >/dev/null 2>&1
    git -C "$repo_dir" config user.name "Bats Test"
    git -C "$repo_dir" config user.email "bats@example.com"
}

commit_all() {
    local repo_dir="$1"
    local message="${2:-test commit}"

    git -C "$repo_dir" add -A
    git -C "$repo_dir" commit -m "$message" >/dev/null 2>&1
}

create_tracked_repo_with_upstream() {
    local repo_dir="$1"
    local remote_dir="$2"
    local rel_path="$3"
    local content="${4:-sample content}"

    init_git_repo "$repo_dir"
    mkdir -p "$(dirname "$repo_dir/$rel_path")"
    printf '%s\n' "$content" > "$repo_dir/$rel_path"
    commit_all "$repo_dir" "Initial commit"

    git init --bare "$remote_dir" >/dev/null 2>&1
    git -C "$repo_dir" remote add origin "$remote_dir"
    git -C "$repo_dir" push -u origin master >/dev/null 2>&1
}
