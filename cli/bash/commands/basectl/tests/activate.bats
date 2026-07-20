#!/usr/bin/env bats

load ./basectl_helpers.bash


setup_activate_lifecycle_fixture() {
    ACTIVATE_CACHE_ROOT="$TEST_TMPDIR/cache"
    ACTIVATE_HISTORY_STATE="$TEST_TMPDIR/activate-history-state"
    ACTIVATE_SHELL_STATE="$TEST_TMPDIR/activate-shell-state"
    ACTIVATE_SHELL_STATUS="$1"
    ACTIVATE_WORKSPACE="$TEST_TMPDIR/workspace"
    ACTIVATE_BASE_PYTHON="$TEST_HOME/.base.d/base/.venv/bin/python"
    ACTIVATE_PROJECT_PYTHON="$ACTIVATE_WORKSPACE/demo/.venv/bin/python"
    ACTIVATE_SHELL="$TEST_TMPDIR/fake-bash"

    unset \
        BASE_CLI_RUNTIME_OWNER \
        BASE_CLI_RUN_ID \
        BASE_CLI_RUN_ROOT \
        BASE_CLI_PRIMARY_LOG \
        BASE_CLI_HISTORY_PARENT_RUN_ID \
        BASE_CLI_HISTORY_STARTED_AT \
        BASE_CLI_HISTORY_SCOPE \
        BASE_CLI_HISTORY_PROJECT \
        BASE_CLI_HISTORY_PROJECT_ROOT \
        BASE_CLI_HISTORY_MANIFEST \
        BASE_CLI_PROJECT_NAME \
        BASE_CLI_PROJECT_ROOT \
        BASE_CLI_PROJECT_MANIFEST

    mkdir -p "$(dirname "$ACTIVATE_BASE_PYTHON")" "$(dirname "$ACTIVATE_PROJECT_PYTHON")" \
        "$ACTIVATE_WORKSPACE/demo"
    cat > "$ACTIVATE_BASE_PYTHON" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_history.record" ]]; then
    printf '%s\n' "$*" >> "${BASE_TEST_ACTIVATE_HISTORY_STATE:?}"
    exit 0
fi
printf 'unexpected activate lifecycle python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$ACTIVATE_BASE_PYTHON" "$ACTIVATE_PROJECT_PYTHON"
    cat > "$ACTIVATE_SHELL" <<'EOF'
#!/usr/bin/env bash
grep -Fq '"status":"running"' "${BASE_CLI_RUN_ROOT:?}/run.json" || exit 97
[[ ! -s "${BASE_TEST_ACTIVATE_HISTORY_STATE:?}" ]] || exit 98
"$BASH" -c 'trap "exit 42" INT; kill -s INT "$$"; exit 99'
[[ $? -eq 42 ]] || exit 99
{
    printf 'run-status=running\n'
    printf 'history-before-exit=absent\n'
    printf 'int-disposition=catchable\n'
} > "${BASE_TEST_ACTIVATE_SHELL_STATE:?}"

exit "$BASE_TEST_ACTIVATE_SHELL_STATUS"
EOF
    chmod +x "$ACTIVATE_BASE_PYTHON" "$ACTIVATE_PROJECT_PYTHON" "$ACTIVATE_SHELL"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$ACTIVATE_WORKSPACE/demo/base_manifest.yaml"
    ACTIVATE_WORKSPACE="$(cd "$ACTIVATE_WORKSPACE" && pwd -P)"
}


@test "basectl activate resolves a project and launches a project subshell" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local project_python="$workspace/demo/.venv/bin/python"
    local project_activate="$workspace/demo/.venv/bin/activate"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'args=%s\n' "$*"
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'BASE_PROJECT_MANIFEST=%s\n' "$BASE_PROJECT_MANIFEST"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
printf 'PWD=%s\n' "$PWD"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$workspace/demo/.venv" > "$project_activate"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" != *"BASE_SHELL: readonly variable"* ]]
    [[ "$output" == *"args=--rcfile $BASE_REPO_ROOT/lib/bash/runtime/bashrc"* ]]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/demo"* ]]
    [[ "$output" == *"BASE_PROJECT_MANIFEST=$workspace/demo/base_manifest.yaml"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$workspace/demo/.venv"* ]]
    [[ "$output" == *"PWD=$workspace/demo"* ]]
}

@test "basectl activate finalizes a successful runtime shell and records primary project history" {
    local run_root run_id run_json history_call

    setup_activate_lifecycle_fixture 0

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_CACHE_DIR="$ACTIVATE_CACHE_ROOT" \
        BASE_ACTIVATE_SHELL="$ACTIVATE_SHELL" \
        BASE_TEST_ACTIVATE_HISTORY_STATE="$ACTIVATE_HISTORY_STATE" \
        BASE_TEST_ACTIVATE_SHELL_STATE="$ACTIVATE_SHELL_STATE" \
        BASE_TEST_ACTIVATE_SHELL_STATUS="$ACTIVATE_SHELL_STATUS" \
        BASE_TEST_PROJECT_ROOT="$ACTIVATE_WORKSPACE/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    grep -Fqx "run-status=running" "$ACTIVATE_SHELL_STATE"
    grep -Fqx "history-before-exit=absent" "$ACTIVATE_SHELL_STATE"
    grep -Fqx "int-disposition=catchable" "$ACTIVATE_SHELL_STATE"
    run_root="$(find "$ACTIVATE_CACHE_ROOT/base/runs" -mindepth 1 -maxdepth 1 -type d -print -quit)"
    [ -n "$run_root" ]
    run_id="$(basename -- "$run_root")"
    run_id="${run_id%%__*}"
    run_json="$(cat "$run_root/run.json")"
    [[ "$run_json" == *'"status":"ok"'* ]]
    [[ "$run_json" == *'"exit_code":0'* ]]
    [ -f "$ACTIVATE_HISTORY_STATE" ]
    [ "$(wc -l < "$ACTIVATE_HISTORY_STATE")" -eq 1 ]
    history_call="$(cat "$ACTIVATE_HISTORY_STATE")"
    [[ "$history_call" == *"-m base_history.record --command activate "* ]]
    [[ "$history_call" == *" --run-id $run_id "* ]]
    [[ "$history_call" == *" --exit-code 0 --scope primary --owner base "* ]]
    [[ "$history_call" == *" --bundle-path $run_root "* ]]
    [[ "$history_call" == *" --project demo --project-root $ACTIVATE_WORKSPACE/demo "* ]]
    [[ "$history_call" == *" --manifest $ACTIVATE_WORKSPACE/demo/base_manifest.yaml "* ]]
    [[ "$history_call" == *" -- basectl activate demo" ]]
}

@test "basectl activate propagates and records a failed runtime shell exit" {
    local run_root run_id run_json history_call

    setup_activate_lifecycle_fixture 23

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_CACHE_DIR="$ACTIVATE_CACHE_ROOT" \
        BASE_ACTIVATE_SHELL="$ACTIVATE_SHELL" \
        BASE_TEST_ACTIVATE_HISTORY_STATE="$ACTIVATE_HISTORY_STATE" \
        BASE_TEST_ACTIVATE_SHELL_STATE="$ACTIVATE_SHELL_STATE" \
        BASE_TEST_ACTIVATE_SHELL_STATUS="$ACTIVATE_SHELL_STATUS" \
        BASE_TEST_PROJECT_ROOT="$ACTIVATE_WORKSPACE/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 23 ]
    grep -Fqx "run-status=running" "$ACTIVATE_SHELL_STATE"
    grep -Fqx "history-before-exit=absent" "$ACTIVATE_SHELL_STATE"
    grep -Fqx "int-disposition=catchable" "$ACTIVATE_SHELL_STATE"
    run_root="$(find "$ACTIVATE_CACHE_ROOT/base/runs" -mindepth 1 -maxdepth 1 -type d -print -quit)"
    [ -n "$run_root" ]
    run_id="$(basename -- "$run_root")"
    run_id="${run_id%%__*}"
    run_json="$(cat "$run_root/run.json")"
    [[ "$run_json" == *'"status":"error"'* ]]
    [[ "$run_json" == *'"exit_code":23'* ]]
    [ -f "$ACTIVATE_HISTORY_STATE" ]
    [ "$(wc -l < "$ACTIVATE_HISTORY_STATE")" -eq 1 ]
    history_call="$(cat "$ACTIVATE_HISTORY_STATE")"
    [[ "$history_call" == *"-m base_history.record --command activate "* ]]
    [[ "$history_call" == *" --run-id $run_id "* ]]
    [[ "$history_call" == *" --exit-code 23 --scope primary --owner base "* ]]
    [[ "$history_call" == *" --bundle-path $run_root "* ]]
    [[ "$history_call" == *" --project demo --project-root $ACTIVATE_WORKSPACE/demo "* ]]
    [[ "$history_call" == *" --manifest $ACTIVATE_WORKSPACE/demo/base_manifest.yaml "* ]]
    [[ "$history_call" == *" -- basectl activate demo" ]]
}

@test "basectl activate honors BASE_PROJECT_VENV_DIR override" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_python="$TEST_TMPDIR/custom-venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_PROJECT_VENV_DIR="$TEST_TMPDIR/custom-venv" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$TEST_TMPDIR/custom-venv"* ]]
}

@test "basectl activate prefers uv project .venv when python manager is uv" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$workspace/demo/.venv/bin"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" true false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
EOF
    printf '#!/usr/bin/env bash\n' > "$workspace/demo/.venv/bin/python"
    chmod +x "$base_python" "$workspace/demo/.venv/bin/python" "$fake_bash"
    printf 'project:\n  name: demo\npython:\n  manager: uv\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    printf '[project]\nname = "demo"\n' > "$workspace/demo/pyproject.toml"
    printf 'version = 1\n' > "$workspace/demo/uv.lock"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$workspace/demo/.venv"* ]]
}

@test "basectl activate uses project .venv without python manager uv" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local project_python="$workspace/demo/.venv/bin/python"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo/.venv/bin"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    printf '#!/usr/bin/env bash\n' > "$workspace/demo/.venv/bin/python"
    chmod +x "$base_python" "$project_python" "$workspace/demo/.venv/bin/python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    printf '[project]\nname = "demo"\n' > "$workspace/demo/pyproject.toml"
    printf 'version = 1\n' > "$workspace/demo/uv.lock"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$workspace/demo/.venv"* ]]
}

@test "basectl activate guides uv projects to create the uv environment" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$base_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" true false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$base_python"
    printf 'project:\n  name: demo\npython:\n  manager: uv\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    printf '[project]\nname = "demo"\n' > "$workspace/demo/pyproject.toml"
    printf 'version = 1\n' > "$workspace/demo/uv.lock"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -ne 0 ]
    [[ "$output" == *"Project virtual environment Python was not found at '$workspace/demo/.venv/bin/python'."* ]]
    [[ "$output" == *"Run 'uv sync' in '$workspace/demo' first."* ]]
    [[ "$output" != *"Run 'basectl setup demo' first."* ]]
}

@test "basectl default runtime shell preserves caller working directory" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_activate="$TEST_HOME/.base.d/base/.venv/bin/activate"
    local workspace="$TEST_TMPDIR/workspace"
    local caller="$TEST_TMPDIR/caller"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$workspace/base" "$caller"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "base" ]]; then
    base_test_protocol_project_route base "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${HOME:?}/.base.d/base/.venv" false false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'PWD=%s\n' "$PWD"
EOF
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$TEST_HOME/.base.d/base/.venv" > "$project_activate"
    chmod +x "$base_python" "$fake_bash"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"
    caller="$(cd "$caller" && pwd -P)"

    run bash -c 'cd "$1" || exit 1; shift; exec "$@"' _ "$caller" \
        env \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            BASE_ACTIVATE_PRESERVE_CWD=1 \
            BASE_ACTIVATE_SHELL="$fake_bash" \
            BASE_TEST_PROJECT_ROOT="$workspace/base" \
            "$BASE_REPO_ROOT/bin/basectl" activate base

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/base"* ]]
    [[ "$output" == *"PWD=$caller"* ]]
}

@test "basectl activate --no-cd preserves caller working directory" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local project_python="$workspace/demo/.venv/bin/python"
    local project_activate="$workspace/demo/.venv/bin/activate"
    local caller="$TEST_TMPDIR/caller"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo" "$caller"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'PWD=%s\n' "$PWD"
EOF
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$workspace/demo/.venv" > "$project_activate"
    printf '#!/usr/bin/env bash\n' > "$project_python"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"
    caller="$(cd "$caller" && pwd -P)"

    run bash -c 'cd "$1" || exit 1; shift; exec "$@"' _ "$caller" \
        env \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            BASE_ACTIVATE_SHELL="$fake_bash" \
            BASE_TEST_PROJECT_ROOT="$workspace/demo" \
            "$BASE_REPO_ROOT/bin/basectl" activate demo --no-cd

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/demo"* ]]
    [[ "$output" == *"PWD=$caller"* ]]
}

@test "basectl activate prints help without requiring the Base Python venv" {
    run_basectl activate --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl activate <project> [options]"* ]]
    [[ "$output" == *"--no-cd"* ]]
    [[ "$output" == *"interactive Base Bash runtime shell"* ]]
}

@test "basectl activate rejects non-Bash BASE_ACTIVATE_SHELL before launch" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local project_python="$workspace/demo/.venv/bin/python"
    local project_activate="$workspace/demo/.venv/bin/activate"
    local fake_zsh="$TEST_TMPDIR/zsh"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_zsh" <<'EOF'
#!/usr/bin/env bash
printf 'non-bash shell invoked\n'
exit 99
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$workspace/demo/.venv" > "$project_activate"
    chmod +x "$base_python" "$project_python" "$fake_zsh"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_zsh" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -ne 0 ]
    [[ "$output" == *"BASE_ACTIVATE_SHELL"* ]]
    [[ "$output" == *"requires Bash"* ]]
    [[ "$output" != *"non-bash shell invoked"* ]]
}

@test "basectl activate reports missing project as a usage error" {
    run_basectl activate

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Project name is required."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}

@test "basectl activate reports invalid arguments as usage errors" {
    run_basectl activate --workspace
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl activate --unknown demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown activate option '--unknown'."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl activate demo extra
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: The 'activate' command accepts exactly one project name."* ]]
    [[ "$output" != *"FATAL"* ]]
}
