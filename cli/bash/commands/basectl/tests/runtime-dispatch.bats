#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl prints help when no command is given in a non-interactive shell" {
    run_basectl

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
}

@test "basectl with no command activates the current Base project in an interactive shell" {
    local fake_base_home="$TEST_TMPDIR/fake-base-home"

    mkdir -p "$fake_base_home/bin"
    cat > "$fake_base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--project" && "${2:-}" == "base" && "${3:-}" == "base_projects" && "${4:-}" == "current" ]]; then
    base_test_protocol_project_reference brew /tmp/work/brew /tmp/work/brew/base_manifest.yaml
    exit 0
fi
printf 'unexpected args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$fake_base_home/bin/base-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_FAKE_BASE_HOME="$fake_base_home" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"
            log_debug() { :; }
            basectl_should_start_shell() { return 0; }
            basectl_get_base_home() { BASE_HOME="$BASE_TEST_FAKE_BASE_HOME"; export BASE_HOME; }
            basectl_do_activate() { printf "activate=%s preserve=%s\n" "$*" "${BASE_ACTIVATE_PRESERVE_CWD:-}"; }
            basectl_main
        '

    [ "$status" -eq 0 ]
    [ "$output" = "activate=brew preserve=1" ]
}

@test "basectl with no command falls back to base when current directory is not in a Base project" {
    local fake_base_home="$TEST_TMPDIR/fake-base-home"

    mkdir -p "$fake_base_home/bin"
    cat > "$fake_base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$fake_base_home/bin/base-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_FAKE_BASE_HOME="$fake_base_home" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"
            log_debug() { :; }
            basectl_should_start_shell() { return 0; }
            basectl_get_base_home() { BASE_HOME="$BASE_TEST_FAKE_BASE_HOME"; export BASE_HOME; }
            basectl_do_activate() { printf "activate=%s preserve=%s\n" "$*" "${BASE_ACTIVATE_PRESERVE_CWD:-}"; }
            basectl_main
        '

    [ "$status" -eq 0 ]
    [ "$output" = "activate=base preserve=1" ]
}

@test "basectl prints version with --version and version" {
    local expected_version

    expected_version="$(head -n 1 "$BASE_REPO_ROOT/VERSION")"

    run_basectl --version
    [ "$status" -eq 0 ]
    [ "$output" = "basectl $expected_version" ]

    run_basectl version
    [ "$status" -eq 0 ]
    [ "$output" = "basectl $expected_version" ]
}

@test "basectl version has leaf help and rejects trailing arguments" {
    run_basectl version --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl version"* ]]
    [[ "$output" == *"Show the installed Base version."* ]]

    run_basectl help version

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl version"* ]]

    run_basectl version nonsense

    [ "$status" -eq 2 ]
    [ "${lines[0]}" = "ERROR: version does not accept arguments." ]
    [ "${lines[1]}" = "Run 'basectl version --help' for usage." ]
    [[ "$output" != *"basectl $(head -n 1 "$BASE_REPO_ROOT/VERSION")"* ]]
}

@test "README version badge matches VERSION" {
    local expected_version expected_badge

    expected_version="$(head -n 1 "$BASE_REPO_ROOT/VERSION")"
    expected_badge="![Version](https://img.shields.io/badge/version-$expected_version-blue)"

    grep -Fqx "$expected_badge" "$BASE_REPO_ROOT/README.md"
}

@test "basectl re-execs through an installed supported Bash when current Bash is too old" {
    local fake_bash="$TEST_TMPDIR/fake-bash"

    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'fake_bash=%s\n' "$0"
printf 'args=%s\n' "$*"
EOF
    chmod +x "$fake_bash"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_BASH_VERSION=32 \
        BASE_TEST_BASH_CANDIDATES="$fake_bash" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 0 ]
    [[ "$output" == *"fake_bash=$fake_bash"* ]]
    [[ "$output" == *"args=$BASE_REPO_ROOT/bin/basectl --version"* ]]
}

@test "basectl re-execs through native Bash when translated under ARM Homebrew" {
    local fake_bash="$TEST_TMPDIR/fake-arm-bash"

    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'fake_arm_bash=%s\n' "$0"
printf 'args=%s\n' "$*"
EOF
    chmod +x "$fake_bash"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_BASH_VERSION=50 \
        BASE_TEST_PROC_TRANSLATED=1 \
        BASE_TEST_HOMEBREW_PREFIX=/opt/homebrew \
        BASE_TEST_BASH_CANDIDATES="$fake_bash" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 0 ]
    [[ "$output" == *"fake_arm_bash=$fake_bash"* ]]
    [[ "$output" == *"args=$BASE_REPO_ROOT/bin/basectl --version"* ]]
}

@test "basectl rejects translated Bash when ARM Homebrew is active and no native Bash is available" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_BASH_VERSION=50 \
        BASE_TEST_PROC_TRANSLATED=1 \
        BASE_TEST_HOMEBREW_PREFIX=/opt/homebrew \
        BASE_TEST_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base is running under Rosetta while Homebrew resolves to /opt/homebrew."* ]]
    [[ "$output" == *"Install native Homebrew Bash with:"* ]]
    [[ "$output" == *"arch -arm64 /opt/homebrew/bin/brew install bash"* ]]
}

@test "basectl gives setup guidance when current Bash is too old and no supported Bash is installed" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_BASH_VERSION=32 \
        BASE_TEST_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base requires Bash 4.2 or newer; current version is 3.2."* ]]
    [[ "$output" == *"A supported Bash was not found"* ]]
    [[ "$output" == *"bootstrap.sh --ensure-bash --dry-run"* ]]
    [[ "$output" == *"bootstrap.sh --ensure-bash --yes"* ]]
    [[ "$output" == *"brew install bash"* ]]
    [[ "$output" == *"sudo apt-get install -y bash"* ]]
}

@test "basectl rejects removed legacy commands" {
    local legacy_command

    for legacy_command in status set-team set-shared-teams man embrace install shell; do
        run_basectl "$legacy_command"
        [ "$status" -eq 2 ]
        [[ "$output" == *"Unrecognized command: $legacy_command"* ]]
    done
}

@test "Base home verification does not require a git repository" {
    local base_home="$TEST_TMPDIR/embedded/base"

    run bash -c '
        source "$1"
        base_home="$2"
        for file in "${BASECTL_REQUIRED_HOME_FILES[@]}"; do
            mkdir -p "$base_home/$(dirname -- "$file")"
            : > "$base_home/$file"
        done
        basectl_verify_home "$base_home"
    ' _ \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$base_home"

    [ "$status" -eq 0 ]
}

@test "Base home verification contract is a readonly required-file list" {
    run bash -c 'source "$1"; declare -p BASECTL_REQUIRED_HOME_FILES' _ \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == declare\ -ar\ BASECTL_REQUIRED_HOME_FILES=* ]]
    [[ "$output" == *'VERSION'* ]]
    [[ "$output" == *'base_init.sh'* ]]
    [[ "$output" == *'bin/basectl'* ]]
    [[ "$output" == *'cli/bash/commands/basectl/basectl.sh'* ]]
}

@test "Base home verification reports missing required files" {
    local base_home="$TEST_TMPDIR/incomplete/base"

    run bash -c '
        source "$1"
        base_home="$2"
        omitted="bin/base-wrapper"
        for file in "${BASECTL_REQUIRED_HOME_FILES[@]}"; do
            [[ "$file" == "$omitted" ]] && continue
            mkdir -p "$base_home/$(dirname -- "$file")"
            : > "$base_home/$file"
        done
        if basectl_verify_home "$base_home"; then
            printf "verified unexpectedly\n"
            exit 0
        fi
        printf "%s\n" "$BASE_CLI_ERROR_MESSAGE"
        exit 1
    ' _ \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$base_home"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Files missing in Base home '$base_home': bin/base-wrapper"* ]]
    [[ "$output" != *"VERSION"* ]]
}

@test "base-wrapper runs package commands in the selected project venv" {
    local python_bin="$TEST_HOME/.base.d/demo/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_HOME=%s\n' "$BASE_HOME"
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'PYTHONPATH=%s\n' "$PYTHONPATH"
printf 'ARGS=%s\n' "$*"
EOF
    chmod +x "$python_bin"

    run env \
        HOME="$TEST_HOME" \
        PYTHONPATH="existing" \
        "$BASE_REPO_ROOT/bin/base-wrapper" --project demo base_setup --dry-run demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"PYTHONPATH=$BASE_REPO_ROOT/lib/python:$BASE_REPO_ROOT/cli/python:existing"* ]]
    [[ "$output" == *"ARGS=-m base_setup --dry-run demo"* ]]
}

@test "basectl treats path-like arguments as scripts before command names" {
    local script_path="$TEST_TMPDIR/demo-script"

    cat > "$script_path" <<'EOF'
main() {
    printf 'script path wins: %s\n' "$1"
}
EOF

    run_basectl "$script_path" arg1

    [ "$status" -eq 0 ]
    [[ "$output" == *"script path wins: arg1"* ]]
}

@test "basectl command names cannot be shadowed by same-named files" {
    local workdir="$TEST_TMPDIR/command-shadow"

    mkdir -p "$workdir"
    cat > "$workdir/test" <<'EOF'
main() {
    printf 'local file shadowed test\n'
}
EOF

    cd "$workdir"
    run_basectl test --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl test [project] [options]"* ]]
    [[ "$output" != *"local file shadowed test"* ]]
}

@test "basectl rejects bare script names with an explicit-path hint" {
    local workdir="$TEST_TMPDIR/bare-script"

    mkdir -p "$workdir"
    cat > "$workdir/deploy" <<'EOF'
main() {
    printf 'bare script executed unexpectedly\n'
}
EOF

    cd "$workdir"
    run_basectl deploy

    [ "$status" -eq 2 ]
    [[ "$output" == *"Bare script name 'deploy' is not executed implicitly."* ]]
    [[ "$output" == *"basectl ./deploy"* ]]
    [[ "$output" != *"bare script executed unexpectedly"* ]]
}

@test "basectl runs explicit relative script paths containing spaces" {
    local workdir="$TEST_TMPDIR/explicit-script"
    local script_name="deploy task.sh"

    mkdir -p "$workdir"
    cat > "$workdir/$script_name" <<'EOF'
main() {
    printf 'explicit script: %s\n' "$1"
}
EOF

    cd "$workdir"
    run_basectl "./$script_name" "release candidate"

    [ "$status" -eq 0 ]
    [[ "$output" == *"explicit script: release candidate"* ]]
}

@test "basectl marks command dispatch metadata readonly" {
    local script_path="$TEST_TMPDIR/inspect-command-env.sh"
    local script_dir

    cat > "$script_path" <<'EOF'
main() {
    declare -p BASE_BASH_COMMAND_NAME
    declare -p BASE_BASH_COMMAND_DIR
    declare -p BASE_BASH_COMMAND_SCRIPT
}
EOF
    script_dir="$(cd "$TEST_TMPDIR" && pwd -P)"

    run_basectl "$script_path"

    [ "$status" -eq 0 ]
    [[ "$output" == *'declare -rx BASE_BASH_COMMAND_NAME="inspect-command-env"'* ]]
    [[ "$output" == *"declare -rx BASE_BASH_COMMAND_DIR=\"$script_dir\""* ]]
    [[ "$output" == *"declare -rx BASE_BASH_COMMAND_SCRIPT=\"$script_dir/inspect-command-env.sh\""* ]]
}
