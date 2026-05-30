#!/usr/bin/env bats

load ./basectl_helpers.bash


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
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
    [[ "$output" == *"host=aadhara"* ]]
    [[ "$output" == *"venv=[.venv] "* ]]
    [[ "$output" == *"git=("* ]]
    [[ "$output" == *"disable=1"* ]]
}

@test "Base runtime shell activates project virtual environment" {
    local project_root="$TEST_TMPDIR/demo"
    local venv_dir="$TEST_TMPDIR/demo-venv"

    mkdir -p "$project_root/bin" "$venv_dir/bin"
    cat > "$venv_dir/bin/activate" <<'EOF'
VIRTUAL_ENV="$BASE_PROJECT_VENV_DIR"
PATH="$VIRTUAL_ENV/bin:$PATH"
export VIRTUAL_ENV PATH
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        BASE_PROJECT_VENV_DIR="$venv_dir" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "BASE_PROJECT=%s\n" "$BASE_PROJECT"; \
            printf "VIRTUAL_ENV=%s\n" "$VIRTUAL_ENV"; \
            printf "PATH=%s\n" "$PATH"; \
            printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"VIRTUAL_ENV=$venv_dir"* ]]
    [[ "$output" == *"PATH=$venv_dir/bin:$BASE_REPO_ROOT/bin:$project_root/bin:"* ]]
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
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
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
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
