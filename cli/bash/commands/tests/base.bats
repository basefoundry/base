#!/usr/bin/env bats

load ../../../../lib/bash/tests/test_helper.bash

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_BASE_HOME="$TEST_TMPDIR/install-target"
    mkdir -p "$TEST_HOME"
}

run_base() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/base" "$@"
}

@test "base prints help with --help" {
    run_base --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: base [options] <command> [args...]"* ]]
    [[ "$output" == *"setup [args...]"* ]]
}

@test "base prints help when no command is given in a non-interactive shell" {
    run_base

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: base [options] <command> [args...]"* ]]
}

@test "base version uses BASE_VERSION when provided" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_VERSION="test-version" \
        "$BASE_REPO_ROOT/bin/base" version

    [ "$status" -eq 0 ]
    [[ "$output" == "base version test-version" ]]
}

@test "base delegates setup help to the setup command" {
    run_base setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"setup [options] <command>"* ]]
}

@test "base status reports a valid Base checkout" {
    run_base -b "$BASE_REPO_ROOT" status

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base is installed at $BASE_REPO_ROOT"* ]]
}

@test "base status reports when Base is not installed at BASE_HOME" {
    run_base -b "$TEST_BASE_HOME" status

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base is not installed at '$TEST_BASE_HOME'"* ]]
}

@test "base set-team writes BASE_TEAM to .baserc" {
    run_base set-team alpha

    [ "$status" -eq 0 ]
    [ -f "$TEST_HOME/.baserc" ]
    run grep -F 'export BASE_TEAM="alpha" # BASE_MARKER, do not delete' "$TEST_HOME/.baserc"
    [ "$status" -eq 0 ]
}

@test "base set-shared-teams writes BASE_SHARED_TEAMS to .baserc" {
    run_base set-shared-teams alpha beta

    [ "$status" -eq 0 ]
    [ -f "$TEST_HOME/.baserc" ]
    run grep -F 'export BASE_SHARED_TEAMS="alpha beta" # BASE_MARKER, do not delete' "$TEST_HOME/.baserc"
    [ "$status" -eq 0 ]
}
