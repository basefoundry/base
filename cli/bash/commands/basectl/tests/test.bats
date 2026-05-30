#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl test runs declared project test command from project root" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/test-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'printf "project=%s\nroot=%s\nmanifest=%s\nvenv=%s\npwd=%s\npath=%s\n" "$BASE_PROJECT" "$BASE_PROJECT_ROOT" "$BASE_PROJECT_MANIFEST" "$BASE_PROJECT_VENV_DIR" "$PWD" "$PATH" > "$BASE_TEST_TEST_STATE"; exit 7'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    touch "$TEST_HOME/.base.d/demo/.venv/bin/pytest"
    printf 'project:\n  name: demo\ntest:\n  command: pytest tests/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TEST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" test demo

    [ "$status" -eq 7 ]
    [[ "$(cat "$state_file")" == *"project=demo"* ]]
    [[ "$(cat "$state_file")" == *"root=$workspace/demo"* ]]
    [[ "$(cat "$state_file")" == *"manifest=$workspace/demo/base_manifest.yaml"* ]]
    [[ "$(cat "$state_file")" == *"venv=$TEST_HOME/.base.d/demo/.venv"* ]]
    [[ "$(cat "$state_file")" == *"pwd=$workspace/demo"* ]]
    [[ "$(cat "$state_file")" == *"path=$TEST_HOME/.base.d/demo/.venv/bin:"* ]]
}

@test "basectl test dry-run prints resolved command without running it" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/test-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'touch "$BASE_TEST_TEST_STATE"; exit 7'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ntest:\n  command: pytest tests/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TEST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" test demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run tests for project demo"* ]]
    [[ "$output" == *'touch "$BASE_TEST_TEST_STATE"; exit 7'* ]]
    [ ! -e "$state_file" ]
}

@test "basectl test passes extra args after separator to command" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/test-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'fake-test tests/'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$TEST_HOME/.base.d/demo/.venv/bin/fake-test" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_TEST_TEST_STATE:?}"
EOF
    chmod +x "$python_bin" "$TEST_HOME/.base.d/demo/.venv/bin/fake-test"
    printf 'project:\n  name: demo\ntest:\n  command: fake-test tests/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TEST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" test demo -- -k "name with spaces" --verbose

    [ "$status" -eq 0 ]
    [ "$(cat "$state_file")" = $'tests/\n-k\nname with spaces\n--verbose' ]
}

@test "basectl test dry-run shows extra args with shell quoting" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'pytest tests/'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ntest:\n  command: pytest tests/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" test demo --dry-run -- -k "name with spaces"

    [ "$status" -eq 0 ]
    [[ "$output" == *"pytest tests/ -k name\\ with\\ spaces"* ]]
}

@test "basectl test passes extra args to mise task after separator" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/test-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'mise run unit'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$TEST_HOME/.base.d/demo/.venv/bin/mise" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_TEST_TEST_STATE:?}"
EOF
    chmod +x "$python_bin" "$TEST_HOME/.base.d/demo/.venv/bin/mise"
    printf 'project:\n  name: demo\ntest:\n  mise: unit\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TEST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" test demo -- -k focused

    [ "$status" -eq 0 ]
    [ "$(cat "$state_file")" = $'run\nunit\n--\n-k\nfocused' ]
}

@test "basectl test warns when project venv is missing" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'printf "ran-test\n"'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ntest:\n  command: pytest tests/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" test demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Project virtual environment was not found at '$TEST_HOME/.base.d/demo/.venv'"* ]]
    [[ "$output" == *"Run 'basectl setup demo' first."* ]]
    [[ "$output" == *"ran-test"* ]]
}

@test "basectl test can resolve the current project when omitted" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "test-command" && -z "${4:-}" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" 'printf "current-project-test\n"'
    exit 0
fi
printf 'unexpected test python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\ntest:\n  command: pytest tests/\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        bash -c '
            cd "$1"
            shift
            "$@"
        ' bash "$workspace/demo" "$BASE_REPO_ROOT/bin/basectl" test

    [ "$status" -eq 0 ]
    [[ "$output" == *"current-project-test"* ]]
}

@test "basectl test prints help without requiring the Base Python venv" {
    run_basectl test --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl test [project] [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--dry-run"* ]]
}

@test "basectl test reports invalid arguments as usage errors" {
    run_basectl test --workspace
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an argument."* ]]

    run_basectl test --workspace "$TEST_TMPDIR"
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an explicit project name."* ]]

    run_basectl test --unknown demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown test option '--unknown'."* ]]

    run_basectl test demo -- --unknown
    [ "$status" -ne 2 ]
    [[ "$output" != *"ERROR: Unknown test option '--unknown'."* ]]
}
