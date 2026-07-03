#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl projects list discovers manifests in a workspace" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base" "$workspace/demo" "$workspace/notes"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" && "${4:-}" == "--workspace" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT" > "${BASE_TEST_PROJECTS_LIST_STATE:?}"
    printf '%s\t%s\n' base "$5/base"
    printf '%s\t%s\n' demo "$5/demo"
    exit 0
fi
printf 'unexpected projects list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECTS_LIST_STATE="$TEST_TMPDIR/projects-list-state" \
        "$BASE_REPO_ROOT/bin/basectl" projects list --workspace "$workspace"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'base\t'"$workspace/base"* ]]
    [[ "$output" == *$'demo\t'"$workspace/demo"* ]]
    [ "$(cat "$TEST_TMPDIR/projects-list-state")" = "BASE_PROJECT=base" ]
}

@test "basectl projects list forwards json format option" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_TEST_PROJECTS_LIST_STATE:?}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" ]]; then
    printf '[{"name":"base","path":"%s"}]\n' "${BASE_TEST_WORKSPACE:?}/base"
    exit 0
fi
printf 'unexpected projects list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECTS_LIST_STATE="$TEST_TMPDIR/projects-list-state" \
        BASE_TEST_WORKSPACE="$workspace" \
        "$BASE_REPO_ROOT/bin/basectl" projects list --workspace "$workspace" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "[{\"name\":\"base\",\"path\":\"$workspace/base\"}]" ]
    [ "$(cat "$TEST_TMPDIR/projects-list-state")" = "-m base_projects list --workspace $workspace --format json" ]
}

@test "basectl projects list falls back to source python before setup" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/projects-list-state"

    mkdir -p "$workspace/base" "$workspace/demo"
    cat > "$TEST_MOCKBIN/python3" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-c" ]]; then
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" && "${4:-}" == "--workspace" ]]; then
    {
        printf 'BASE_PROJECT=%s\n' "${BASE_PROJECT:-}"
        printf 'PYTHONPATH=%s\n' "${PYTHONPATH:-}"
        printf 'ARGS=%s\n' "$*"
    } > "${BASE_TEST_PROJECTS_LIST_STATE:?}"
    printf '%s\t%s\n' base "$5/base"
    printf '%s\t%s\n' demo "$5/demo"
    exit 0
fi
printf 'unexpected source python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/python3"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECTS_LIST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" projects list --workspace "$workspace"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'base\t'"$workspace/base"* ]]
    [[ "$output" == *$'demo\t'"$workspace/demo"* ]]
    grep -Fqx "BASE_PROJECT=base" "$state_file"
    grep -Fqx "PYTHONPATH=$BASE_REPO_ROOT/lib/python:$BASE_REPO_ROOT/cli/python" "$state_file"
    grep -Fqx "ARGS=-m base_projects list --workspace $workspace" "$state_file"
}

@test "basectl projects list reports a targeted pre-setup diagnostic without source python dependencies" {
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$workspace/base"
    cat > "$TEST_MOCKBIN/python3" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-c" ]]; then
    exit 1
fi
printf 'unexpected source python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/python3"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" projects list --workspace "$workspace"

    [ "$status" -eq 1 ]
    [[ "$output" == *"basectl projects list needs either the Base project virtualenv or a Python 3 with Click and PyYAML available."* ]]
    [[ "$output" == *"Run 'basectl setup' to create the Base project virtualenv."* ]]
    [[ "$output" != *"Project virtual environment Python was not found"* ]]
}

@test "basectl projects list prints help without requiring the Base Python venv" {
    run_basectl projects list --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl projects list [options]"* ]]
    [[ "$output" == *"--format <format>"* ]]
}

@test "basectl projects reports unknown command as a usage error" {
    run_basectl projects unknown

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Unknown projects command 'unknown'."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}

@test "basectl projects list reports invalid format as a usage error" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" ]]; then
    printf 'ERROR: Unsupported output format '\''xml'\''. Expected one of: text, json.\n' >&2
    exit 2
fi
printf 'unexpected projects list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl projects list --format xml

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported output format 'xml'"* ]]
    [[ "$output" != *"Traceback"* ]]
}
