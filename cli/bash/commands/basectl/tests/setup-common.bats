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
        BASE_CLI_SOURCE_DIR="$(base_cli_test_source_dir)" \
        PYTHONPATH="${BASE_SETUP_TEST_PYTHONPATH:-}" \
        bash -c "source \"\$BASE_HOME/base_init.sh\"; source \"\$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh\"; $script"
}

@test "setup_common caches Base virtualenv and Python import paths" {
    local expected_pythonpath="$BASE_REPO_ROOT/cli/python"
    local base_cli_path

    base_cli_path="$(base_cli_test_source_dir)"
    if [[ -n "$base_cli_path" ]]; then
        expected_pythonpath="$base_cli_path:$expected_pythonpath"
    fi

    run_setup_common_script 'setup_refresh_cached_paths; printf "venv=%s\n" "$(setup_venv_dir)"; printf "pythonpath=%s\n" "$(setup_pythonpath)"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"venv=$TEST_HOME/.base.d/base/.venv"* ]]
    [[ "$output" == *"pythonpath=$expected_pythonpath"* ]]
}

@test "setup_common appends an inherited PYTHONPATH after Base paths" {
    local expected_pythonpath="$BASE_REPO_ROOT/cli/python"
    local base_cli_path

    base_cli_path="$(base_cli_test_source_dir)"
    if [[ -n "$base_cli_path" ]]; then
        expected_pythonpath="$base_cli_path:$expected_pythonpath"
    fi

    BASE_SETUP_TEST_PYTHONPATH="/opt/example/python" \
        run_setup_common_script 'setup_refresh_cached_paths; setup_pythonpath'

    [ "$status" -eq 0 ]
    [ "$output" = "$expected_pythonpath:/opt/example/python" ]
}

@test "setup_common delegates dry-run truthiness to the shared stdlib" {
    run_setup_common_script '
        for value in true 1 yes on; do
            BASE_BASH_LIBS_DRY_RUN="$value"
            setup_is_dry_run || {
                printf "expected dry-run value to be enabled: %s\n" "$value" >&2
                exit 1
            }
        done
        for value in "" false 0 no off; do
            BASE_BASH_LIBS_DRY_RUN="$value"
            if setup_is_dry_run; then
                printf "expected dry-run value to be disabled: %s\n" "$value" >&2
                exit 1
            fi
        done
        printf "dry-run truthiness is shared\n"
    '

    [ "$status" -eq 0 ]
    [ "$output" = "dry-run truthiness is shared" ]
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

@test "setup_common writes collected check result records for Python JSON assembly" {
    local output_dir="$TEST_STATE_DIR/check-records"

    run_setup_common_script "setup_add_check_result_with_status homebrew ok 'Homebrew is installed.' ''; setup_add_check_result_with_status xcode_command_line_tools warn 'Xcode needs attention.' 'Repair Xcode.'; setup_write_collected_check_result_files \"$output_dir\"; printf -- '---\\n'; cat \"$output_dir/check-0.result\"; printf -- '---\\n'; cat \"$output_dir/check-1.result\""

    [ "$status" -eq 0 ]
    [[ "$output" == *"$output_dir/check-0.result"* ]]
    [[ "$output" == *"$output_dir/check-1.result"* ]]
    [[ "$output" == *"name=homebrew"* ]]
    [[ "$output" == *"status=ok"* ]]
    [[ "$output" == *"message=Homebrew is installed."* ]]
    [[ "$output" == *"name=xcode_command_line_tools"* ]]
    [[ "$output" == *"status=warn"* ]]
    [[ "$output" == *"recovery=Repair Xcode."* ]]
}

@test "setup_common delegates base check metadata to Python" {
    run_setup_common_script 'setup_base_check_metadata homebrew base_virtualenv unexpected'

    [ "$status" -eq 0 ]
    [[ "$output" == *$'homebrew\tBASE-D001\tHomebrew'* ]]
    [[ "$output" == *$'base_virtualenv\tBASE-D004\tBase virtualenv'* ]]
    [[ "$output" == *$'unexpected\tBASE-D000\tunexpected'* ]]
}

@test "setup_common exposes centralized platform policy helpers" {
    run_setup_common_script '
        for helper in \
            setup_current_platform \
            setup_current_host_env \
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

@test "setup_common exposes Linux release baseline check helper" {
    run_setup_common_script '
        declare -F setup_add_linux_release_baseline_check_result >/dev/null || exit 30
        printf "linux release baseline helper is available\n"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"linux release baseline helper is available"* ]]
}

@test "setup_common sources Linux/Debian helper idempotently" {
    run_setup_common_script '
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_linux_debian.sh"
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_linux_debian.sh"
        for helper in \
            setup_find_linux_python_bin \
            setup_collect_linux_debian_base_check_results \
            setup_run_linux_debian_apt_prerequisites \
            setup_run_linux_debian_install; do
            declare -F "$helper" >/dev/null || {
                printf "missing helper: %s\n" "$helper" >&2
                exit 20
            }
        done
        printf "guard=%s\n" "${_base_setup_linux_debian_sourced:-}"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"guard=1"* ]]
}

@test "setup_common sources macOS/Homebrew helper idempotently" {
    run_setup_common_script '
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_macos_homebrew.sh"
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_macos_homebrew.sh"
        for helper in \
            base_homebrew_install \
            base_homebrew_run_verified_installer \
            setup_find_brew_bin \
            setup_install_homebrew \
            setup_collect_macos_base_check_results \
            setup_run_macos_install; do
            declare -F "$helper" >/dev/null || {
                printf "missing helper: %s\n" "$helper" >&2
                exit 21
            }
        done
        printf "guard=%s\n" "${_base_setup_macos_homebrew_sourced:-}"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"guard=1"* ]]
}

@test "setup_common sources venv helper idempotently" {
    run_setup_common_script '
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_venv.sh"
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_venv.sh"
        for helper in \
            setup_virtualenv_healthy_path \
            setup_create_virtualenv \
            setup_base_python_package_installed \
            setup_collect_base_python_runtime_check_results \
            setup_collect_ci_runtime_check_results \
            setup_run_shared_python_install_sequence \
            setup_run_ci_runtime_install; do
            declare -F "$helper" >/dev/null || {
                printf "missing helper: %s\n" "$helper" >&2
                exit 22
            }
        done
        printf "guard=%s\n" "${_base_setup_venv_sourced:-}"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"guard=1"* ]]
}

@test "setup platform adapters share Python setup order and omit user config in CI" {
    run_setup_common_script '
        setup_trace_add() { SETUP_TRACE="${SETUP_TRACE:+$SETUP_TRACE,}$1"; }
        setup_install_homebrew() { setup_trace_add homebrew; }
        setup_install_xcode_tools() { setup_trace_add xcode; }
        setup_install_python() { setup_trace_add python; }
        setup_run_linux_debian_apt_prerequisites() { setup_trace_add apt; }
        setup_profile_enabled() { return 0; }
        setup_run_linux_debian_github_cli_prerequisite() { setup_trace_add gh-cli; }
        setup_create_virtualenv() { setup_trace_add venv; }
        setup_upgrade_base_pip() { setup_trace_add pip; }
        setup_install_pyyaml() { setup_trace_add pyyaml; }
        setup_install_click() { setup_trace_add click; }
        setup_install_base_cli() { setup_trace_add base-cli; }
        setup_profiles_enabled() { return 0; }
        setup_is_dry_run() { return 1; }
        setup_run_base_dev_layer() { setup_trace_add profile; }
        setup_run_project_artifact_setup() { setup_trace_add artifacts; }
        setup_seed_user_config() { setup_trace_add user-config; }
        base_std_log_info() { :; }

        SETUP_TRACE=""
        setup_run_macos_install || exit $?
        printf "macos=%s\n" "$SETUP_TRACE"
        SETUP_TRACE=""
        setup_run_linux_debian_install || exit $?
        printf "debian=%s\n" "$SETUP_TRACE"
        SETUP_TRACE=""
        setup_run_ci_runtime_install || exit $?
        printf "ci=%s\n" "$SETUP_TRACE"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"macos=homebrew,xcode,python,venv,pip,pyyaml,click,base-cli,profile,artifacts,user-config"* ]]
    [[ "$output" == *"debian=apt,gh-cli,venv,pip,pyyaml,click,base-cli,profile,artifacts,user-config"* ]]
    [[ "$output" == *"ci=venv,pip,pyyaml,click,base-cli,profile,artifacts"* ]]
}

@test "shared Python setup sequence propagates pip and artifact failures" {
    run_setup_common_script '
        setup_trace_add() { SETUP_TRACE="${SETUP_TRACE:+$SETUP_TRACE,}$1"; }
        setup_create_virtualenv() { setup_trace_add venv; }
        setup_upgrade_base_pip() { setup_trace_add pip; return 37; }
        setup_install_pyyaml() { setup_trace_add pyyaml; }
        setup_install_click() { setup_trace_add click; }
        setup_install_base_cli() { setup_trace_add base-cli; }
        setup_profiles_enabled() { return 1; }
        setup_run_project_artifact_setup() { setup_trace_add artifacts; return 42; }
        setup_seed_user_config() { setup_trace_add user-config; }

        SETUP_TRACE=""
        if setup_run_shared_python_install_sequence true; then
            printf "pip failure was lost\\n" >&2
            exit 20
        else
            status=$?
            [[ "$status" -eq 37 ]] || exit 21
            [[ "$SETUP_TRACE" == venv,pip ]] || exit 22
        fi

        setup_upgrade_base_pip() { setup_trace_add pip; }
        SETUP_TRACE=""
        if setup_run_shared_python_install_sequence true; then
            printf "artifact failure was lost\\n" >&2
            exit 23
        else
            status=$?
            [[ "$status" -eq 42 ]] || exit 24
            [[ "$SETUP_TRACE" == venv,pip,pyyaml,click,base-cli,artifacts ]] || exit 25
        fi
        printf "pip and artifact failures propagated\\n"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"pip and artifact failures propagated"* ]]
}

@test "setup_common sources profiles helper idempotently" {
    run_setup_common_script '
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_profiles.sh"
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_profiles.sh"
        for helper in \
            setup_enable_profile_argument \
            setup_profiles_csv \
            setup_profile_json_key \
            setup_run_base_dev_layer; do
            declare -F "$helper" >/dev/null || {
                printf "missing helper: %s\n" "$helper" >&2
                exit 23
            }
        done
        setup_enable_profile_argument "DEV, sre"
        printf "profiles=%s\n" "$(setup_profiles_csv)"
        printf "json_key=%s\n" "$(setup_profile_json_key checks)"
        printf "guard=%s\n" "${_base_setup_profiles_sourced:-}"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"profiles=dev,sre"* ]]
    [[ "$output" == *"json_key=profile_checks"* ]]
    [[ "$output" == *"guard=1"* ]]
}

@test "setup_common sources project artifact helper idempotently" {
    run_setup_common_script '
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_project_artifacts.sh"
        source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_project_artifacts.sh"
        for helper in \
            setup_run_project_artifact_layer \
            setup_run_project_artifact_setup \
            setup_run_project_artifact_check \
            setup_run_project_artifact_check_json \
            setup_run_project_artifact_doctor \
            setup_run_project_artifact_doctor_json; do
            declare -F "$helper" >/dev/null || {
                printf "missing helper: %s\n" "$helper" >&2
                exit 24
            }
        done
        printf "guard=%s\n" "${_base_setup_project_artifacts_sourced:-}"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"guard=1"* ]]
}

@test "setup_common reports WSL2 host context without changing platform support" {
    run_setup_common_script '
        BASE_TEST_MODE=true
        BASE_SETUP_TEST_PLATFORM=linux-unknown
        BASE_SETUP_TEST_HOST_ENV=wsl2
        printf "host_env=%s\n" "$(setup_current_host_env)"
        setup_unsupported_platform_message "$(setup_current_platform)"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"host_env=wsl2"* ]]
    [[ "$output" == *"BASE_PLATFORM='linux-unknown', BASE_HOST_ENV='wsl2'"* ]]
    [[ "$output" == *"Ubuntu/Debian under WSL2 uses the Linux source-checkout path"* ]]
    [[ "$output" == *"native Windows are not supported"* ]]
}

@test "setup_common rejects host environment override outside test mode" {
    run_setup_common_script '
        CI=false
        BASE_SETUP_TEST_HOST_ENV=wsl2
        setup_current_host_env
    '

    [ "$status" -ne 0 ]
    [[ "$output" == *"BASE_SETUP_TEST_HOST_ENV is a test-only setup override"* ]]
}

@test "setup_common CI runtime checks use the Linux platform Python finder" {
    create_system_python3_stub
    create_project_setup_venv_stub "$TEST_HOME/.base.d/base/.venv"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"

    run_setup_common_script '
        BASE_TEST_MODE=true
        BASE_SETUP_TEST_PLATFORM=linux-debian
        setup_collect_ci_runtime_check_results
        setup_print_check_text_results
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Python is available for CI runtime checks."* ]]
}

@test "setup_common shares Python runtime check ordering across Linux and CI" {
    run_setup_common_script '
        setup_find_linux_python_bin() { printf "/linux/python\\n"; }
        setup_find_platform_python_bin() { printf "/ci/python\\n"; }
        setup_recovery_linux_python() { printf "install Linux Python"; }
        setup_recovery_ci_python() { printf "install CI Python"; }
        setup_virtualenv_healthy() { _BASE_SETUP_VENV_HEALTH_MESSAGE="venv is healthy"; return 0; }
        setup_base_python_package_installed() { return 0; }
        setup_add_linux_python_venv_check_result() {
            setup_add_check_result python_venv true "Python venv support is available."
        }

        setup_collect_base_python_runtime_check_results \
            setup_find_linux_python_bin "Ubuntu/Debian runtime checks" setup_recovery_linux_python click PyYAML true || exit $?
        printf "linux-names=%s\\n" "${_BASE_SETUP_CHECK_NAMES[*]}"
        printf "linux-python=%s\\n" "${_BASE_SETUP_CHECK_MESSAGES[0]}"
        setup_clear_check_results
        setup_collect_base_python_runtime_check_results \
            setup_find_platform_python_bin "CI runtime checks" setup_recovery_ci_python click PyYAML false || exit $?
        printf "ci-names=%s\\n" "${_BASE_SETUP_CHECK_NAMES[*]}"
        printf "ci-python=%s\\n" "${_BASE_SETUP_CHECK_MESSAGES[0]}"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"linux-names=python python_venv base_virtualenv pyyaml click"* ]]
    [[ "$output" == *"linux-python=Python is available for Ubuntu/Debian runtime checks."* ]]
    [[ "$output" == *"ci-names=python base_virtualenv pyyaml click"* ]]
    [[ "$output" == *"ci-python=Python is available for CI runtime checks."* ]]
}

@test "setup_common keeps GitHub CLI out of bulk Ubuntu apt prerequisites" {
    run_setup_common_script '
        packages="$(setup_linux_debian_apt_packages)"
        printf "packages=%s\n" "$packages"
        printf "command=%s\n" "$(setup_linux_debian_apt_prerequisite_command)"
        setup_linux_debian_github_cli_install_guidance
        case " $packages " in
            *" gh "*)
                printf "gh must use official GitHub CLI apt repository guidance, not the bulk apt list\n" >&2
                exit 20
                ;;
        esac
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"packages=bash git python3 python3-venv python3-pip bats shellcheck jq golang-go"* ]]
    [[ "$output" == *"command=sudo apt-get install -y bash git python3 python3-venv python3-pip bats shellcheck jq golang-go"* ]]
    [[ "$output" == *"Configure GitHub CLI's official Debian/Ubuntu apt repository before installing 'gh':"* ]]
}

@test "setup_common keeps GitHub CLI guidance out of bulk Ubuntu apt prerequisite install" {
    create_linux_dpkg_query_stub

    cat > "$TEST_MOCKBIN/sudo" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "$TEST_STATE_DIR/sudo-args"
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/sudo"

    run_setup_common_script '
        setup_enable_yes
        BASE_SETUP_TEST_MISSING_APT_PACKAGES=python3-venv
        setup_run_linux_debian_apt_prerequisites
    '

    [ "$status" -eq 0 ]
    [ "$(sed -n '1p' "$TEST_STATE_DIR/sudo-args")" = "apt-get update" ]
    [ "$(sed -n '2p' "$TEST_STATE_DIR/sudo-args")" = "apt-get install -y bash git python3 python3-venv python3-pip bats shellcheck jq golang-go" ]
    [[ "$output" != *"Configure GitHub CLI's official Debian/Ubuntu apt repository before installing 'gh':"* ]]
}
