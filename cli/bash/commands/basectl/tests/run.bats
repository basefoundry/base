#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl run runs declared project command from project root" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/run-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-command" && "${4:-}" == "demo" && "${5:-}" == "dev" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'printf "project=%s\nroot=%s\nmanifest=%s\nvenv=%s\npwd=%s\npath=%s\n" "$BASE_PROJECT" "$BASE_PROJECT_ROOT" "$BASE_PROJECT_MANIFEST" "$BASE_PROJECT_VENV_DIR" "$PWD" "$PATH" > "$BASE_TEST_RUN_STATE"; exit 7'
    exit 0
fi
printf 'unexpected run python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    touch "$TEST_HOME/.base.d/demo/.venv/bin/uvicorn"
    printf 'project:\n  name: demo\ncommands:\n  dev: uvicorn app:app --reload\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_RUN_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo dev

    [ "$status" -eq 7 ]
    [[ "$(cat "$state_file")" == *"project=demo"* ]]
    [[ "$(cat "$state_file")" == *"root=$workspace/demo"* ]]
    [[ "$(cat "$state_file")" == *"manifest=$workspace/demo/base_manifest.yaml"* ]]
    [[ "$(cat "$state_file")" == *"venv=$TEST_HOME/.base.d/demo/.venv"* ]]
    [[ "$(cat "$state_file")" == *"pwd=$workspace/demo"* ]]
    [[ "$(cat "$state_file")" == *"path=$TEST_HOME/.base.d/demo/.venv/bin:"* ]]
}

@test "basectl run dry-run prints resolved command without running it" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/run-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-command" && "${4:-}" == "demo" && "${5:-}" == "dev" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'touch "$BASE_TEST_RUN_STATE"; exit 7'
    exit 0
fi
printf 'unexpected run python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ncommands:\n  dev: uvicorn app:app --reload\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_RUN_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo dev --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run command dev for project demo"* ]]
    [[ "$output" == *'touch "$BASE_TEST_RUN_STATE"; exit 7'* ]]
    [ ! -e "$state_file" ]
}

@test "basectl run passes extra args after separator to command" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/run-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-command" && "${4:-}" == "demo" && "${5:-}" == "lint" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'fake-lint src/'
    exit 0
fi
printf 'unexpected run python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$TEST_HOME/.base.d/demo/.venv/bin/fake-lint" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_TEST_RUN_STATE:?}"
EOF
    chmod +x "$python_bin" "$TEST_HOME/.base.d/demo/.venv/bin/fake-lint"
    printf 'project:\n  name: demo\ncommands:\n  lint: fake-lint src/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_RUN_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo lint -- --fix "name with spaces"

    [ "$status" -eq 0 ]
    [ "$(cat "$state_file")" = $'src/\n--fix\nname with spaces' ]
}

@test "basectl run passes extra args to mise task after separator" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/run-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-command" && "${4:-}" == "demo" && "${5:-}" == "dev" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'mise run dev'
    exit 0
fi
printf 'unexpected run python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$TEST_HOME/.base.d/demo/.venv/bin/mise" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_TEST_RUN_STATE:?}"
EOF
    chmod +x "$python_bin" "$TEST_HOME/.base.d/demo/.venv/bin/mise"
    printf 'project:\n  name: demo\ncommands:\n  dev: mise run dev\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_RUN_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo dev -- --watch

    [ "$status" -eq 0 ]
    [ "$(cat "$state_file")" = $'run\ndev\n--\n--watch' ]
}

@test "basectl run test delegates to the test contract" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-command" && "${4:-}" == "demo" && "${5:-}" == "test" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'printf "test-contract\n"'
    exit 0
fi
printf 'unexpected run python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ntest:\n  command: pytest tests/\ncommands:\n  dev: uvicorn app:app\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" run demo test

    [ "$status" -eq 0 ]
    [[ "$output" == *"test-contract"* ]]
}

@test "basectl run --list prints runnable commands for explicit project" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-commands" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" test 'pytest tests/'
    printf 'demo\t%s\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" dev 'uvicorn app:app --reload'
    exit 0
fi
printf 'unexpected run list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ncommands:\n  dev: uvicorn app:app --reload\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" run demo --list

    [ "$status" -eq 0 ]
    [[ "$output" == *"Commands for project 'demo'"* ]]
    [[ "$output" == *"test"*"pytest tests/"* ]]
    [[ "$output" == *"dev"*"uvicorn app:app --reload"* ]]
}

@test "basectl run --list can resolve nearest project" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "run-commands" && -z "${4:-}" ]]; then
    printf 'demo\t%s\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" dev 'uvicorn app:app --reload'
    exit 0
fi
printf 'unexpected run list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ncommands:\n  dev: uvicorn app:app --reload\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        bash -c '
            cd "$1"
            shift
            "$@"
        ' bash "$workspace/demo" "$BASE_REPO_ROOT/bin/basectl" run --list

    [ "$status" -eq 0 ]
    [[ "$output" == *"Commands for project 'demo'"* ]]
    [[ "$output" == *"dev"*"uvicorn app:app --reload"* ]]
}

@test "basectl run prints help without requiring the Base Python venv" {
    run_basectl run --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl run <project> <command>"* ]]
    [[ "$output" == *"--list"* ]]
    [[ "$output" == *"--dry-run"* ]]
}

@test "basectl run reports invalid arguments as usage errors" {
    run_basectl run
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Project name is required."* ]]

    run_basectl run demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Command name is required."* ]]

    run_basectl run --workspace "$TEST_TMPDIR" --list
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an explicit project name."* ]]

    run_basectl run demo dev --list
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--list' cannot be combined with a command name."* ]]

    run_basectl run --unknown demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown run option '--unknown'."* ]]
}
