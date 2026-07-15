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
    local path_with_platform
    local path_without_platform
    local workspace_root

    workspace_root="$(cd "$BASE_REPO_ROOT/.." && pwd -P)"
    path_without_platform="PATH=$venv_dir/bin:$BASE_REPO_ROOT/bin:$project_root/bin:"
    path_with_platform="PATH=$venv_dir/bin:$BASE_REPO_ROOT/bin:$workspace_root/base-platform-tools/bin:$project_root/bin:"
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
    [[ "$output" == *"$path_without_platform"* || "$output" == *"$path_with_platform"* ]]
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
}

@test "Base runtime shell marks project metadata readonly" {
    local project_root="$TEST_TMPDIR/demo"
    local venv_dir="$TEST_TMPDIR/demo-venv"

    mkdir -p "$project_root" "$venv_dir/bin"
    touch "$project_root/base_manifest.yaml"
    cat > "$venv_dir/bin/activate" <<'EOF'
VIRTUAL_ENV="$BASE_PROJECT_VENV_DIR"
export VIRTUAL_ENV
EOF
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "activation-sources" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin activation-source 0
    base_test_protocol_end
    exit 0
fi
printf 'unexpected base_projects args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$venv_dir/bin/python"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        BASE_PROJECT_MANIFEST="$project_root/base_manifest.yaml" \
        BASE_PROJECT_VENV_DIR="$venv_dir" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            declare -p BASE_PROJECT; \
            declare -p BASE_PROJECT_ROOT; \
            declare -p BASE_PROJECT_MANIFEST; \
            declare -p BASE_PROJECT_VENV_DIR'

    [ "$status" -eq 0 ]
    [[ "$output" == *'declare -rx BASE_PROJECT="demo"'* ]]
    [[ "$output" == *"declare -rx BASE_PROJECT_ROOT=\"$project_root\""* ]]
    [[ "$output" == *"declare -rx BASE_PROJECT_MANIFEST=\"$project_root/base_manifest.yaml\""* ]]
    [[ "$output" == *"declare -rx BASE_PROJECT_VENV_DIR=\"$venv_dir\""* ]]
}

@test "Base runtime shell sources manifest-declared project activation scripts" {
    local project_root="$TEST_TMPDIR/demo"
    local venv_dir="$TEST_TMPDIR/demo-venv"
    local activation_script="$project_root/.base/activate.sh"

    mkdir -p "$project_root/.base" "$venv_dir/bin"
    cat > "$venv_dir/bin/activate" <<'EOF'
VIRTUAL_ENV="$BASE_PROJECT_VENV_DIR"
export VIRTUAL_ENV
EOF
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "activation-sources" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin activation-source 1
    base_test_protocol_activation_source_record 0 "${BASE_TEST_ACTIVATION_SOURCE:?}"
    base_test_protocol_end
    exit 0
fi
printf 'unexpected base_projects args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$activation_script" <<'EOF'
export PROJECT_ACTIVATION_PROJECT="$BASE_PROJECT"
export PROJECT_ACTIVATION_VENV="$VIRTUAL_ENV"
project_activation_function() {
    printf '%s:%s\n' "$PROJECT_ACTIVATION_PROJECT" "$PROJECT_ACTIVATION_VENV"
}
EOF
    chmod +x "$venv_dir/bin/python"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        BASE_PROJECT_MANIFEST="$project_root/base_manifest.yaml" \
        BASE_PROJECT_VENV_DIR="$venv_dir" \
        BASE_TEST_ACTIVATION_SOURCE="$activation_script" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "PROJECT_ACTIVATION_PROJECT=%s\n" "${PROJECT_ACTIVATION_PROJECT:-}"; \
            printf "PROJECT_ACTIVATION_VENV=%s\n" "${PROJECT_ACTIVATION_VENV:-}"; \
            project_activation_function'

    [ "$status" -eq 0 ]
    [[ "$output" == *"INFO: Sourcing project activation script '$activation_script'."* ]]
    [[ "$output" == *"PROJECT_ACTIVATION_PROJECT=demo"* ]]
    [[ "$output" == *"PROJECT_ACTIVATION_VENV=$venv_dir"* ]]
    [[ "$output" == *"demo:$venv_dir"* ]]
}

@test "Base runtime shell reports activation source resolution failures clearly" {
    local project_root="$TEST_TMPDIR/demo"
    local venv_dir="$TEST_TMPDIR/demo-venv"

    mkdir -p "$project_root" "$venv_dir/bin"
    cat > "$venv_dir/bin/activate" <<'EOF'
VIRTUAL_ENV="$BASE_PROJECT_VENV_DIR"
export VIRTUAL_ENV
EOF
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "activation-sources" && "${4:-}" == "demo" ]]; then
    printf 'ERROR: %s: activate.source[1] script %q does not exist.\n' "$BASE_PROJECT_MANIFEST" ".base/missing.sh" >&2
    exit 1
fi
printf 'unexpected base_projects args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$venv_dir/bin/python"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        BASE_PROJECT_MANIFEST="$project_root/base_manifest.yaml" \
        BASE_PROJECT_VENV_DIR="$venv_dir" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "shell-continued\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"activate.source[1]"* ]]
    [[ "$output" == *".base/missing.sh"* ]]
    [[ "$output" == *"ERROR: Unable to resolve project activation scripts for 'demo'."* ]]
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
