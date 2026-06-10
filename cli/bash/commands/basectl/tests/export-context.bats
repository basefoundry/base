#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl export-context prints help without requiring the Base Python venv" {
    run_basectl export-context --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl export-context [project] [options]"* ]]
    [[ "$output" == *"--format <markdown|zip>"* ]]
    [[ "$output" == *"--list-files"* ]]
}

@test "basectl export-context resolves current project when omitted" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/export-state"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "current" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_export_context" ]]; then
    shift 2
    printf '%s\n' "$*" > "${BASE_TEST_EXPORT_STATE:?}"
    printf 'exported current\n'
    exit 0
fi
printf 'unexpected export-context python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_EXPORT_STATE="$state_file" \
        bash -c '
            cd "$1"
            shift
            "$@"
        ' bash "$workspace/demo" "$BASE_REPO_ROOT/bin/basectl" export-context --print

    [ "$status" -eq 0 ]
    [[ "$output" == *"exported current"* ]]
    [ "$(cat "$state_file")" = "--project-name demo --project-root $workspace/demo --format markdown --print" ]
}

@test "basectl export-context resolves named project and forwards output options" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/export-state"
    local output_path="$TEST_TMPDIR/base-ai-context.zip"

    mkdir -p "$(dirname "$python_bin")" "$workspace/demo"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" && "${5:-}" == "--workspace" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_export_context" ]]; then
    shift 2
    printf '%s\n' "$*" > "${BASE_TEST_EXPORT_STATE:?}"
    printf 'exported named\n'
    exit 0
fi
printf 'unexpected export-context python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_EXPORT_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" export-context demo --workspace "$workspace" --format zip --output "$output_path"

    [ "$status" -eq 0 ]
    [[ "$output" == *"exported named"* ]]
    [ "$(cat "$state_file")" = "--project-name demo --project-root $workspace/demo --format zip --output $output_path" ]
}

@test "basectl export-context reports invalid arguments as usage errors" {
    run_basectl export-context demo extra

    [ "$status" -eq 2 ]
    [[ "$output" == *"basectl export-context [project] [options]"* ]]
    [[ "$output" == *"The 'export-context' command accepts exactly one project name."* ]]
}
