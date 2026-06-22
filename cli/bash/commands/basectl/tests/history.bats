#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl history delegates to the Python history layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_history" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected history python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl history --project demo --command check --status error --limit 3 --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"ARGS=--project demo --command check --status error --limit 3 --format json"* ]]
}

@test "basectl history forwards verbose flag to the Python history layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_history" ]]; then
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected history python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl history -v --limit 2

    [ "$status" -eq 0 ]
    [[ "$output" == *"ARGS=--debug --limit 2"* ]]
}

@test "basectl history prints help without requiring the Base Python venv" {
    run_basectl history --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl history [options]"* ]]
    [[ "$output" == *"--project <name>"* ]]
    [[ "$output" == *"--format <text|json>"* ]]
}

@test "basectl history reports missing option arguments as usage errors" {
    run_basectl history --project

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--project' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl history --limit

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--limit' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]
}
