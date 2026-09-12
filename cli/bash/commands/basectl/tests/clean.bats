#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl clean delegates to the Python cleanup layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
# Bash 3 reads BASH_ENV before assigning script arguments.
source "${BASH_ENV:?}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_clean" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected clean python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl clean --older-than 30d --yes

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"ARGS=--older-than 30d --yes"* ]]
}

@test "basectl clean prints help without requiring the Base Python venv" {
    run_basectl clean --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl clean [--older-than <age>] [--keep-last <count>] [options]"* ]]
    [[ "$output" == *"Accepts integer ages with suffix d, h, m, or s"* ]]
    [[ "$output" == *"Examples: 30d, 12h, 45m, 60s."* ]]
    [[ "$output" == *"--yes"* ]]
    [[ "$output" == *"Deletion requires --yes"* ]]
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

@test "basectl clean validates owned options without changing Python pass-through argv" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
# Bash 3 reads BASH_ENV before assigning script arguments.
source "${BASH_ENV:?}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_clean" ]]; then
    shift 2
    printf 'ARGC=%s\n' "$#"
    local_index=0
    for argument in "$@"; do
        printf 'ARG%s=<%s>\n' "$local_index" "$argument"
        local_index=$((local_index + 1))
    done
    exit 0
fi
printf 'unexpected clean python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl clean --older-than --yes -- --python-flag --foreign-value

    [ "$status" -eq 0 ]
    [[ "$output" == *"ARGC=5"* ]]
    [[ "$output" == *"ARG0=<--older-than>"* ]]
    [[ "$output" == *"ARG1=<--yes>"* ]]
    [[ "$output" == *"ARG2=<-->"* ]]
    [[ "$output" == *"ARG3=<--python-flag>"* ]]
    [[ "$output" == *"ARG4=<--foreign-value>"* ]]
}
