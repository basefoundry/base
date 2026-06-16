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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv"
}

@test "basectl ci prints help" {
    run_base_command ci --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl ci setup <project>"* ]]
    [[ "$output" == *"basectl ci check <project>"* ]]
    [[ "$output" == *"basectl ci doctor <project>"* ]]
    [[ "$output" == *"--format <text|json>"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" == *"Profile lists are comma-separated, for example: --profile dev,sre."* ]]
    [[ "$output" == *"dev - Base development tooling for this repository."* ]]
    [[ "$output" == *"sre - production/SRE prerequisite tooling."* ]]
    [[ "$output" == *"ai  - AI coding assistant tooling."* ]]
    [[ "$output" == *"BASE_CI=true"* ]]
}

@test "basectl ci requires a command and project" {
    run_base_command ci
    [ "$status" -eq 2 ]
    [[ "$output" == *"CI command is required."* ]]

    run_base_command ci check --format json
    [ "$status" -eq 2 ]
    [[ "$output" == *"The 'ci check' command requires a project name."* ]]
}

@test "basectl ci check delegates with CI defaults and JSON output" {
    local workspace="$TEST_TMPDIR/workspace"

    prepare_ci_runtime "$workspace"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" ci check demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "ok"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
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
    [[ "$output" != *"setup_common.sh"* ]]
    [[ "$stderr" == *"Homebrew is already installed."* ]]
    [[ "$stderr" == *"Python project setup layer failed."* ]]
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
