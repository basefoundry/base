#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.bash

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
    ! grep -Fqx '  version' <<<"$output"
    [[ "$output" != *"-b DIR"* ]]
    [[ "$output" != *"Force install"* ]]
    [[ "$output" != *"-V"* ]]
}

@test "basectl prints help when no command is given in a non-interactive shell" {
    run_basectl

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
}

@test "basectl rejects removed version option" {
    run_basectl --version

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown option '--version'"* ]]
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

    for legacy_command in status update run set-team set-shared-teams man embrace install version; do
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
        "$base_home/cli/bash/commands/basectl"
    touch \
        "$base_home/base_init.sh" \
        "$base_home/lib/shell/bash_profile" \
        "$base_home/lib/shell/bashrc" \
        "$base_home/lib/bash/runtime/bashrc" \
        "$base_home/bin/basectl" \
        "$base_home/cli/bash/commands/basectl/basectl.sh"

    run bash -c 'source "$1"; basectl_verify_home "$2"' _ \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$base_home"

    [ "$status" -eq 0 ]
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


@test "Base runtime shell sources user bashrc before setting prompt" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
alias user_bashrc_alias='printf user-bashrc'
export USER_BASHRC_LOADED=1
PS1='user prompt: '
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            alias user_bashrc_alias; \
            printf "USER_BASHRC_LOADED=%s\n" "${USER_BASHRC_LOADED:-}"; \
            printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"alias user_bashrc_alias='printf user-bashrc'"* ]]
    [[ "$output" == *"USER_BASHRC_LOADED=1"* ]]
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
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$TEST_HOME/.bashrc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$BASE_REPO_ROOT/base_init.sh'"* ]]
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
