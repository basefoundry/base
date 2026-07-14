#!/usr/bin/env bats

load ./basectl_helpers.bash

source_project_command_helpers() {
    source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/project_command_helpers.sh"
}

@test "project command helper resolves project venv directories" {
    source_project_command_helpers

    HOME="$TEST_HOME"
    unset BASE_PROJECT_VENV_DIR

    run base_project_venv_dir demo

    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_HOME/.base.d/demo/.venv" ]

    run base_project_venv_dir demo "$TEST_TMPDIR/demo" "$TEST_TMPDIR/demo/base_manifest.yaml"

    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_TMPDIR/demo/.venv" ]

    BASE_PROJECT_VENV_DIR="$TEST_TMPDIR/custom-venv"

    run base_project_venv_dir demo

    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_TMPDIR/custom-venv" ]
}

@test "project command helper resolves uv-managed project venv directories" {
    source_project_command_helpers

    local project_root="$TEST_TMPDIR/demo"
    local manifest_path="$project_root/base_manifest.yaml"

    mkdir -p "$project_root"
    printf 'project:\n  name: demo\npython:\n  manager: uv\nartifacts: []\n' > "$manifest_path"
    HOME="$TEST_HOME"
    unset BASE_PROJECT_VENV_DIR

    run base_project_venv_dir demo "$project_root" "$manifest_path" "__base_project_venv_dir=$project_root/.venv"

    [ "$status" -eq 0 ]
    [ "$output" = "$project_root/.venv" ]
}

@test "project command helper uses Python route venv metadata" {
    source_project_command_helpers

    local project_root="$TEST_TMPDIR/demo"
    local manifest_path="$project_root/base_manifest.yaml"

    mkdir -p "$project_root"
    printf 'project:\n  name: demo\npython: {manager: uv}\nartifacts: []\n' > "$manifest_path"
    HOME="$TEST_HOME"
    unset BASE_PROJECT_VENV_DIR

    run base_project_venv_dir demo "$project_root" "$manifest_path" "__base_project_venv_dir=$project_root/.venv"

    [ "$status" -eq 0 ]
    [ "$output" = "$project_root/.venv" ]
}

@test "project command helper activates project environment" {
    source_project_command_helpers

    local project_root="$TEST_TMPDIR/demo"
    local manifest_path="$project_root/base_manifest.yaml"
    local venv_dir="$project_root/.venv"

    mkdir -p "$venv_dir/bin"
    run env \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/project_command_helpers.sh"
            HOME="$1"
            PATH="/usr/bin:/bin"
            unset BASE_PROJECT BASE_PROJECT_ROOT BASE_PROJECT_MANIFEST BASE_PROJECT_VENV_DIR
            base_project_activate_environment demo "$2" "$3" 0 "__base_project_venv_dir=$4"
            printf "BASE_PROJECT=%s\n" "$BASE_PROJECT"
            printf "BASE_PROJECT_ROOT=%s\n" "$BASE_PROJECT_ROOT"
            printf "BASE_PROJECT_MANIFEST=%s\n" "$BASE_PROJECT_MANIFEST"
            printf "BASE_PROJECT_VENV_DIR=%s\n" "$BASE_PROJECT_VENV_DIR"
            printf "PATH=%s\n" "$PATH"
        ' bash "$TEST_HOME" "$project_root" "$manifest_path" "$venv_dir"

    [ "$status" -eq 0 ]
    [[ "$output" == *"$venv_dir"* ]]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$project_root"* ]]
    [[ "$output" == *"BASE_PROJECT_MANIFEST=$manifest_path"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$venv_dir"* ]]
    [[ "$output" == *"PATH=$venv_dir/bin:/usr/bin:/bin"* ]]
}

@test "project command helper warns for missing venv outside dry-run" {
    source_project_command_helpers

    local project_root="$TEST_TMPDIR/demo"
    local manifest_path="$project_root/base_manifest.yaml"
    local venv_dir="$project_root/.venv"

    run env \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/project_command_helpers.sh"
            HOME="$1"
            log_warn() { printf "WARN:%s\n" "$*"; }
            base_project_activate_environment demo "$2" "$3" 0 "__base_project_venv_dir=$4"
        ' bash "$TEST_HOME" "$project_root" "$manifest_path" "$venv_dir"

    [ "$status" -eq 0 ]
    [[ "$output" == *"WARN:Project virtual environment was not found at '$venv_dir'. Run 'basectl setup demo' first."* ]]
    [[ "$output" == *"set python.venv_location: external in base_manifest.yaml or export BASE_PROJECT_VENV_DIR"* ]]

    run env \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/project_command_helpers.sh"
            HOME="$1"
            log_warn() { printf "WARN:%s\n" "$*"; }
            base_project_activate_environment demo "$2" "$3" 1 "__base_project_venv_dir=$4"
        ' bash "$TEST_HOME" "$project_root" "$manifest_path" "$venv_dir"

    [ "$status" -eq 0 ]
    [[ "$output" != *"WARN:"* ]]
}

@test "project command helper formats extra args for display" {
    source_project_command_helpers

    run base_format_extra_args plain "two words" ""

    [ "$status" -eq 0 ]
    [ "$output" = " plain two\\ words ''" ]
}

@test "project command helper appends extra args for shell commands" {
    source_project_command_helpers

    run base_command_with_extra_args "pytest" "-k" "slow case"

    [ "$status" -eq 0 ]
    [ "$output" = 'pytest "$@"' ]

    run base_command_with_extra_args "mise run test" "--watch"

    [ "$status" -eq 0 ]
    [ "$output" = 'mise run test -- "$@"' ]
}

@test "project command helper runs bash -c commands with a named sentinel" {
    source_project_command_helpers

    local working_dir="$TEST_TMPDIR/project"
    mkdir -p "$working_dir"

    run base_project_run_shell_command \
        "$working_dir" \
        'printf "pwd=%s\n" "$PWD"; printf "sentinel=%s\n" "$0"; printf "args=<%s><%s>\n" "$1" "$2"' \
        basectl-test \
        "one word" \
        two

    [ "$status" -eq 0 ]
    [[ "$output" == *"pwd=$working_dir"* ]]
    [[ "$output" == *"sentinel=basectl-test"* ]]
    [[ "$output" == *"args=<one word><two>"* ]]
}

@test "project command helper wraps uv runner commands" {
    source_project_command_helpers

    run base_command_with_runner "uv" "pytest tests/" "-k" "slow case"

    [ "$status" -eq 0 ]
    [ "$output" = 'uv run -- pytest tests/ "$@"' ]
}

@test "project command helper displays mise extra args after separator" {
    source_project_command_helpers

    run base_display_command "pytest" "-k" "slow case"

    [ "$status" -eq 0 ]
    [ "$output" = "pytest -k slow\\ case" ]

    run base_display_command "mise run test" "--watch"

    [ "$status" -eq 0 ]
    [ "$output" = "mise run test -- --watch" ]
}

@test "project command helper displays uv runner commands" {
    source_project_command_helpers

    run base_display_command_with_runner "uv" "pytest tests/" "-k" "slow case"

    [ "$status" -eq 0 ]
    [ "$output" = "uv run -- pytest tests/ -k slow\\ case" ]
}
