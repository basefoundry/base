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
    printf 'brew\t/tmp/work/brew\t/tmp/work/brew/base_manifest.yaml\n'
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
    [[ "$output" == *"basectl setup"* ]]
    [[ "$output" == *"brew install bash"* ]]
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

    mkdir -p \
        "$base_home/bin" \
        "$base_home/lib/shell" \
        "$base_home/lib/bash/runtime" \
        "$base_home/lib/bash/version" \
        "$base_home/cli/bash/commands/basectl"
    touch \
        "$base_home/VERSION" \
        "$base_home/base_init.sh" \
        "$base_home/lib/shell/bash_profile" \
        "$base_home/lib/shell/bashrc" \
        "$base_home/lib/shell/baserc_guard.sh" \
        "$base_home/lib/bash/runtime/bashrc" \
        "$base_home/lib/bash/version/lib_version.sh" \
        "$base_home/bin/basectl" \
        "$base_home/bin/base-wrapper" \
        "$base_home/cli/bash/commands/basectl/basectl.sh"

    run bash -c 'source "$1"; basectl_verify_home "$2"' _ \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$base_home"

    [ "$status" -eq 0 ]
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

@test "basectl dispatches command implementations by command name" {
    run_basectl sort-in-place --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Sort text files in place."* ]]
}

@test "basectl treats path-like arguments as scripts before command names" {
    local script_path="$TEST_TMPDIR/sort-in-place"

    cat > "$script_path" <<'EOF'
main() {
    printf 'script path wins: %s\n' "$1"
}
EOF

    run_basectl "$script_path" arg1

    [ "$status" -eq 0 ]
    [[ "$output" == *"script path wins: arg1"* ]]
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
