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
