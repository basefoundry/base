#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl logs delegates to the Python logs layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_logs" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
    printf 'DISPLAY=%s\n' "${BASE_CLI_DISPLAY_COMMAND:-}"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected logs python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl logs --command check,doctor --limit 3 --latest

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"DISPLAY=basectl logs"* ]]
    [[ "$output" == *"ARGS=--command check,doctor --limit 3 --latest"* ]]
}

@test "basectl logs forwards verbose flag to the Python logs layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_logs" ]]; then
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected logs python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl logs -v --latest

    [ "$status" -eq 0 ]
    [[ "$output" == *"ARGS=--debug --latest"* ]]
}

@test "basectl logs last-failed forwards action and format to the Python logs layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_logs" ]]; then
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected logs python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl logs last-failed --format json --lines 5

    [ "$status" -eq 0 ]
    [[ "$output" == *"ARGS=last-failed --format json --lines 5"* ]]
}

@test "basectl logs prints help without requiring the Base Python venv" {
    run_basectl logs --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl logs [options]"* ]]
    [[ "$output" == *"basectl logs last-failed"* ]]
    [[ "$output" == *"--command <name[,name...]>"* ]]
    [[ "$output" == *"--latest"* ]]
    [[ "$output" != *"--path"* ]]
    [[ "$output" != *"--format <format>"* ]]
}

@test "basectl logs last-failed prints focused help" {
    run_basectl logs last-failed --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl logs last-failed [options]"* ]]
    [[ "$output" == *"--format <format>"* ]]
    [[ "$output" == *"--lines <count>"* ]]
    [[ "$output" != *"--limit"* ]]
    [[ "$output" != *"--path"* ]]
    [[ "$output" != *"--tail"* ]]
    [[ "$output" != *"--open"* ]]
}

@test "basectl logs reports missing option arguments as usage errors" {
    run_basectl logs --command

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--command' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl logs --limit

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--limit' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl logs last-failed --format

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--format' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]
}
