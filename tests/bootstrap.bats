#!/usr/bin/env bats

load ../lib/bash/tests/test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_COMMAND_LOG="$TEST_TMPDIR/bootstrap-commands"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN"
}

run_bootstrap() {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" "$@"
}

create_unusable_git_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/bin/sh
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

create_git_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/bin/sh
printf 'git %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
if [ "${1:-}" = "--version" ]; then
    printf 'git version 2.0.0\n'
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

create_failing_git_clone_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/bin/sh
printf 'git %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
if [ "${1:-}" = "--version" ]; then
    printf 'git version 2.0.0\n'
    exit 0
fi
if [ "${1:-}" = "clone" ]; then
    exit 2
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

create_brew_stub() {
    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/bin/sh
printf 'brew %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
case "${1:-}" in
    --prefix)
        printf '%s\n' "${BASE_BOOTSTRAP_TEST_BREW_PREFIX:?}"
        exit 0
        ;;
    list)
        if [ "${BASE_BOOTSTRAP_TEST_BREW_BASE_INSTALLED:-false}" = "true" ]; then
            exit 0
        fi
        exit 1
        ;;
    install)
        exit 0
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/brew"
}

create_supported_bash_candidate() {
    local bash_path="$1"

    mkdir -p "$(dirname "$bash_path")"
    cat > "$bash_path" <<'EOF'
#!/bin/sh
exit 0
EOF
    chmod +x "$bash_path"
}

@test "bootstrap prints help" {
    run_bootstrap --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"--source"* ]]
    [[ "$output" == *"--brew"* ]]
}

@test "bootstrap avoids shell strict mode" {
    run grep -nE '^[[:space:]]*set[[:space:]].*(-e|-u|pipefail)' "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [ "$output" = "" ]
}

@test "bootstrap uses scoped colon splitting for candidate lists" {
    run grep -n 'old_ifs' "$BASE_REPO_ROOT/bootstrap.sh"
    [ "$status" -eq 1 ]
    [ "$output" = "" ]

    run grep -c 'IFS=: read -ra' "$BASE_REPO_ROOT/bootstrap.sh"
    [ "$status" -eq 0 ]
    [ "$output" -eq 2 ]
}

@test "bootstrap source dry-run installs first-mile prerequisites and prints handoff commands" {
    local install_dir="$TEST_HOME/work/base"

    create_unusable_git_stub

    run_bootstrap --dry-run --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base bootstrap"* ]]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh>"* ]]
    [[ "$output" == *"Installing Git through Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install git"* ]]
    [[ "$output" == *"Installing Bash 4.2+ through Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install bash"* ]]
    [[ "$output" == *"Install mode: source"* ]]
    [[ "$output" == *"Repository: https://example.test/base.git"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: git clone https://example.test/base.git $install_dir"* ]]
    [[ "$output" == *"$install_dir/bin/basectl setup"* ]]
    [[ "$output" == *"$install_dir/bin/basectl update-profile"* ]]
    [[ "$output" == *"exec \"\$SHELL\" -l"* ]]
}

@test "bootstrap reports source clone failures without printing handoff commands" {
    local install_dir="$TEST_HOME/work/base"

    create_brew_stub
    create_failing_git_clone_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=42 \
        BASE_BOOTSTRAP_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to clone Base repository."* ]]
    [[ "$output" != *"Run these commands to finish Base setup"* ]]
}

@test "bootstrap brew dry-run installs Base through Homebrew and prints basectl handoff" {
    create_unusable_git_stub

    run_bootstrap --dry-run --brew

    [ "$status" -eq 0 ]
    [[ "$output" == *"Install mode: brew"* ]]
    [[ "$output" == *"Formula: codeforester/base/base"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install codeforester/base/base"* ]]
    [[ "$output" == *"  basectl setup"* ]]
    [[ "$output" == *"  basectl update-profile"* ]]
}

@test "bootstrap defaults to an existing Homebrew Base install" {
    local brew_prefix="$TEST_TMPDIR/homebrew"
    local supported_bash="$brew_prefix/bin/bash"

    mkdir -p "$brew_prefix/bin"
    create_brew_stub
    create_git_stub
    create_supported_bash_candidate "$supported_bash"
    touch "$brew_prefix/bin/basectl"
    touch "$TEST_MOCKBIN/basectl"
    chmod +x "$brew_prefix/bin/basectl"
    chmod +x "$TEST_MOCKBIN/basectl"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$supported_bash" \
        BASE_BOOTSTRAP_TEST_BREW_BASE_INSTALLED=true \
        BASE_BOOTSTRAP_TEST_BREW_PREFIX="$brew_prefix" \
        BASE_BOOTSTRAP_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is available at '$TEST_MOCKBIN/brew'."* ]]
    [[ "$output" == *"Git is available."* ]]
    [[ "$output" == *"Bash 4.2+ is available for Base."* ]]
    [[ "$output" == *"Install mode: brew"* ]]
    [[ "$output" == *"Base Homebrew formula 'codeforester/base/base' is already installed."* ]]
    [[ "$output" == *"Homebrew basectl: $brew_prefix/bin/basectl"* ]]
    [[ "$output" == *"active basectl: $TEST_MOCKBIN/basectl"* ]]
    [[ "$output" == *"$brew_prefix/bin/basectl setup"* ]]
    [[ "$output" == *"$brew_prefix/bin/basectl update-profile"* ]]
    ! grep -Fqx "brew install codeforester/base/base" "$TEST_COMMAND_LOG"
}

@test "bootstrap command-line mode overrides BASE_BOOTSTRAP_MODE" {
    create_unusable_git_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        BASE_BOOTSTRAP_MODE=brew \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run --source

    [ "$status" -eq 0 ]
    [[ "$output" == *"Install mode: source"* ]]
    [[ "$output" != *"Formula: codeforester/base/base"* ]]
}

@test "bootstrap can refuse to install missing Homebrew" {
    run_bootstrap --no-homebrew-install

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base bootstrap"* ]]
    [[ "$output" == *"Homebrew is required"* ]]
}

@test "bootstrap rejects non-macOS systems" {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Linux \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run

    [ "$status" -eq 1 ]
    [[ "$output" == *"bootstrap.sh currently supports macOS only"* ]]
}
