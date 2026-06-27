#!/usr/bin/env bats

load ./basectl_helpers.bash

line_at() {
    local text="$1"
    local line_number="$2"

    printf '%s\n' "$text" | sed -n "${line_number}p"
}

run_loaded_repo_helper_script() {
    local bash_libs_dir
    local script="$1"

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        bash -c "source \"\$BASE_HOME/base_init.sh\"; source \"\$BASE_HOME/cli/bash/commands/basectl/subcommands/repo.sh\"; base_repo_load_installer_template || exit \$?; $script"
}

@test "repo check help does not source installer-template helpers" {
    local bash_libs_dir
    local module_dir="$TEST_TMPDIR/repo-module"

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    mkdir -p "$module_dir"
    cp "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo.sh" "$module_dir/repo.sh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        BASE_REPO_TEST_MODULE_DIR="$module_dir" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_REPO_TEST_MODULE_DIR/repo.sh"
            base_repo_subcommand_main check --help
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl repo check [path] [options]"* ]]
    [[ "$output" != *"repo_installer_template.sh"* ]]
}

@test "repo installer-template helper rejects an empty --repo assignment" {
    run_loaded_repo_helper_script 'base_repo_installer_template "$HOME/install.sh" --repo= --pr --dry-run'

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: Option '--repo' requires an argument." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo installer-template --help' for usage." ]
    [[ "$output" != *"Usage:"* ]]
    [ ! -e "$TEST_HOME/install.sh" ]
}

@test "repo installer-template helper resolves the maintained template path" {
    run_loaded_repo_helper_script 'base_repo_installer_template_path'

    [ "$status" -eq 0 ]
    [ "$output" = "$BASE_REPO_ROOT/templates/project-install.sh" ]
}

@test "repo installer-template helper renders the pull request body command" {
    run_loaded_repo_helper_script 'base_repo_create_installer_template_pr_body "/tmp/My Project/install.sh" "codeforester/base-demo"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"Add the maintained Base project installer template."* ]]
    [[ "$output" == *'basectl repo installer-template "/tmp/My Project/install.sh" --repo codeforester/base-demo --pr'* ]]
}
