#!/usr/bin/env bats

load ../lib/bash/tests/test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_BASE_HOME="$TEST_TMPDIR/base"
    mkdir -p "$TEST_BASE_HOME"
    TEST_BASE_HOME="$(cd "$TEST_BASE_HOME" && pwd -P)"
    create_minimal_base_home "$TEST_BASE_HOME"
}

create_minimal_base_home() {
    local base_home="$1"

    mkdir -p \
        "$base_home/bin" \
        "$base_home/cli/bash/commands" \
        "$base_home/lib/bash/file" \
        "$base_home/lib/bash/std" \
        "$base_home/lib/shell"

    cp "$BASE_REPO_ROOT/base_init.sh" "$base_home/base_init.sh"
    cp "$BASE_REPO_ROOT/lib/bash/std/lib_std.sh" "$base_home/lib/bash/std/lib_std.sh"
    cp "$BASE_REPO_ROOT/lib/bash/file/lib_file.sh" "$base_home/lib/bash/file/lib_file.sh"
}

run_base_init_script() {
    local script="$1"

    run env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_HOST \
        -u BASE_SHELL \
        bash -c "$script" bash "$TEST_BASE_HOME"
}

@test "base_init exports the Base runtime path contract" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_HOME=%s\n" "$BASE_HOME"
        printf "BASE_BIN_DIR=%s\n" "$BASE_BIN_DIR"
        printf "BASE_CLI_DIR=%s\n" "$BASE_CLI_DIR"
        printf "BASE_BASH_DIR=%s\n" "$BASE_BASH_DIR"
        printf "BASE_BASH_COMMANDS_DIR=%s\n" "$BASE_BASH_COMMANDS_DIR"
        printf "BASE_LIB_DIR=%s\n" "$BASE_LIB_DIR"
        printf "BASE_BASH_LIB_DIR=%s\n" "$BASE_BASH_LIB_DIR"
        printf "BASE_SHELL_DIR=%s\n" "$BASE_SHELL_DIR"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$TEST_BASE_HOME"* ]]
    [[ "$output" == *"BASE_BIN_DIR=$TEST_BASE_HOME/bin"* ]]
    [[ "$output" == *"BASE_CLI_DIR=$TEST_BASE_HOME/cli"* ]]
    [[ "$output" == *"BASE_BASH_DIR=$TEST_BASE_HOME/cli/bash"* ]]
    [[ "$output" == *"BASE_BASH_COMMANDS_DIR=$TEST_BASE_HOME/cli/bash/commands"* ]]
    [[ "$output" == *"BASE_LIB_DIR=$TEST_BASE_HOME/lib"* ]]
    [[ "$output" == *"BASE_BASH_LIB_DIR=$TEST_BASE_HOME/lib/bash"* ]]
    [[ "$output" == *"BASE_SHELL_DIR=$TEST_BASE_HOME/lib/shell"* ]]
}

@test "base_init exports host operating system and shell metadata" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_OS=%s\n" "$BASE_OS"
        printf "BASE_HOST=%s\n" "$BASE_HOST"
        printf "BASE_SHELL=%s\n" "$BASE_SHELL"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOST="* ]]
    [[ "$output" == *"BASE_SHELL=bash"* ]]
    [[ "$output" == *"BASE_OS=linux"* || "$output" == *"BASE_OS=macos"* ]]
}

@test "base_init marks the Base runtime contract readonly" {
    local var

    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        for var in \
            BASE_HOME \
            BASE_BIN_DIR \
            BASE_CLI_DIR \
            BASE_BASH_DIR \
            BASE_BASH_COMMANDS_DIR \
            BASE_LIB_DIR \
            BASE_BASH_LIB_DIR \
            BASE_SHELL_DIR \
            BASE_OS \
            BASE_HOST \
            BASE_SHELL; do
            declare -p "$var"
        done
    '

    [ "$status" -eq 0 ]
    for var in \
        BASE_HOME \
        BASE_BIN_DIR \
        BASE_CLI_DIR \
        BASE_BASH_DIR \
        BASE_BASH_COMMANDS_DIR \
        BASE_LIB_DIR \
        BASE_BASH_LIB_DIR \
        BASE_SHELL_DIR \
        BASE_OS \
        BASE_HOST \
        BASE_SHELL; do
        [[ "$output" == *"declare -rx $var="* ]]
    done
}

@test "base_init readonly contract rejects later mutation" {
    run_base_init_script '
        base_home="$1"
        (
            source "$base_home/base_init.sh"
            BASE_HOME=/tmp/not-base
        )
        printf "mutation_status=%s\n" "$?"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME: readonly variable"* ]]
    [[ "$output" == *"mutation_status=1"* ]]
}

@test "runtime environment docs list the base_init contract variables" {
    local var

    for var in \
        BASE_HOME \
        BASE_BIN_DIR \
        BASE_CLI_DIR \
        BASE_BASH_DIR \
        BASE_BASH_COMMANDS_DIR \
        BASE_LIB_DIR \
        BASE_BASH_LIB_DIR \
        BASE_SHELL_DIR \
        BASE_OS \
        BASE_HOST \
        BASE_SHELL; do
        grep -F "| \`$var\` |" "$BASE_REPO_ROOT/docs/runtime-environment.md"
    done
}

@test "base_init is idempotent when sourced twice" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        source "$base_home/base_init.sh"
        print_path | grep -Fxc "$BASE_BIN_DIR"
    '

    [ "$status" -eq 0 ]
    [ "$output" = "1" ]
}

@test "base_init import_base_lib resolves libraries relative to BASE_HOME" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        import_base_lib file/lib_file.sh
        declare -F safe_touch >/dev/null
    '

    [ "$status" -eq 0 ]
}
