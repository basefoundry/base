# shellcheck shell=bash
# Common helpers for Base BATS suites.

# Preserve BATS' built-in `run` helper before lib_std.sh defines its own.
if declare -f run >/dev/null 2>&1; then
    eval "$(declare -f run | sed '1 s/^run /bats_run /')"
fi

readonly BASE_TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly BASE_REPO_ROOT="$(cd "$BASE_TESTS_DIR/.." && pwd -P)"
readonly BASE_BASH_DIR="$BASE_REPO_ROOT/lib/bash"
readonly BASE_CLI_BASH_DIR="$BASE_REPO_ROOT/cli/bash"
readonly BASE_TEST_ORIG_PATH="$PATH"

unset_base_runtime_env() {
    local var_name

    for var_name in \
        BASE_HOME \
        BASE_BIN_DIR \
        BASE_CLI_DIR \
        BASE_BASH_DIR \
        BASE_BASH_COMMANDS_DIR \
        BASE_LIB_DIR \
        BASE_BASH_LIB_DIR \
        BASE_BASH_LIBS_SOURCE \
        BASE_SHELL_DIR \
        BASE_OS \
        BASE_PLATFORM \
        BASE_HOST \
        BASE_SHELL \
        BASE_PLATFORM_TOOLS_HOME \
        BASE_PLATFORM_TOOLS_BIN_DIR \
        BASE_PROFILE_VERSION \
        BASE_ENABLE_BASH_DEFAULTS \
        BASE_ENABLE_ZSH_DEFAULTS \
        BASE_DEBUG \
        BASE_BASH_COMMAND_NAME \
        BASE_BASH_COMMAND_DIR \
        BASE_BASH_COMMAND_SCRIPT \
        BASE_BASH_BOOTSTRAP_SOURCE \
        BASE_INIT_TEST_OS_RELEASE_PATH \
        BASE_ACTIVATE_PRESERVE_CWD \
        BASE_ACTIVATE_SHELL \
        BASE_PROJECT \
        BASE_PROJECT_ROOT \
        BASE_PROJECT_MANIFEST \
        BASE_PROJECT_VENV_DIR \
        VIRTUAL_ENV; do
        unset "$var_name" 2>/dev/null || true
    done
}

setup_test_tmpdir() {
    unset_base_runtime_env
    TEST_TMPDIR="${BATS_TEST_TMPDIR}/workspace"
    mkdir -p "$TEST_TMPDIR"
}

base_bash_libs_fixture_dir() {
    local candidate

    for candidate in \
        "${BASE_BASH_LIBS_FIXTURE_DIR:-}" \
        "${BASE_BASH_LIBS_DIR:-}" \
        "$BASE_REPO_ROOT/../base-bash-libs/lib/bash"; do
        [[ -n "$candidate" ]] || continue
        if [[ -f "$candidate/std/lib_std.sh" ]]; then
            (cd "$candidate" && pwd -P)
            return $?
        fi
    done

    printf 'ERROR: Base Bash library fixtures were not found. Clone basefoundry/base-bash-libs next to Base or set BASE_BASH_LIBS_DIR.\n' >&2
    return 1
}

copy_base_bash_libs_fixture() {
    local target_dir="$1"
    local source_dir
    local source_root
    local target_root

    source_dir="$(base_bash_libs_fixture_dir)" || return 1
    mkdir -p "$target_dir"
    cp -R "$source_dir/." "$target_dir/"

    source_root="$(cd "$source_dir/../.." && pwd -P)" || return 1
    target_root="$(cd "$target_dir/../.." && pwd -P)" || return 1
    cp "$source_root/VERSION" "$target_root/VERSION"
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
