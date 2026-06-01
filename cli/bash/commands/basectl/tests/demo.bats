#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl demo prints help" {
    run_basectl demo --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl demo <project> [options]"* ]]
}

@test "basectl demo runs declared project demo from project root" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/demo-state"
    local script_path="$workspace/demo/demo/demo.sh"

    mkdir -p "$(dirname "$python_bin")" "$(dirname "$script_path")" "$TEST_HOME/.base.d/demo/.venv/bin"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "demo-script" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/demo/demo.sh"
    exit 0
fi
printf 'unexpected demo python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$script_path" <<'EOF'
#!/usr/bin/env bash
{
    printf 'project=%s\n' "$BASE_PROJECT"
    printf 'root=%s\n' "$BASE_PROJECT_ROOT"
    printf 'manifest=%s\n' "$BASE_PROJECT_MANIFEST"
    printf 'venv=%s\n' "$BASE_PROJECT_VENV_DIR"
    printf 'pwd=%s\n' "$PWD"
    printf 'path=%s\n' "$PATH"
    printf 'args='
    printf '<%s>' "$@"
    printf '\n'
} > "$BASE_TEST_DEMO_STATE"
exit 7
EOF
    chmod +x "$python_bin" "$script_path"
    touch "$TEST_HOME/.base.d/demo/.venv/bin/demo-tool"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_DEMO_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" demo demo -- --non-interactive "name with spaces"

    [ "$status" -eq 7 ]
    [[ "$(cat "$state_file")" == *"project=demo"* ]]
    [[ "$(cat "$state_file")" == *"root=$workspace/demo"* ]]
    [[ "$(cat "$state_file")" == *"manifest=$workspace/demo/base_manifest.yaml"* ]]
    [[ "$(cat "$state_file")" == *"venv=$TEST_HOME/.base.d/demo/.venv"* ]]
    [[ "$(cat "$state_file")" == *"pwd=$workspace/demo"* ]]
    [[ "$(cat "$state_file")" == *"path=$TEST_HOME/.base.d/demo/.venv/bin:"* ]]
    [[ "$(cat "$state_file")" == *"args=<--non-interactive><name with spaces>"* ]]
}

@test "basectl demo dry-run prints resolved script without running it" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/demo-state"
    local script_path="$workspace/demo/demo.sh"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "demo-script" && "${4:-}" == "demo" && "${5:-}" == "--workspace" ]]; then
    printf 'demo\t%s\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/demo.sh"
    exit 0
fi
printf 'unexpected demo python args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$script_path" <<'EOF'
#!/usr/bin/env bash
touch "$BASE_TEST_DEMO_STATE"
EOF
    chmod +x "$python_bin" "$script_path"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_DEMO_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" demo demo --workspace "$workspace" --dry-run -- --non-interactive

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run demo for project demo"* ]]
    [[ "$output" == *"$workspace/demo/demo.sh"* ]]
    [[ "$output" == *"--non-interactive"* ]]
    [ ! -e "$state_file" ]
}

@test "basectl demo reports missing demo declaration" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "demo-script" && "${4:-}" == "demo" ]]; then
    printf "ERROR: No demo declared for project 'demo'. Add demo.script to '%s/base_manifest.yaml'.\n" "${BASE_TEST_PROJECT_ROOT:?}" >&2
    exit 1
fi
printf 'unexpected demo python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" demo demo

    [ "$status" -eq 1 ]
    [[ "$output" == *"No demo declared for project 'demo'"* ]]
}

@test "basectl demo reports invalid demo script from resolver" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "demo-script" && "${4:-}" == "demo" ]]; then
    printf "ERROR: %s/base_manifest.yaml: demo.script './demo.sh' does not exist.\n" "${BASE_TEST_PROJECT_ROOT:?}" >&2
    exit 1
fi
printf 'unexpected demo python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" demo demo

    [ "$status" -eq 1 ]
    [[ "$output" == *"demo.script './demo.sh' does not exist"* ]]
}
