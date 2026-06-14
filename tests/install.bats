#!/usr/bin/env bats

load ../lib/bash/tests/test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_COMMAND_LOG="$TEST_TMPDIR/install-commands"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN"
}

run_installer() {
    run env \
        HOME="$TEST_HOME" \
        "$BASE_REPO_ROOT/install.sh" "$@"
}

create_supported_bash_stub() {
    cat > "$TEST_MOCKBIN/bash" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${BASE_INSTALL_TEST_COMMAND_LOG:?}"
if [[ ! -x "${1:-}" ]]; then
    printf 'expected executable basectl path, got: %s\n' "${1:-}" >&2
    exit 1
fi
case "${2:-}" in
    setup|update-profile)
        exit 0
        ;;
    *)
        printf 'unexpected basectl command: %s\n' "${2:-}" >&2
        exit 1
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/bash"
}

create_install_source_repo() {
    local source_dir="$TEST_TMPDIR/source-repo"

    git clone "$BASE_REPO_ROOT" "$source_dir" >/dev/null 2>&1
    git -C "$source_dir" checkout -B master >/dev/null 2>&1
    printf '%s\n' "$source_dir"
}

run_real_installer() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_INSTALL_TEST_BASH_VERSION=32 \
        BASE_INSTALL_BASH_CANDIDATES="$TEST_MOCKBIN/bash" \
        BASE_INSTALL_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASE_REPO_ROOT/install.sh" "$@"
}

assert_base_init_loads() {
    local install_dir="$1"
    local resolved_install_dir
    resolved_install_dir="$(cd -L "$install_dir" && pwd -L)"

    run env -i \
        HOME="$TEST_HOME" \
        BASE_HOME="$install_dir" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" -c '\
            source "$BASE_HOME/base_init.sh"; \
            printf "BASE_HOME=%s\n" "$BASE_HOME"; \
            if declare -F import_base_lib >/dev/null 2>&1; then \
                printf "IMPORT_BASE_LIB=1\n"; \
            fi'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$resolved_install_dir"* ]]
    [[ "$output" == *"IMPORT_BASE_LIB=1"* ]]
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

@test "installer uses scoped colon splitting for candidate lists" {
    run grep -n 'old_ifs' "$BASE_REPO_ROOT/install.sh"
    [ "$status" -eq 1 ]
    [ "$output" = "" ]

    run grep -c 'IFS=: read -ra' "$BASE_REPO_ROOT/install.sh"
    [ "$status" -eq 0 ]
    [ "$output" -eq 2 ]
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

@test "installer clones and sets up Base in a fresh directory" {
    create_supported_bash_stub
    local install_dir="$TEST_HOME/work/base"
    local repo_url
    repo_url="$(create_install_source_repo)"

    run_real_installer --dir "$install_dir" --repo-url "$repo_url" --branch master

    [ "$status" -eq 0 ]
    [[ "$output" == *"Cloning Base into '$install_dir'."* ]]
    [[ "$output" == *"Running basectl setup."* ]]
    [[ "$output" == *"Updating shell startup files."* ]]
    [[ "$output" == *"Base installation is complete."* ]]
    [ -d "$install_dir/.git" ]
    [ -x "$install_dir/bin/basectl" ]
    [ -f "$install_dir/base_init.sh" ]
    grep -Fqx "$install_dir/bin/basectl setup" "$TEST_COMMAND_LOG"
    grep -Fqx "$install_dir/bin/basectl update-profile" "$TEST_COMMAND_LOG"

    assert_base_init_loads "$install_dir"
}

@test "installer reruns idempotently on an existing Base checkout" {
    create_supported_bash_stub
    local install_dir="$TEST_HOME/work/base"
    local repo_url
    repo_url="$(create_install_source_repo)"

    run_real_installer --dir "$install_dir" --repo-url "$repo_url" --branch master --no-profile
    [ "$status" -eq 0 ]
    local installed_head
    installed_head="$(git -C "$install_dir" rev-parse HEAD)"

    run_real_installer --dir "$install_dir" --repo-url "$repo_url" --branch master --no-profile

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating existing Base checkout at '$install_dir'."* ]]
    [ "$(git -C "$install_dir" rev-parse HEAD)" = "$installed_head" ]
    [ -x "$install_dir/bin/basectl" ]
    [ -f "$install_dir/base_init.sh" ]
}

@test "installer uses BASE_HOME as the default install directory" {
    create_supported_bash_stub
    local install_dir="$TEST_HOME/base-home-install"
    local repo_url
    repo_url="$(create_install_source_repo)"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$install_dir" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_INSTALL_TEST_BASH_VERSION=32 \
        BASE_INSTALL_BASH_CANDIDATES="$TEST_MOCKBIN/bash" \
        BASE_INSTALL_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASE_REPO_ROOT/install.sh" --repo-url "$repo_url" --branch master --no-profile

    [ "$status" -eq 0 ]
    [[ "$output" == *"Install path: $install_dir"* ]]
    [ -d "$install_dir/.git" ]
    [ -x "$install_dir/bin/basectl" ]
}

@test "installer fails when the target directory cannot be created" {
    create_supported_bash_stub
    local parent="$TEST_TMPDIR/unwritable"
    local install_dir="$parent/base"
    local repo_url
    repo_url="$(create_install_source_repo)"
    mkdir -p "$parent"
    chmod a-w "$parent"

    run_real_installer --dir "$install_dir" --repo-url "$repo_url" --branch master --no-profile
    chmod u+w "$parent"

    [ "$status" -ne 0 ]
    [[ "$output" == *"Permission denied"* || "$output" == *"could not create work tree dir"* ]]
    [ ! -e "$install_dir" ]
}

@test "installer leaves basectl executable and base_init loadable after install" {
    create_supported_bash_stub
    local install_dir="$TEST_HOME/loadable/base"
    local repo_url
    repo_url="$(create_install_source_repo)"

    run_real_installer --dir "$install_dir" --repo-url "$repo_url" --branch master --no-profile

    [ "$status" -eq 0 ]
    [ -x "$install_dir/bin/basectl" ]
    [ -f "$install_dir/base_init.sh" ]
    assert_base_init_loads "$install_dir"
}
