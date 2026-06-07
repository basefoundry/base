#!/usr/bin/env bats

load ../../tests/test_helper.sh

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

create_fake_runtime_base() {
    local fake_base="$1"

    mkdir -p "$fake_base/bin" "$fake_base/lib/shell"
    cp "$BASE_REPO_ROOT/lib/shell/baserc_guard.sh" "$fake_base/lib/shell/baserc_guard.sh"
    cp "$BASE_REPO_ROOT/lib/shell/base_platform_tools.sh" "$fake_base/lib/shell/base_platform_tools.sh"
    cat > "$fake_base/bin/basectl" <<'EOF'
#!/usr/bin/env bash
printf 'fake basectl\n'
EOF
    chmod +x "$fake_base/bin/basectl"
    cat > "$fake_base/base_init.sh" <<'EOF'
#!/usr/bin/env bash
[[ -n "${__base_init_sourced__:-}" ]] && return 0
readonly __base_init_sourced__=1
BASE_HOME="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BASE_BIN_DIR="$BASE_HOME/bin"
BASE_LIB_DIR="$BASE_HOME/lib"
BASE_SHELL_DIR="$BASE_HOME/lib/shell"
BASE_SHELL="${BASE_SHELL:-bash}"
export BASE_HOME BASE_BIN_DIR BASE_LIB_DIR BASE_SHELL_DIR BASE_SHELL
readonly BASE_HOME BASE_BIN_DIR BASE_LIB_DIR BASE_SHELL_DIR BASE_SHELL
case ":$PATH:" in
    *:"$BASE_BIN_DIR":*) ;;
    *) PATH="$BASE_BIN_DIR${PATH:+:$PATH}" ;;
esac
export PATH
import_base_lib() {
    return 0
}
EOF
    chmod +x "$fake_base/base_init.sh"
}

create_fake_runtime_platform_tools() {
    local platform_tools_home="$1"

    mkdir -p "$platform_tools_home/bin"
    touch "$platform_tools_home/base_manifest.yaml"
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

@test "runtime bashrc adds optional platform tools between Base and project bins" {
    local workspace="$TEST_TMPDIR/fake-workspace"
    local fake_base="$workspace/base"
    local fake_platform_tools="$workspace/base-platform-tools"
    local project_root="$TEST_TMPDIR/demo"

    create_fake_runtime_base "$fake_base"
    create_fake_runtime_platform_tools "$fake_platform_tools"
    mkdir -p "$project_root/bin"
    fake_base="$(cd "$fake_base" && pwd -P)"
    fake_platform_tools="$(cd "$fake_platform_tools" && pwd -P)"
    project_root="$(cd "$project_root" && pwd -P)"

    run env -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        BASE_HOME="$fake_base" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        PATH="$fake_platform_tools/bin:$fake_base/bin:/usr/bin:/bin:$project_root/bin:$fake_platform_tools/bin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "BASE_PLATFORM_TOOLS_HOME=%s\n" "$BASE_PLATFORM_TOOLS_HOME"; \
            printf "BASE_PLATFORM_TOOLS_BIN_DIR=%s\n" "$BASE_PLATFORM_TOOLS_BIN_DIR"; \
            printf "PATH=%s\n" "$PATH"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_HOME=$fake_platform_tools"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_BIN_DIR=$fake_platform_tools/bin"* ]]
    [[ "$output" == *"PATH=$fake_base/bin:$fake_platform_tools/bin:$project_root/bin:/usr/bin:/bin"* ]]
}

@test "runtime bashrc leaves platform tools unset when sibling repo is absent" {
    local workspace="$TEST_TMPDIR/fake-workspace"
    local fake_base="$workspace/base"
    local project_root="$TEST_TMPDIR/demo"

    create_fake_runtime_base "$fake_base"
    mkdir -p "$project_root/bin"
    fake_base="$(cd "$fake_base" && pwd -P)"
    project_root="$(cd "$project_root" && pwd -P)"

    run env -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        BASE_HOME="$fake_base" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "BASE_PLATFORM_TOOLS_HOME=%s\n" "${BASE_PLATFORM_TOOLS_HOME-unset}"; \
            printf "BASE_PLATFORM_TOOLS_BIN_DIR=%s\n" "${BASE_PLATFORM_TOOLS_BIN_DIR-unset}"; \
            printf "PATH=%s\n" "$PATH"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_HOME=unset"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_BIN_DIR=unset"* ]]
    [[ "$output" == *"PATH=$fake_base/bin:$project_root/bin:/usr/bin:/bin:/usr/sbin:/sbin"* ]]
    [[ "$output" != *"base-platform-tools/bin"* ]]
}
