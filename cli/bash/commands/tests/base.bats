#!/usr/bin/env bats

load ../../../../lib/bash/tests/test_helper.bash

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
}

@test "basectl prints help when no command is given in a non-interactive shell" {
    run_basectl

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
}

@test "basectl --version uses BASE_VERSION when provided" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_VERSION="test-version" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 0 ]
    [[ "$output" == "basectl version test-version" ]]
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

    for legacy_command in status update run set-team set-shared-teams man embrace; do
        run_basectl "$legacy_command"
        [ "$status" -eq 2 ]
        [[ "$output" == *"Unrecognized command: $legacy_command"* ]]
    done
}


@test "basectl dispatches command implementations by command name" {
    run_basectl sort-in-place --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Sort text files in place."* ]]
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
