#!/usr/bin/env bats

load ./setup_helpers.bash


create_ci_project() {
    local workspace="$1"
    local project="${2:-demo}"
    local project_dir="$workspace/$project"

    mkdir -p "$project_dir"
    cat > "$project_dir/base_manifest.yaml" <<EOF
schema_version: 1

project:
  name: $project

python: {}
EOF
}

prepare_ci_runtime() {
    local workspace="$1"

    create_xcode_stubs
    create_brew_stub
    create_ci_project "$workspace" demo
    touch "$TEST_STATE_DIR/xcode-installed"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/base/.venv"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"
}

run_ci_delegate_capture() {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="${BASE_BASH_LIBS_DIR:-}" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/ci.sh"

            base_ci_source_subcommand_module() {
                return 0
            }
            base_setup_subcommand_main() {
                printf "command=setup\n"
                printf "arg=<%s>\n" "$@"
            }
            base_check_subcommand_main() {
                printf "command=check\n"
                printf "arg=<%s>\n" "$@"
            }
            base_doctor_subcommand_main() {
                printf "command=doctor\n"
                printf "arg=<%s>\n" "$@"
            }

            base_ci_subcommand_main "$@"
        ' bash "$@"
}

@test "basectl ci prints help" {
    run_base_command ci --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl ci setup [project] [options]"* ]]
    [[ "$output" == *"basectl ci check [project] [options]"* ]]
    [[ "$output" == *"basectl ci doctor [project] [options]"* ]]
    [[ "$output" == *"Target command options are passed through unchanged after --ci is added."* ]]
    [[ "$output" == *'Run `basectl setup --help`, `basectl check --help`, or'* ]]
    [[ "$output" == *'`basectl doctor --help` for the canonical option list.'* ]]
    [[ "$output" == *"Compatibility alias for setup/check/doctor --ci."* ]]
    [[ "$output" == *"Prefer: basectl <setup|check|doctor> --ci [project] [options]"* ]]
    [[ "$output" == *"BASE_CI=true"* ]]
    [[ "$output" == *"Does not run project tests, launch GitHub Actions, or create Ubuntu/Multipass VMs."* ]]
}

@test "basectl ci requires a supported lifecycle command" {
    run_base_command ci
    [ "$status" -eq 2 ]
    [[ "$output" == *"CI command is required."* ]]

    run_base_command ci deploy demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown ci command 'deploy'."* ]]
}

@test "basectl ci passes lifecycle arguments through unchanged after adding --ci" {
    run_ci_delegate_capture setup demo --dry-run --yes --notify --no-notify --recreate-venv

    [ "$status" -eq 0 ]
    [ "$output" = "$(printf '%s\n' \
        'command=setup' \
        'arg=<--ci>' \
        'arg=<demo>' \
        'arg=<--dry-run>' \
        'arg=<--yes>' \
        'arg=<--notify>' \
        'arg=<--no-notify>' \
        'arg=<--recreate-venv>')" ]

    run_ci_delegate_capture check demo --remote-network

    [ "$status" -eq 0 ]
    [ "$output" = "$(printf '%s\n' \
        'command=check' \
        'arg=<--ci>' \
        'arg=<demo>' \
        'arg=<--remote-network>')" ]

    run_ci_delegate_capture doctor demo --remote-network --no-color

    [ "$status" -eq 0 ]
    [ "$output" = "$(printf '%s\n' \
        'command=doctor' \
        'arg=<--ci>' \
        'arg=<demo>' \
        'arg=<--remote-network>' \
        'arg=<--no-color>')" ]
}

@test "basectl ci lifecycle help and parser errors match canonical commands" {
    local command
    local alias_output alias_status canonical_output canonical_status

    for command in setup check doctor; do
        run_base_command ci "$command" --help
        alias_status="$status"
        alias_output="$output"
        run_base_command "$command" --ci --help
        canonical_status="$status"
        canonical_output="$output"

        [ "$alias_status" -eq "$canonical_status" ]
        [ "$alias_output" = "$canonical_output" ]

        run_base_command ci "$command" demo --not-a-real-option
        alias_status="$status"
        alias_output="$output"
        run_base_command "$command" --ci demo --not-a-real-option
        canonical_status="$status"
        canonical_output="$output"

        [ "$alias_status" -eq "$canonical_status" ]
        [ "$alias_output" = "$canonical_output" ]
    done
}

@test "basectl ci forwards canonical setup mutation controls" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"

    run_base_command \
        BASE_SETUP_TEST_WORKSPACE="$workspace" \
        ci setup demo --dry-run --yes --no-notify --recreate-venv

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' \
        --dry-run \
        --manifest "$workspace/demo/base_manifest.yaml" \
        --action setup \
        demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-yes")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-notify")" = "false" ]
    [ "$(cat "$TEST_STATE_DIR/project-bootstrap-recreate-venv")" = "true" ]
}

@test "basectl ci forwards canonical check and doctor diagnostic controls" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" ci check demo --remote-network

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' \
        --manifest "$workspace/demo/base_manifest.yaml" \
        --action check \
        --format text \
        --remote-network \
        demo)" ]

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" ci doctor demo --remote-network --no-color

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' \
        --manifest "$workspace/demo/base_manifest.yaml" \
        --action doctor \
        --format text \
        --remote-network \
        demo)" ]
}

@test "basectl ci check delegates with CI defaults and JSON output" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" ci check demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    assert_base_check_json_status_for_readiness "$output"
    assert_base_bash_libraries_json_finding "$output"
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format json demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-base-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-ci")" = "true" ]
}

@test "basectl check --ci delegates with CI defaults and JSON output" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check --ci demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    assert_base_check_json_status_for_readiness "$output"
    [[ "$output" == *'"project": "demo"'* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format json demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-base-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-ci")" = "true" ]
}

@test "basectl ci setup disables notifications and writes JSON when requested" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"
    create_osascript_stub

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" ci setup demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"command": "setup"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"status": "ok"'* ]]
    [[ "$output" == *'"output":'* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-base-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-notify")" = "false" ]
    [ ! -f "$TEST_STATE_DIR/osascript-args" ]
}

@test "basectl setup --ci disables notifications and writes JSON when requested" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"
    create_osascript_stub

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" setup --ci demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"command": "setup"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"status": "ok"'* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-base-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-notify")" = "false" ]
    [ ! -f "$TEST_STATE_DIR/osascript-args" ]
}

@test "basectl doctor --ci delegates with CI defaults and JSON output" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" doctor --ci demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_findings":'* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action doctor --format json demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-base-ci")" = "true" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-ci")" = "true" ]
}

@test "basectl ci setup json output summarizes stderr without embedding log stream" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"
    printf '%s\n' \
        "2026-06-10 10:15:32 INFO    setup_common.sh:122 Homebrew is already installed." \
        "2026-06-10 10:15:33 ERROR   setup_common.sh:801 Python project setup layer failed." \
        > "$TEST_STATE_DIR/project-setup-stderr"
    printf '%s\n' 17 > "$TEST_STATE_DIR/project-setup-exit-code"

    run_base_command_separate_stderr BASE_SETUP_TEST_WORKSPACE="$workspace" ci setup demo --format json

    [ "$status" -eq 17 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"output": "Python project setup layer failed."'* ]]
    [[ "$output" == *'"output_lines": ['* ]]
    [[ "$output" == *'"Homebrew is already installed."'* ]]
    [[ "$output" == *'"Python project setup layer failed."'* ]]
    [[ "$output" != *"setup_common.sh"* ]]
    [[ "$stderr" == *"Homebrew is already installed."* ]]
    [[ "$stderr" == *"Python project setup layer failed."* ]]
}

@test "basectl ci setup json output preserves utf8" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"
    printf '%s\n' \
        "2026-06-10 10:15:33 ERROR   setup_common.sh:801 Café setup failed for 東京." \
        > "$TEST_STATE_DIR/project-setup-stderr"
    printf '%s\n' 17 > "$TEST_STATE_DIR/project-setup-exit-code"

    run_base_command_separate_stderr BASE_SETUP_TEST_WORKSPACE="$workspace" ci setup demo --format json

    [ "$status" -eq 17 ]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"Café setup failed for 東京."'* ]]
    [[ "$output" != *"\\u00e9"* ]]
    [[ "$output" != *"\\u6771"* ]]
    [[ "$stderr" == *"Café setup failed for 東京."* ]]
}

@test "basectl ci check supports Linux runtime-only JSON checks" {
    create_system_python3_stub
    create_project_setup_venv_stub "$TEST_HOME/.base.d/base/.venv"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"

    run_base_command OSTYPE=linux-gnu ci check base --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"status": "ok"'* ]]
    [[ "$output" == *'"name":"python","message":"Python is available for CI runtime checks."'* ]]
    [[ "$output" != *"Homebrew"* ]]
    [[ "$output" != *"Xcode"* ]]
}
