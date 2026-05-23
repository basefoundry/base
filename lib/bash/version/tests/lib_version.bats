#!/usr/bin/env bats

load ../../tests/test_helper.sh

setup() {
    setup_test_tmpdir
    source "$BASE_BASH_DIR/version/lib_version.sh"
}

@test "base_read_version returns the first version file line" {
    local base_home="$TEST_TMPDIR/base"

    mkdir -p "$base_home"
    printf '1.2.3\nignored\n' > "$base_home/VERSION"

    [ "$(base_read_version "$base_home")" = "1.2.3" ]
}

@test "base_read_version returns unknown when version file is missing" {
    local base_home="$TEST_TMPDIR/base"

    mkdir -p "$base_home"

    [ "$(base_read_version "$base_home")" = "unknown" ]
}

@test "base_read_version returns unknown when version file is empty" {
    local base_home="$TEST_TMPDIR/base"

    mkdir -p "$base_home"
    : > "$base_home/VERSION"

    [ "$(base_read_version "$base_home")" = "unknown" ]
}

@test "lib_version can be sourced more than once" {
    source "$BASE_BASH_DIR/version/lib_version.sh"

    [ "$(type -t base_read_version)" = "function" ]
}
