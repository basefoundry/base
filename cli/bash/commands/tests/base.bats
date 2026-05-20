#!/usr/bin/env bats

load ../../../../lib/bash/tests/test_helper.bash

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

run_base() {
    run env         HOME="$TEST_HOME"         PATH="/usr/bin:/bin:/usr/sbin:/sbin"         "$BASE_REPO_ROOT/bin/base" "$@"
}

@test "base prints help with --help" {
    run_base --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: base [options] <command> [args...]"* ]]
    [[ "$output" == *"setup [options]"* ]]
    [[ "$output" == *"check [options]"* ]]
}

@test "base help omits legacy leftover commands" {
    run_base --help

    [ "$status" -eq 0 ]
    ! grep -Fqx '  update' <<<"$output"
    ! grep -Fqx '  run <command> [args...]' <<<"$output"
    ! grep -Fqx '  status' <<<"$output"
    ! grep -Fqx '  set-team TEAM' <<<"$output"
    ! grep -Fqx '  set-shared-teams TEAM...' <<<"$output"
    ! grep -Fqx '  man' <<<"$output"
}

@test "base prints help when no command is given in a non-interactive shell" {
    run_base

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: base [options] <command> [args...]"* ]]
}

@test "base --version uses BASE_VERSION when provided" {
    run env         HOME="$TEST_HOME"         PATH="/usr/bin:/bin:/usr/sbin:/sbin"         BASE_VERSION="test-version"         "$BASE_REPO_ROOT/bin/base" --version

    [ "$status" -eq 0 ]
    [[ "$output" == "base version test-version" ]]
}

@test "base setup prints setup-specific help" {
    run_base setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"base setup [options]"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
}

@test "base rejects removed legacy commands" {
    local legacy_command

    for legacy_command in status update run set-team set-shared-teams man; do
        run_base "$legacy_command"
        [ "$status" -eq 2 ]
        [[ "$output" == *"Unrecognized command: $legacy_command"* ]]
    done
}
