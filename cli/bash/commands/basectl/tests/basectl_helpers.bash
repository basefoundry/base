# Shared helpers for basectl command BATS suites.

load ../../../../../tests/test_helper.sh
load ./bash_lib_readiness_helpers.bash
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    TEST_BASH_BIN_DIR="$(dirname "$(command -v bash)")"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
    unset BASE_GH_PROJECT_WRAPPER
    export BASH_ENV="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash"
}

run_basectl() {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" "$@"
}

base_cli_test_pythonpath() {
    local base_cli_path

    # Use the same provider resolver as Base commands so these tests remain
    # valid with either an installed package or a source checkout.
    # shellcheck source=lib/base/base_cli_runtime.sh
    source "$BASE_REPO_ROOT/lib/base/base_cli_runtime.sh"
    base_cli_path="$(BASE_HOME="$BASE_REPO_ROOT" base_cli_runtime_source_root)" || return 1
    if [[ -n "$base_cli_path" ]]; then
        printf '%s:%s\n' "$base_cli_path" "$BASE_REPO_ROOT/cli/python"
    else
        printf '%s\n' "$BASE_REPO_ROOT/cli/python"
    fi
}
