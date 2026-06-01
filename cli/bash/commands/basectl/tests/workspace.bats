#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl workspace status delegates to the Python projects layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base"
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
        "$BASE_REPO_ROOT/bin/basectl" workspace status --workspace "$workspace" --format json

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=--workspace $workspace --format json" ]
    [ "$(cat "$TEST_TMPDIR/workspace-status-state")" = "BASE_PROJECT=base" ]
}

@test "basectl workspace status prints help without requiring the Base Python venv" {
    run_basectl workspace status --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl workspace status [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" == *"--format <format>"* ]]
}

@test "basectl workspace rejects unknown subcommands" {
    run_basectl workspace repair

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown workspace command 'repair'"* ]]
    [[ "$output" != *"Traceback"* ]]
}
