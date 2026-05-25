#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.sh

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

run_basectl() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" "$@"
}

@test "basectl prints help with --help" {
    run_basectl --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
    [[ "$output" == *"setup [options]"* ]]
    [[ "$output" == *"check [options]"* ]]
    [[ "$output" == *"--version"* ]]
    [[ "$output" == *"Wrapper options:"* ]]
    [[ "$output" == *"--debug-wrapper"* ]]
    [[ "$output" == *"--verbose-wrapper"* ]]
    [[ "$output" == *"--utc-wrapper"* ]]
    [[ "$output" == *"--color"* ]]
}

@test "basectl help omits legacy leftover commands" {
    run_basectl --help

    [ "$status" -eq 0 ]
    ! grep -Fqx '  update' <<<"$output"
    ! grep -Fqx '  run <command> [args...]' <<<"$output"
    ! grep -Fqx '  status' <<<"$output"
    ! grep -Fqx '  set-team TEAM' <<<"$output"
    ! grep -Fqx '  set-shared-teams TEAM...' <<<"$output"
    ! grep -Fqx '  man' <<<"$output"
    ! grep -Fqx '  embrace' <<<"$output"
    ! grep -Fqx '  install' <<<"$output"
    grep -Fqx '  version' <<<"$output"
    [[ "$output" != *"-b DIR"* ]]
    [[ "$output" != *"Force install"* ]]
    [[ "$output" != *"-V"* ]]
}

@test "basectl prints help when no command is given in a non-interactive shell" {
    run_basectl

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
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

@test "basectl setup prints setup-specific help" {
    run_basectl setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
}

@test "basectl rejects removed legacy commands" {
    local legacy_command

    for legacy_command in status update run set-team set-shared-teams man embrace install; do
        run_basectl "$legacy_command"
        [ "$status" -eq 2 ]
        [[ "$output" == *"Unrecognized command: $legacy_command"* ]]
    done
}

@test "basectl shell rejects arguments" {
    run_basectl shell -c 'echo ignored'

    [ "$status" -eq 2 ]
    [[ "$output" == *"The 'shell' command does not accept arguments."* ]]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
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


@test "Base runtime shell prompt includes host, venv, and git segments" {
    local venv_dir="$TEST_TMPDIR/.venv"
    local mockbin="$TEST_TMPDIR/mockbin"

    mkdir -p "$venv_dir" "$mockbin"
    cat > "$mockbin/scutil" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--get" && "${2:-}" == "ComputerName" ]]; then
    printf '%s\n' "aadhara"
    exit 0
fi
if [[ "${1:-}" == "--get" && "${2:-}" == "LocalHostName" ]]; then
    printf '%s\n' "aadhara-local"
    exit 0
fi
exit 1
EOF
    chmod +x "$mockbin/scutil"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        VIRTUAL_ENV="$venv_dir" \
        PATH="$mockbin:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "PS1=%s\n" "$PS1"; \
            printf "host=%s\n" "$(_base_runtime_host_prompt)"; \
            printf "venv=%s\n" "$(_base_runtime_venv_prompt)"; \
            cd "$BASE_HOME"; \
            printf "git=%s\n" "$(_base_runtime_git_prompt)"; \
            printf "disable=%s\n" "${VIRTUAL_ENV_DISABLE_PROMPT:-}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *'PS1=\T $(_base_runtime_host_prompt) $(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
    [[ "$output" == *"host=aadhara"* ]]
    [[ "$output" == *"venv=[.venv] "* ]]
    [[ "$output" == *"git=("* ]]
    [[ "$output" == *"disable=1"* ]]
}


@test "Base runtime shell loads base_init before user bashrc and owns final prompt" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
alias user_bashrc_alias='printf user-bashrc'
export USER_BASHRC_LOADED=1
if declare -F import_base_lib >/dev/null 2>&1; then
    export USER_BASHRC_HAS_BASE_IMPORT=1
fi
PS1='user prompt: '
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            alias user_bashrc_alias; \
            printf "USER_BASHRC_LOADED=%s\n" "${USER_BASHRC_LOADED:-}"; \
            printf "USER_BASHRC_HAS_BASE_IMPORT=%s\n" "${USER_BASHRC_HAS_BASE_IMPORT:-}"; \
            printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"alias user_bashrc_alias='printf user-bashrc'"* ]]
    [[ "$output" == *"USER_BASHRC_LOADED=1"* ]]
    [[ "$output" == *"USER_BASHRC_HAS_BASE_IMPORT=1"* ]]
    [[ "$output" == *'PS1=\T $(_base_runtime_host_prompt) $(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
}

@test "BASE_DEBUG traces Base runtime shell startup" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
export USER_BASHRC_LOADED=1
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_DEBUG=1 \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "ok\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: loading"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$BASE_REPO_ROOT/base_init.sh'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$TEST_HOME/.bashrc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: complete"* ]]
}


@test "baserc can enable BASE_DEBUG for Base runtime shells" {
    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"

    run env -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "ok\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: loading"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: complete"* ]]
}

@test "baserc cannot override BASE_HOME for Base runtime shells" {
    printf '%s\n' 'BASE_HOME=/tmp/not-base' > "$TEST_HOME/.baserc"

    run env -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "BASE_HOME=%s\n" "$BASE_HOME"; printf "BASE_BIN_DIR=%s\n" "${BASE_BIN_DIR-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"ERROR: ~/.baserc must not set Base-owned variable 'BASE_HOME'."* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"BASE_BIN_DIR=unset"* ]]
}
