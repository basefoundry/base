#!/usr/bin/env bats

load ./basectl_helpers.bash

line_at() {
    local text="$1"
    local line_number="$2"

    printf '%s\n' "$text" | sed -n "${line_number}p"
}

@test "basectl config path rejects extra arguments with focused usage hint" {
    run_basectl config path extra

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: config path does not accept arguments." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl config --help' for usage." ]
    [[ "$output" != *"Usage:"* ]]
}

@test "basectl config doctor forwards through the Python wrapper" {
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
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/config.sh"
            base_config_subcommand_main doctor --format json
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"display=basectl config"* ]]
    [[ "$output" == *"args=--project base base_config doctor --format json"* ]]
}
