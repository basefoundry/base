#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl prompt prints help without requiring the Base Python venv" {
    run_basectl prompt --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl prompt list"* ]]
    [[ "$output" == *"basectl prompt <name>"* ]]
    [[ "$output" == *"product-self-review"* ]]
}

@test "basectl prompt forwards prompt names to the Python prompt renderer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local state_file="$TEST_TMPDIR/prompt-state"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_prompt" ]]; then
    shift 2
    printf '%s\n' "$*" > "${BASE_TEST_PROMPT_STATE:?}"
    printf '# rendered prompt\n'
    exit 0
fi
printf 'unexpected prompt python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROMPT_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" prompt product-self-review

    [ "$status" -eq 0 ]
    [[ "$output" == *"# rendered prompt"* ]]
    [ "$(cat "$state_file")" = "product-self-review" ]
}

@test "basectl prompt list delegates to the Python prompt renderer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_prompt" && "${3:-}" == "list" ]]; then
    printf 'product-self-review\tPeriodic Base product self-review\n'
    exit 0
fi
printf 'unexpected prompt list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl prompt list

    [ "$status" -eq 0 ]
    [[ "$output" == *"product-self-review"* ]]
    [[ "$output" == *"Periodic Base product self-review"* ]]
}
