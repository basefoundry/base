#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl build prints help" {
    run_basectl build --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl build [project] [target...]"* ]]
    [[ "$output" == *"--project <name>"* ]]
    [[ "$output" == *"--format <format>"* ]]
}

@test "basectl build reports invalid arguments as usage errors" {
    run_basectl build --workspace
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an argument."* ]]

    run_basectl build --project
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--project' requires an argument."* ]]

    run_basectl build --format json
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--format' requires --list."* ]]

    run_basectl build --unknown demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown build option '--unknown'."* ]]
}

@test "basectl build runs default targets from target working directories" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/build-state"

    mkdir -p "$(dirname "$python_bin")" \
        "$workspace/demo/services/api" \
        "$workspace/demo/services/worker" \
        "$workspace/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin build-target 2
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" \
        'printf "api:%s:%s:%s:%s:%s\n" "$BASE_PROJECT" "$BASE_PROJECT_ROOT" "$BASE_PROJECT_MANIFEST" "$BASE_PROJECT_VENV_DIR" "$PWD" >> "$BASE_TEST_BUILD_STATE"' 'Build API' ""
    base_test_protocol_build_target_record 1 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false worker \
        "${BASE_TEST_PROJECT_ROOT:?}/services/worker" \
        'printf "worker:%s:%s\n" "$BASE_PROJECT" "$PWD" >> "$BASE_TEST_BUILD_STATE"' 'Build worker' ""
    base_test_protocol_end
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    touch "$workspace/demo/.venv/bin/go"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_BUILD_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo

    [ "$status" -eq 0 ]
    [[ "$(cat "$state_file")" == *"api:demo:$workspace/demo:$workspace/demo/base_manifest.yaml:$workspace/demo/.venv:$workspace/demo/services/api"* ]]
    [[ "$(cat "$state_file")" == *"worker:demo:$workspace/demo/services/worker"* ]]
}

@test "basectl build routes uv runner targets through uv" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/build-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api" "$workspace/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'python -m build' 'Build API' uv
    base_test_protocol_end
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$workspace/demo/.venv/bin/uv" <<'EOF'
#!/usr/bin/env bash
{
    printf 'pwd=%s\n' "$PWD"
    printf 'args='
    printf '<%s>' "$@"
    printf '\n'
} > "${BASE_TEST_BUILD_STATE:?}"
EOF
    chmod +x "$python_bin" "$workspace/demo/.venv/bin/uv"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_BUILD_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo -- --wheel

    [ "$status" -eq 0 ]
    [[ "$(cat "$state_file")" == *"pwd=$workspace/demo/services/api"* ]]
    [[ "$(cat "$state_file")" == *"args=<run><--><python><-m><build><--wheel>"* ]]
}

@test "basectl build passes explicit targets and extra args" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/build-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api" "$workspace/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" && "${5:-}" == "api" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'fake-build ./cmd/api' 'Build API' ""
    base_test_protocol_end
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$workspace/demo/.venv/bin/fake-build" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_TEST_BUILD_STATE:?}"
EOF
    chmod +x "$python_bin" "$workspace/demo/.venv/bin/fake-build"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_BUILD_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo api -- --release "name with spaces"

    [ "$status" -eq 0 ]
    [ "$(cat "$state_file")" = $'./cmd/api\n--release\nname with spaces' ]
}

@test "basectl build dry-run prints resolved targets without running them" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/build-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'touch "$BASE_TEST_BUILD_STATE"; exit 7' 'Build API' ""
    base_test_protocol_end
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_BUILD_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo --dry-run -- --release

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would build target api for project demo"* ]]
    [[ "$output" == *'touch "$BASE_TEST_BUILD_STATE"; exit 7 --release'* ]]
    [ ! -e "$state_file" ]
}

@test "basectl build preserves delegated command failures without reporting protocol errors" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api" "$workspace/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'printf "build failed\n" >&2; exit 23' 'Build API' ""
    base_test_protocol_end
    exit 0
fi
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" build demo

    [ "$status" -eq 23 ]
    [[ "$output" == *"build failed"* ]]
    [[ "$output" != *"Invalid Base command protocol"* ]]
    [[ "$output" != *"Unable to parse build targets"* ]]
}

@test "basectl build --list prints project build targets" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-target-list" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'go build ./cmd/api' 'Build API' ""
    base_test_protocol_end
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" build demo --list

    [ "$status" -eq 0 ]
    [[ "$output" == *$'demo\tapi\t'* ]]
    [[ "$output" == *$'\tBuild API\t'* ]]
}

@test "basectl build --list shows runner without wrapping target descriptions" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-target-list" && "${4:-}" == "demo" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'python -m build' 'Build API' uv
    base_test_protocol_end
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" build demo --list

    [ "$status" -eq 0 ]
    [[ "$output" == *$'demo\tapi\t'* ]]
    [[ "$output" == *$'\tBuild API\tuv'* ]]
    [[ "$output" != *"uv run -- Build API"* ]]
}

@test "basectl build resolves current-project targets from a nested directory" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/docs" "$workspace/demo/services/api"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "api" ]]; then
    base_test_protocol_begin build-target 1
    base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
        "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
        "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'printf current-project-build' 'Build API' ""
    base_test_protocol_end
    exit 0
fi
printf 'unexpected current build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env HOME="$TEST_HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        bash -c 'cd "$1" && shift && "$@"' bash "$workspace/demo/docs" \
        "$BASE_REPO_ROOT/bin/basectl" build api --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would build target api for project demo"* ]]
}

@test "basectl build list exposes stable JSON for an explicit project" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local expected='{"schema_version":1,"project":{"name":"demo"},"targets":[{"name":"web app"}]}'

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ " $* " == *" -m base_projects build-target-list --project demo --dry-run --format json "* ]]; then
    printf '%s\n' "${BASE_TEST_EXPECTED_JSON:?}"
    exit 0
fi
printf 'unexpected build JSON args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run env HOME="$TEST_HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_EXPECTED_JSON="$expected" \
        "$BASE_REPO_ROOT/bin/basectl" build --project demo --list --format json

    [ "$status" -eq 0 ]
    [ "$output" = "$expected" ]
}

@test "basectl build reports resolver errors" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" ]]; then
    printf "ERROR: Project 'demo' does not declare build targets in '%s/base_manifest.yaml'.\n" "${BASE_TEST_PROJECT_ROOT:?}" >&2
    exit 1
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" build demo

    [ "$status" -eq 1 ]
    [[ "$output" == *"does not declare build targets"* ]]
}
