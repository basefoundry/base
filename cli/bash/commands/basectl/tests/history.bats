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

    run_basectl history --project demo --command check --status error --limit 3 --format json --oldest-first --last 2h --since 2026-06-10 --until 2026-06-11 --local-time

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"ARGS=--project demo --command check --status error --limit 3 --format json --oldest-first --last 2h --since 2026-06-10 --until 2026-06-11 --local-time"* ]]
}

@test "basectl history forwards report mode to the Python history layer" {
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

    run_basectl history --report --limit 5 --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *"ARGS=--report --limit 5 --format json"* ]]
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
    [[ "$output" == *"--report"* ]]
    [[ "$output" != *"--include-internal"* ]]
    [[ "$output" == *"--oldest-first"* ]]
    [[ "$output" == *"--last <duration>"* ]]
    [[ "$output" == *"--since <time>"* ]]
    [[ "$output" == *"--until <time>"* ]]
    [[ "$output" == *"--local-time"* ]]
    [[ "$output" == *"--format <text|markdown|json>"* ]]
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

    run_basectl history --since

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--since' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]
}

@test "basectl history forwards public display command to Python wrapper" {
    local base_home="$TEST_TMPDIR/base-home"

    mkdir -p "$base_home/bin"
    cat > "$base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
printf 'display=%s\n' "${BASE_CLI_DISPLAY_COMMAND:-}"
printf 'args=%s\n' "$*"
EOF
    chmod +x "$base_home/bin/base-wrapper"

    run env \
        BASE_HOME="$base_home" \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/history.sh"
            base_history_subcommand_main --limit 2
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"display=basectl history"* ]]
    [[ "$output" == *"args=--project base base_history --limit 2"* ]]
}
