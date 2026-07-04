#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl trust prints help" {
    run_basectl trust --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl trust status <project> [options]"* ]]
    [[ "$output" == *"basectl trust allow <project> [options]"* ]]
    [[ "$output" == *"basectl trust revoke <project> [options]"* ]]
    [[ "$output" == *"--manifest-sha256 <sha256>"* ]]
}

@test "basectl trust forwards through the Python wrapper" {
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
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/trust.sh"
            base_trust_subcommand_main status demo --workspace /tmp/work --format json
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"display=basectl trust"* ]]
    [[ "$output" == *"args=--project base base_trust status demo --workspace /tmp/work --format json"* ]]
}
