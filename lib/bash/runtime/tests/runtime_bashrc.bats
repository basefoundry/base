#!/usr/bin/env bats

load ../../tests/test_helper.sh

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

@test "non-interactive bash ignores runtime rcfile" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
touch "$HOME/user-bashrc-ran"
EOF

    run env -i \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -c '\
            printf "BASE_SHELL=%s\n" "${BASE_SHELL:-}"; \
            if [[ -f "$HOME/user-bashrc-ran" ]]; then \
                printf "USER_BASHRC_RAN=1\n"; \
            else \
                printf "USER_BASHRC_RAN=0\n"; \
            fi'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_SHELL="* ]]
    [[ "$output" == *"USER_BASHRC_RAN=0"* ]]
}

@test "runtime bashrc sources base_init before user bashrc" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
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
            printf "USER_BASHRC_HAS_BASE_IMPORT=%s\n" "${USER_BASHRC_HAS_BASE_IMPORT:-}"; \
            printf "BASE_SHELL=%s\n" "${BASE_SHELL:-}"; \
            printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"USER_BASHRC_HAS_BASE_IMPORT=1"* ]]
    [[ "$output" == *"BASE_SHELL=1"* ]]
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
}

@test "runtime bashrc can source user bashrc with Base-managed snippet after readonly BASE_HOME" {
    cat > "$TEST_HOME/.bashrc" <<EOF
source "$BASE_REPO_ROOT/lib/shell/bashrc"
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            command -v basectl; \
            printf "BASE_HOME=%s\n" "$BASE_HOME"; \
            declare -p BASE_HOME'

    [ "$status" -eq 0 ]
    [[ "$output" == *"$BASE_REPO_ROOT/bin/basectl"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"declare -rx BASE_HOME=\"$BASE_REPO_ROOT\""* ]]
}

@test "runtime bashrc sources baserc debug preferences" {
    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"

    run env -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "ok\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: complete"* ]]
}

@test "runtime bashrc handles a missing baserc without error" {
    run env -i \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "BASE_SHELL=%s\n" "${BASE_SHELL:-}"; \
            printf "BASE_DEBUG=%s\n" "${BASE_DEBUG:-}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_SHELL=1"* ]]
    [[ "$output" == *"BASE_DEBUG="* ]]
    [[ "$output" != *"ERROR:"* ]]
}

@test "baserc debug setting enables full runtime trace" {
    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"

    run env -i \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "ok\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: loading"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$BASE_REPO_ROOT/base_init.sh'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: complete"* ]]
}

@test "runtime bashrc is idempotent when sourced twice" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
count_file="$HOME/user-bashrc-count"
count=0
if [[ -f "$count_file" ]]; then
    count="$(cat "$count_file")"
fi
printf '%s\n' "$((count + 1))" > "$count_file"
EOF
    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"

    run env -i \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            source "$BASE_HOME/lib/bash/runtime/bashrc"; \
            printf "USER_BASHRC_COUNT=%s\n" "$(cat "$HOME/user-bashrc-count")"; \
            printf "BASE_SHELL=%s\n" "${BASE_SHELL:-}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: already loaded; skipping"* ]]
    [[ "$output" == *"USER_BASHRC_COUNT=1"* ]]
    [[ "$output" == *"BASE_SHELL=1"* ]]
}
