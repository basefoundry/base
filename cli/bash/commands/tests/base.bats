#!/usr/bin/env bats

load ../../../../lib/bash/tests/test_helper.bash

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

run_basectl() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" "$@"
}

@test "basectl prints help with --help" {
    run_basectl --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
    [[ "$output" == *"setup [options]"* ]]
    [[ "$output" == *"check [options]"* ]]
}

@test "basectl help omits legacy leftover commands" {
    run_basectl --help

    [ "$status" -eq 0 ]
    ! grep -Fqx '  update' <<<"$output"
    ! grep -Fqx '  run <command> [args...]' <<<"$output"
    ! grep -Fqx '  status' <<<"$output"
    ! grep -Fqx '  set-team TEAM' <<<"$output"
    ! grep -Fqx '  set-shared-teams TEAM...' <<<"$output"
    ! grep -Fqx '  man' <<<"$output"
    ! grep -Fqx '  embrace' <<<"$output"
}

@test "basectl prints help when no command is given in a non-interactive shell" {
    run_basectl

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
}

@test "basectl --version uses BASE_VERSION when provided" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_VERSION="test-version" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 0 ]
    [[ "$output" == "basectl version test-version" ]]
}

@test "basectl setup prints setup-specific help" {
    run_basectl setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
}

@test "basectl rejects removed legacy commands" {
    local legacy_command

    for legacy_command in status update run set-team set-shared-teams man embrace; do
        run_basectl "$legacy_command"
        [ "$status" -eq 2 ]
        [[ "$output" == *"Unrecognized command: $legacy_command"* ]]
    done
}


@test "basectl dispatches command implementations by command name" {
    run_basectl test_cmd

    [ "$status" -eq 0 ]
    [[ "$output" == *"I am starting"* ]]
}

@test "sort-in-place launcher delegates through basectl" {
    local input_file="$TEST_TMPDIR/input.txt"

    printf 'b\na\nb\n' > "$input_file"
    run env \
        HOME="$TEST_HOME" \
        PATH="$BASE_REPO_ROOT/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        sort-in-place -u "$input_file"

    [ "$status" -eq 0 ]
    [ "$(cat "$input_file")" = $'a\nb' ]
}
