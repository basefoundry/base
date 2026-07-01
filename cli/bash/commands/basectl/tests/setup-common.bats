#!/usr/bin/env bats

load ./setup_helpers.bash

run_setup_common_script() {
    local bash_libs_dir
    local script="$1"

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        PYTHONPATH="${BASE_SETUP_TEST_PYTHONPATH:-}" \
        bash -c "source \"\$BASE_HOME/base_init.sh\"; source \"\$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh\"; $script"
}

@test "setup_common caches Base virtualenv and Python import paths" {
    run_setup_common_script 'setup_refresh_cached_paths; printf "venv=%s\n" "$(setup_venv_dir)"; printf "pythonpath=%s\n" "$(setup_pythonpath)"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"venv=$TEST_HOME/.base.d/base/.venv"* ]]
    [[ "$output" == *"pythonpath=$BASE_REPO_ROOT/lib/python:$BASE_REPO_ROOT/cli/python"* ]]
}

@test "setup_common appends an inherited PYTHONPATH after Base paths" {
    BASE_SETUP_TEST_PYTHONPATH="/opt/example/python" \
        run_setup_common_script 'setup_refresh_cached_paths; setup_pythonpath'

    [ "$status" -eq 0 ]
    [ "$output" = "$BASE_REPO_ROOT/lib/python:$BASE_REPO_ROOT/cli/python:/opt/example/python" ]
}

@test "setup_common parses explicit warning check results" {
    local result_file="$TEST_STATE_DIR/check.result"

    run_setup_common_script "setup_write_check_result_file \"$result_file\" base_bash_libraries true 'libraries available' 'install libraries' 'used sibling checkout' warn; setup_parse_check_result_file \"$result_file\"; printf 'name=%s\n' \"\$_BASE_SETUP_PARSED_CHECK_NAME\"; printf 'ok=%s\n' \"\$_BASE_SETUP_PARSED_CHECK_OK\"; printf 'status=%s\n' \"\$_BASE_SETUP_PARSED_CHECK_STATUS\"; printf 'message=%s\n' \"\$_BASE_SETUP_PARSED_CHECK_MESSAGE\"; printf 'recovery=%s\n' \"\$_BASE_SETUP_PARSED_CHECK_RECOVERY\"; printf 'debug=%s\n' \"\$_BASE_SETUP_PARSED_CHECK_DEBUG_MESSAGE\""

    [ "$status" -eq 0 ]
    [[ "$output" == *"name=base_bash_libraries"* ]]
    [[ "$output" == *"ok=true"* ]]
    [[ "$output" == *"status=warn"* ]]
    [[ "$output" == *"message=libraries available"* ]]
    [[ "$output" == *"recovery=install libraries"* ]]
    [[ "$output" == *"debug=used sibling checkout"* ]]
}

@test "setup_common owns base check finding metadata" {
    run_setup_common_script 'printf "homebrew=%s/%s\n" "$(setup_base_check_finding_id homebrew)" "$(setup_base_check_display_name homebrew)"; printf "venv=%s/%s\n" "$(setup_base_check_finding_id base_virtualenv)" "$(setup_base_check_display_name base_virtualenv)"; printf "unknown=%s/%s\n" "$(setup_base_check_finding_id unexpected)" "$(setup_base_check_display_name unexpected)"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"homebrew=BASE-D001/Homebrew"* ]]
    [[ "$output" == *"venv=BASE-D004/Base virtualenv"* ]]
    [[ "$output" == *"unknown=BASE-D000/unexpected"* ]]
}

@test "setup_common exposes centralized platform policy helpers" {
    run_setup_common_script '
        for helper in \
            setup_current_platform \
            setup_platform_supported \
            setup_collect_platform_base_check_results \
            setup_run_platform_install; do
            declare -F "$helper" >/dev/null || {
                printf "missing helper: %s\n" "$helper" >&2
                exit 10
            }
        done
        printf "platform=%s\n" "$(setup_current_platform)"
        setup_platform_supported macos || exit 11
        setup_platform_supported linux-debian || exit 12
        if setup_platform_supported linux-unknown; then
            printf "linux-unknown should not be supported yet\n" >&2
            exit 13
        fi
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"platform=macos"* ]]
}
