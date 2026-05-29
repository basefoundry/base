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
    [[ "$output" == *"$TEST_HOME/work/base/bin/basectl setup"* ]]
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
    [[ "$output" == *"$TEST_HOME/work/base/bin/basectl update-profile"* ]]
    [[ "$output" == *"Restart your shell with: exec \"\$SHELL\" -l"* ]]
}

@test "installer bootstraps Homebrew Bash before setup when system Bash is too old" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_INSTALL_TEST_BASH_VERSION=32 \
        BASE_INSTALL_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_INSTALL_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        "$BASE_REPO_ROOT/install.sh" --dry-run --dir "$TEST_HOME/work/base" --no-profile

    [ "$status" -eq 0 ]
    [[ "$output" == *"A supported Bash was not found; bootstrapping Homebrew Bash before running basectl."* ]]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh>"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install bash"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /opt/homebrew/bin/bash $TEST_HOME/work/base/bin/basectl setup"* ]]
}

@test "installer rejects an existing non-git install path" {
    mkdir -p "$TEST_HOME/work/base"

    run_installer --dir "$TEST_HOME/work/base"

    [ "$status" -eq 1 ]
    [[ "$output" == *"exists but is not a Git checkout"* ]]
}
