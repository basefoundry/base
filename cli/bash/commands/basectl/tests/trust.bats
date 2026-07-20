#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl trust prints help" {
    run_basectl trust --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl trust status [project] [options]"* ]]
    [[ "$output" == *"basectl trust allow <project> [options]"* ]]
    [[ "$output" == *"basectl trust revoke <project> [options]"* ]]
    [[ "$output" == *"--manifest-sha256 <sha256>"* ]]
}

@test "basectl trust leaves print command-scoped help" {
    run_basectl trust status --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl trust status [project] [options]"* ]]
    [[ "$output" == *"--format <text|csv|tsv|yaml|json>"* ]]
    [[ "$output" != *"--manifest-sha256"* ]]
    [[ "$output" != *"basectl trust revoke"* ]]

    run_basectl trust allow --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl trust allow <project> [options]"* ]]
    [[ "$output" == *"--manifest-sha256 <sha256>"* ]]
    [[ "$output" != *"--format"* ]]
    [[ "$output" != *"basectl trust status"* ]]

    run_basectl trust revoke --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl trust revoke <project> [options]"* ]]
    [[ "$output" == *"--workspace <path>"* ]]
    [[ "$output" != *"--format"* ]]
    [[ "$output" != *"--manifest-sha256"* ]]
}

@test "basectl trust status forwards without a project for workspace inspection" {
    local base_home="$TEST_TMPDIR/base-home"

    mkdir -p "$base_home/bin"
    cat > "$base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
printf 'args=%s\n' "$*"
printf 'active_project=%s\n' "${BASE_TRUST_ACTIVE_PROJECT:-}"
printf 'active_manifest=%s\n' "${BASE_TRUST_ACTIVE_PROJECT_MANIFEST:-}"
EOF
    chmod +x "$base_home/bin/base-wrapper"

    run env \
        BASE_HOME="$base_home" \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        BASE_PROJECT=demo \
        BASE_PROJECT_MANIFEST=/tmp/work/demo/base_manifest.yaml \
        bash -c '
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/trust.sh"
            base_trust_subcommand_main status --workspace /tmp/work
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"args=--project base base_trust status --workspace /tmp/work"* ]]
    [[ "$output" == *"active_project=demo"* ]]
    [[ "$output" == *"active_manifest=/tmp/work/demo/base_manifest.yaml"* ]]
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
