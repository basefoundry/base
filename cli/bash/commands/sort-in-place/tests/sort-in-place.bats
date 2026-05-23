#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.bash

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

run_sort_in_place() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" sort-in-place "$@"
}

@test "sort-in-place prints help" {
    run_sort_in_place --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"sort-in-place [-u] <file>..."* ]]
}

@test "sort-in-place requires at least one file" {
    run_sort_in_place

    [ "$status" -eq 2 ]
    [[ "$output" == *"At least one file is required."* ]]
    [[ "$output" == *"Usage:"* ]]
}

@test "sort-in-place sorts a file in place" {
    local input_file="$TEST_TMPDIR/input.txt"

    printf 'b\na\nc\n' > "$input_file"

    run_sort_in_place "$input_file"

    [ "$status" -eq 0 ]
    [ "$(cat "$input_file")" = $'a\nb\nc' ]
}

@test "sort-in-place supports unique sorting" {
    local input_file="$TEST_TMPDIR/input.txt"

    printf 'b\na\nb\na\n' > "$input_file"

    run_sort_in_place -u "$input_file"

    [ "$status" -eq 0 ]
    [ "$(cat "$input_file")" = $'a\nb' ]
}

@test "sort-in-place skips non-regular files" {
    local missing_file="$TEST_TMPDIR/missing.txt"

    run_sort_in_place "$missing_file"

    [ "$status" -eq 0 ]
    [[ "$output" == *"$missing_file is not a regular file; skipping."* ]]
}

@test "sort-in-place skips a file when its temp file already exists" {
    local input_file="$TEST_TMPDIR/input.txt"
    local temp_file="$input_file._tmp"

    printf 'b\na\n' > "$input_file"
    printf 'existing temp\n' > "$temp_file"

    run_sort_in_place "$input_file"

    [ "$status" -eq 0 ]
    [[ "$output" == *"$temp_file already exists; skipping $input_file."* ]]
    [ "$(cat "$input_file")" = $'b\na' ]
    [ "$(cat "$temp_file")" = "existing temp" ]
}
