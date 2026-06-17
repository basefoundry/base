#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl workspace status delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local manifest="$TEST_TMPDIR/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    touch "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "status" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT" > "${BASE_TEST_WORKSPACE_STATUS_STATE:?}"
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace status python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_WORKSPACE_STATUS_STATE="$TEST_TMPDIR/workspace-status-state" \
        "$BASE_REPO_ROOT/bin/basectl" workspace status --workspace "$workspace" --manifest "$manifest" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --manifest $manifest --format json" ]
    [ "$(cat "$TEST_TMPDIR/workspace-status-state")" = "BASE_PROJECT=base" ]
}

@test "basectl workspace check delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "check" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace check python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace check --workspace "$workspace" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --format json" ]
}

@test "basectl workspace doctor delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "doctor" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace doctor python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace doctor --workspace "$workspace" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --format json" ]
}

@test "basectl workspace clone delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local manifest="$TEST_TMPDIR/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    touch "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "clone" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace clone python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace clone --workspace "$workspace" --manifest "$manifest" --include-optional --dry-run

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --manifest $manifest --include-optional --dry-run" ]
}

@test "basectl workspace commands print help without requiring the Base Python venv" {
    run_basectl workspace status --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl workspace <status|check|doctor|clone> [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--format <format>"* ]]
    [[ "$output" == *"--include-optional"* ]]
    [[ "$output" == *"--dry-run"* ]]

    run_basectl workspace check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace <status|check|doctor|clone> [options]"* ]]

    run_basectl workspace doctor --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace <status|check|doctor|clone> [options]"* ]]

    run_basectl workspace clone --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace <status|check|doctor|clone> [options]"* ]]
}

@test "basectl workspace rejects unknown subcommands" {
    run_basectl workspace repair

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Unknown workspace command 'repair'."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}
