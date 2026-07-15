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

@test "basectl workspace onboarding delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local manifest="$TEST_TMPDIR/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    touch "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "onboarding" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace onboarding python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace onboarding --workspace "$workspace" --manifest "$manifest" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --manifest $manifest --format json" ]
}

@test "basectl workspace agent-brief delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local manifest="$TEST_TMPDIR/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    touch "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "agent-brief" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace agent brief python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace agent-brief --workspace "$workspace" --manifest "$manifest" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --manifest $manifest --format json" ]
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

@test "basectl workspace pull delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local source="$TEST_TMPDIR/canonical-workspace.yaml"
    local manifest="$TEST_TMPDIR/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")"
    touch "$source"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "pull" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace pull python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace pull --source "$source" --manifest "$manifest" --dry-run

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--source $source --manifest $manifest --dry-run" ]
}

@test "basectl workspace configure delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local manifest="$TEST_TMPDIR/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
    touch "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "configure" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace configure python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace configure --workspace "$workspace" --manifest "$manifest" --dry-run

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --manifest $manifest --dry-run" ]
}

@test "basectl workspace init delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local config_repo="$TEST_TMPDIR/base-workspace"
    local manifest="$TEST_TMPDIR/base-workspace/workspace.yaml"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base" "$config_repo"
    touch "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "init" ]]; then
    printf 'ARGS=%s\n' "${*:4}"
    exit 0
fi
printf 'unexpected workspace init python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    workspace="$(cd "$workspace" && pwd -P)"
    config_repo="$(cd "$config_repo" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" workspace init base-workspace --owner codeforester --path "$config_repo" --workspace "$workspace" --manifest workspace.yaml --include-optional --dry-run

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=base-workspace --owner codeforester --path $config_repo --workspace $workspace --manifest workspace.yaml --include-optional --dry-run" ]
}

@test "basectl workspace commands print help without requiring the Base Python venv" {
    run_basectl workspace status --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl workspace <status|check|doctor> [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--format <format>"* ]]

    run_basectl workspace agent-brief --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace agent-brief [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--format <format>"* ]]
    [[ "$output" == *"without cloning, setup, or network calls"* ]]

    run_basectl workspace check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace <status|check|doctor> [options]"* ]]
    [[ "$output" == *"--format <format>"* ]]

    run_basectl workspace doctor --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace <status|check|doctor> [options]"* ]]
    [[ "$output" == *"--format <format>"* ]]

    run_basectl workspace onboarding --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace onboarding [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--format <format>"* ]]

    run_basectl workspace clone --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace clone [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--include-optional"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--format <format>"* ]]

    run_basectl workspace pull --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace pull [options]"* ]]
    [[ "$output" == *"--source <url-or-path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--format <format>"* ]]

    run_basectl workspace configure --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace configure [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--format <format>"* ]]

    run_basectl workspace init --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace init <workspace-source> [options]"* ]]
    [[ "$output" == *"--owner <owner>"* ]]
    [[ "$output" == *"--path <path>"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--manifest <path>"* ]]
    [[ "$output" == *"--include-optional"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--format <format>"* ]]

    run_basectl workspace help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace <status|check|doctor|onboarding|agent-brief|clone|pull|init|configure> [options]"* ]]
    [[ "$output" != *"Project virtual environment Python was not found"* ]]
}

@test "basectl workspace rejects unknown subcommands" {
    run_basectl workspace repair

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Unknown workspace command 'repair'."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}
