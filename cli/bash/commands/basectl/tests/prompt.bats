#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl prompt prints help without requiring the Base Python venv" {
    run_basectl prompt --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl prompt list"* ]]
    [[ "$output" == *"basectl prompt <name>"* ]]
    [[ "$output" == *"product-self-review"* ]]
    [[ "$output" == *"--output <path>"* ]]
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

@test "basectl prompt -v forwards debug without counting it as a prompt name" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local state_file="$TEST_TMPDIR/prompt-debug-state"

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
        "$BASE_REPO_ROOT/bin/basectl" prompt -v product-self-review

    [ "$status" -eq 0 ]
    [[ "$output" == *"# rendered prompt"* ]]
    [ "$(cat "$state_file")" = "--debug product-self-review" ]
}

@test "basectl prompt forwards output path to the Python prompt renderer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local state_file="$TEST_TMPDIR/prompt-output-state"
    local output_path="$TEST_TMPDIR/product-self-review.md"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_prompt" ]]; then
    shift 2
    printf '%s\n' "$*" > "${BASE_TEST_PROMPT_STATE:?}"
    printf "Wrote prompt 'product-self-review' to %s\n" "${BASE_TEST_PROMPT_OUTPUT:?}"
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
        BASE_TEST_PROMPT_OUTPUT="$output_path" \
        "$BASE_REPO_ROOT/bin/basectl" prompt product-self-review --output "$output_path"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Wrote prompt 'product-self-review' to $output_path"* ]]
    [ "$(cat "$state_file")" = "product-self-review --output $output_path" ]
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

@test "basectl prompt forwards public display command to Python wrapper" {
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
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/prompt.sh"
            base_prompt_subcommand_main list
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"display=basectl prompt"* ]]
    [[ "$output" == *"args=--project base base_prompt list"* ]]
}
