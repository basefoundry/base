#!/usr/bin/env bats

load ../lib/bash/tests/test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

run_installer() {
    run env \
        HOME="$TEST_HOME" \
        "$BASE_REPO_ROOT/install.sh" "$@"
}

@test "installer prints planned actions in dry-run mode" {
    run_installer --dry-run --dir "$TEST_HOME/work/base" --repo-url https://example.test/base.git --no-profile

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base installer"* ]]
    [[ "$output" == *"Repository: https://example.test/base.git"* ]]
    [[ "$output" == *"Install path: $TEST_HOME/work/base"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: mkdir -p $TEST_HOME/work"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: git clone https://example.test/base.git $TEST_HOME/work/base"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: $TEST_HOME/work/base/bin/basectl setup"* ]]
    [[ "$output" != *"update-profile"* ]]
}

@test "installer expands tilde install paths" {
    run_installer --dry-run --dir "~/custom/base" --no-profile

    [ "$status" -eq 0 ]
    [[ "$output" == *"Install path: $TEST_HOME/custom/base"* ]]
}

@test "installer includes update-profile by default" {
    run_installer --dry-run --dir "$TEST_HOME/work/base"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run: $TEST_HOME/work/base/bin/basectl update-profile"* ]]
    [[ "$output" == *"Restart your shell with: exec \"\$SHELL\" -l"* ]]
}

@test "installer rejects an existing non-git install path" {
    mkdir -p "$TEST_HOME/work/base"

    run_installer --dir "$TEST_HOME/work/base"

    [ "$status" -eq 1 ]
    [[ "$output" == *"exists but is not a Git checkout"* ]]
}
