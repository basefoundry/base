#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl build prints help" {
    run_basectl build --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl build <project> [target...]"* ]]
}

@test "basectl build runs default targets from target working directories" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/build-state"

    mkdir -p "$(dirname "$python_bin")" \
        "$workspace/demo/services/api" \
        "$workspace/demo/services/worker" \
        "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\tapi\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'printf "api:%s:%s:%s:%s:%s\n" "$BASE_PROJECT" "$BASE_PROJECT_ROOT" "$BASE_PROJECT_MANIFEST" "$BASE_PROJECT_VENV_DIR" "$PWD" >> "$BASE_TEST_BUILD_STATE"' 'Build API'
    printf 'demo\t%s\t%s\tworker\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/services/worker" 'printf "worker:%s:%s\n" "$BASE_PROJECT" "$PWD" >> "$BASE_TEST_BUILD_STATE"' 'Build worker'
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    touch "$TEST_HOME/.base.d/demo/.venv/bin/go"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_BUILD_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo

    [ "$status" -eq 0 ]
    [[ "$(cat "$state_file")" == *"api:demo:$workspace/demo:$workspace/demo/base_manifest.yaml:$TEST_HOME/.base.d/demo/.venv:$workspace/demo/services/api"* ]]
    [[ "$(cat "$state_file")" == *"worker:demo:$workspace/demo/services/worker"* ]]
}

@test "basectl build passes explicit targets and extra args" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/build-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-targets" && "${4:-}" == "demo" && "${5:-}" == "api" ]]; then
    printf 'demo\t%s\t%s\tapi\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'fake-build ./cmd/api' 'Build API'
    exit 0
fi
printf 'unexpected build python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$TEST_HOME/.base.d/demo/.venv/bin/fake-build" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_TEST_BUILD_STATE:?}"
EOF
    chmod +x "$python_bin" "$TEST_HOME/.base.d/demo/.venv/bin/fake-build"
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
    printf 'demo\t%s\t%s\tapi\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'touch "$BASE_TEST_BUILD_STATE"; exit 7' 'Build API'
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

@test "basectl build --list prints project build targets" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo/services/api"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "build-target-list" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\tapi\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/services/api" 'go build ./cmd/api' 'Build API'
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
    [[ "$output" == *"Build targets for project 'demo'"* ]]
    [[ "$output" == *"api"* ]]
    [[ "$output" == *"Build API"* ]]
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
