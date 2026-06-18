# Shared helpers for basectl command BATS suites.

load ../../../../../lib/bash/tests/test_helper.sh
load ./bash_lib_readiness_helpers.bash
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
}

run_basectl() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" "$@"
}
