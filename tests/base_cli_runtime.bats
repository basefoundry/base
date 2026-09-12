#!/usr/bin/env bats

load ./test_helper.sh

setup() {
    setup_test_tmpdir
    TEST_RUNTIME_HOME="$TEST_TMPDIR/base"
    mkdir -p "$TEST_RUNTIME_HOME/lib/base"
    cp "$BASE_REPO_ROOT/lib/base/base_cli_runtime.sh" "$TEST_RUNTIME_HOME/lib/base/"
}

@test "base_cli runtime prefers a sibling base-cli checkout" {
    mkdir -p "$TEST_TMPDIR/base-cli/lib/python/base_cli"
    touch "$TEST_TMPDIR/base-cli/lib/python/base_cli/__init__.py"

    run env \
        -u BASE_CLI_SOURCE_DIR \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            printf "%s %s\n" "$(base_cli_runtime_source_kind)" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "sibling $TEST_RUNTIME_HOME/../base-cli/lib/python" ]
}

@test "base_cli runtime accepts an explicit Base root when BASE_HOME is unset" {
    mkdir -p "$TEST_TMPDIR/base-cli/lib/python/base_cli"
    touch "$TEST_TMPDIR/base-cli/lib/python/base_cli/__init__.py"

    run env \
        -u BASE_CLI_SOURCE_DIR \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        bash -c '
            base_home="$BASE_HOME"
            source "$base_home/lib/base/base_cli_runtime.sh"
            unset BASE_HOME
            base_cli_runtime_prepare "$base_home"
            printf "%s %s\n" "${BASE_CLI_SOURCE}" "$(base_cli_runtime_source_root "$base_home")"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "sibling $TEST_RUNTIME_HOME/../base-cli/lib/python" ]
}

@test "base_cli runtime uses an explicit source directory before sibling checkout" {
    mkdir -p "$TEST_TMPDIR/base-cli/lib/python/base_cli" "$TEST_TMPDIR/explicit/base_cli"
    touch "$TEST_TMPDIR/base-cli/lib/python/base_cli/__init__.py" "$TEST_TMPDIR/explicit/base_cli/__init__.py"

    run env \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/explicit" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            printf "%s %s\n" "$(base_cli_runtime_source_kind)" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "explicit $TEST_TMPDIR/explicit" ]
}

@test "base_cli runtime reports pip when no source checkout exists" {
    run env \
        -u BASE_CLI_SOURCE_DIR \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            base_cli_runtime_prepare
            printf "%s %s\n" "${BASE_CLI_SOURCE}" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "pip " ]
}

@test "base_cli runtime ignores the removed in-tree source copy" {
    mkdir -p "$TEST_RUNTIME_HOME/lib/python/base_cli"
    touch "$TEST_RUNTIME_HOME/lib/python/base_cli/__init__.py"

    run env \
        -u BASE_CLI_SOURCE_DIR \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            base_cli_runtime_prepare
            printf "%s %s\n" "${BASE_CLI_SOURCE}" "$(base_cli_runtime_source_root)"
        '

    [ "$status" -eq 0 ]
    [ "$output" = "pip " ]
}

@test "base_cli runtime rejects malformed explicit source directories" {
    run env \
        BASE_HOME="$TEST_RUNTIME_HOME" \
        BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/missing" \
        bash -c '
            source "$BASE_HOME/lib/base/base_cli_runtime.sh"
            base_cli_runtime_source_root
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"does not contain base_cli/__init__.py"* ]]
}

@test "base_cli runtime prepare preserves malformed override diagnostics" {
    run env BASE_HOME="$TEST_RUNTIME_HOME" BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/missing" bash -c '
        source "$BASE_HOME/lib/base/base_cli_runtime.sh"
        base_cli_runtime_prepare
    '
    [ "$status" -eq 1 ]
    [[ "$output" == *"BASE_CLI_SOURCE_DIR '$TEST_TMPDIR/missing'"* ]]
    [[ "$output" == *"does not contain base_cli/__init__.py"* ]]
}
