#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl logs delegates to the Python logs layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_logs" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected logs python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl logs --command check --limit 3 --path

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"ARGS=--command check --limit 3 --path"* ]]
}

@test "basectl logs prints help without requiring the Base Python venv" {
    run_basectl logs --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl logs [options]"* ]]
    [[ "$output" == *"--command <name>"* ]]
    [[ "$output" == *"--path"* ]]
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
}
