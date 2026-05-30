#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl clean delegates to the Python cleanup layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_clean" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected clean python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl clean --older-than 30d --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"ARGS=--older-than 30d --dry-run"* ]]
}

@test "basectl clean prints help without requiring the Base Python venv" {
    run_basectl clean --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl clean [--older-than <age>] [--keep-last <count>] [options]"* ]]
}

@test "basectl clean reports missing cleanup criterion as a usage error" {
    run_basectl clean

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: One of '--older-than' or '--keep-last' is required."* ]]
    [[ "$output" != *"Traceback"* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl clean --older-than

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--older-than' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl clean --keep-last

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--keep-last' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]
}
