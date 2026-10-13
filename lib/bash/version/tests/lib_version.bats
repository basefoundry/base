#!/usr/bin/env bats

load ../../../../tests/test_helper.sh

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

@test "base_read_version identifies an untagged development checkout" {
    local base_home="$TEST_TMPDIR/base"
    local revision

    mkdir -p "$base_home"
    printf '1.8.0\n' > "$base_home/VERSION"
    printf '1.9.0\n' > "$base_home/DEVELOPMENT_VERSION"
    init_git_repo "$base_home"
    commit_all "$base_home"
    revision="$(git -C "$base_home" rev-parse --short=12 HEAD)"

    [ "$(base_read_version "$base_home")" = "1.9.0-dev+g$revision" ]
}

@test "base_read_version identifies a dirty development checkout" {
    local base_home="$TEST_TMPDIR/base"
    local revision

    mkdir -p "$base_home"
    printf '1.8.0\n' > "$base_home/VERSION"
    printf '1.9.0\n' > "$base_home/DEVELOPMENT_VERSION"
    init_git_repo "$base_home"
    commit_all "$base_home"
    revision="$(git -C "$base_home" rev-parse --short=12 HEAD)"
    printf 'dirty\n' >> "$base_home/VERSION"

    [ "$(base_read_version "$base_home")" = "1.9.0-dev+g$revision.dirty" ]
}

@test "base_read_version keeps the published identity at its exact release tag" {
    local base_home="$TEST_TMPDIR/base"

    mkdir -p "$base_home"
    printf '1.8.0\n' > "$base_home/VERSION"
    printf '1.9.0\n' > "$base_home/DEVELOPMENT_VERSION"
    init_git_repo "$base_home"
    commit_all "$base_home"
    git -C "$base_home" tag v1.8.0

    [ "$(base_read_version "$base_home")" = "1.8.0" ]
}

@test "base_read_version marks a dirty exact release tag as development" {
    local base_home="$TEST_TMPDIR/base"
    local revision

    mkdir -p "$base_home"
    printf '1.8.0\n' > "$base_home/VERSION"
    printf '1.9.0\n' > "$base_home/DEVELOPMENT_VERSION"
    init_git_repo "$base_home"
    commit_all "$base_home"
    git -C "$base_home" tag v1.8.0
    revision="$(git -C "$base_home" rev-parse --short=12 HEAD)"
    printf 'dirty\n' >> "$base_home/VERSION"

    [ "$(base_read_version "$base_home")" = "1.9.0-dev+g$revision.dirty" ]
}

@test "base_read_version keeps packaged installs on the published identity" {
    local base_home="$TEST_TMPDIR/base"

    mkdir -p "$base_home"
    printf '1.8.0\n' > "$base_home/VERSION"
    printf '1.9.0\n' > "$base_home/DEVELOPMENT_VERSION"

    [ "$(base_read_version "$base_home")" = "1.8.0" ]
}

@test "base_read_version ignores an enclosing unrelated Git checkout" {
    local parent_home="$TEST_TMPDIR/parent"
    local base_home="$parent_home/Cellar/base/1.8.0/libexec"

    mkdir -p "$base_home"
    printf '1.8.0\n' > "$base_home/VERSION"
    printf '1.9.0\n' > "$base_home/DEVELOPMENT_VERSION"
    init_git_repo "$parent_home"
    commit_all "$parent_home"

    [ "$(base_read_version "$base_home")" = "1.8.0" ]
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
