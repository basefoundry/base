#!/usr/bin/env bash

#
# setup_common.sh
#     Shared implementation for Base CLI environment bootstrap subcommands.
#
# This file houses the reusable setup/check helpers that back:
#   - `basectl setup`
#   - `basectl check`
#   - `basectl update-profile`
#
# It is meant to be sourced by the umbrella `basectl` command, not invoked
# directly.
#

[[ -n "${_base_setup_common_sourced:-}" ]] && return 0
_base_setup_common_sourced=1
readonly _base_setup_common_sourced

import_base_lib str/lib_str.sh

source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_check_results.sh"
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_linux_debian.sh"
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_macos_homebrew.sh"
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_venv.sh"
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_profiles.sh"

_BASE_SETUP_VENV_DIR_CACHE=""
_BASE_SETUP_PYTHONPATH_CACHE=""

setup_refresh_cached_paths() {
    local base_pythonpath old_pythonpath

    _BASE_SETUP_VENV_DIR_CACHE="${BASE_SETUP_VENV_DIR:-$HOME/.base.d/base/.venv}"

    base_pythonpath="$BASE_HOME/lib/python:$BASE_HOME/cli/python"
    old_pythonpath="${PYTHONPATH-}"
    if [[ -n "$old_pythonpath" ]]; then
        base_pythonpath="$base_pythonpath:$old_pythonpath"
    fi
    _BASE_SETUP_PYTHONPATH_CACHE="$base_pythonpath"
}

setup_ensure_cached_paths() {
    if [[ -z "${_BASE_SETUP_VENV_DIR_CACHE:-}" || -z "${_BASE_SETUP_PYTHONPATH_CACHE:-}" ]]; then
        setup_refresh_cached_paths
    fi
}

setup_clear_run_state() {
    # Clear legacy lowercase state too so inherited environments cannot trigger
    # lib_std.sh dry-run behavior unless this command explicitly enables it.
    unset dry_run DRY_RUN BASE_SETUP_PROFILE_ERROR BASE_SETUP_PROFILES BASE_SETUP_PROJECT_NAME BASE_SETUP_MANIFEST BASE_SETUP_REMOTE_NETWORK BASE_SETUP_RECREATE_VENV BASE_SETUP_YES
    setup_refresh_cached_paths
}

setup_enable_dry_run() {
    export DRY_RUN=true
}

setup_enable_debug_logging() {
    set_log_level DEBUG
    export LOG_DEBUG=1
}

setup_epoch_seconds() {
    printf '%(%s)T\n' -1
}

setup_backup_timestamp() {
    printf '%(%Y%m%dT%H%M%S)T\n' -1
}

setup_is_dry_run() {
    [[ "${DRY_RUN-}" == true ]]
}

setup_enable_yes() {
    export BASE_SETUP_YES=true
}

setup_yes_enabled() {
    [[ "${BASE_SETUP_YES:-false}" == true ]]
}

setup_test_assume_interactive() {
    [[ -n "${BASE_SETUP_TEST_ASSUME_INTERACTIVE+x}" ]] || return 1
    setup_reject_test_hook_if_disallowed BASE_SETUP_TEST_ASSUME_INTERACTIVE
    [[ "${BASE_SETUP_TEST_ASSUME_INTERACTIVE:-false}" == true ]]
}

setup_test_confirm_response() {
    [[ -n "${BASE_SETUP_TEST_CONFIRM_RESPONSE+x}" ]] || return 1
    setup_reject_test_hook_if_disallowed BASE_SETUP_TEST_CONFIRM_RESPONSE
    printf '%s\n' "$BASE_SETUP_TEST_CONFIRM_RESPONSE"
}

setup_interactive_consent_available() {
    setup_test_assume_interactive && return 0
    is_interactive
}

setup_read_confirmation_response() {
    local response

    if response="$(setup_test_confirm_response)"; then
        printf '%s\n' "$response"
        return 0
    fi

    if [[ -r /dev/tty ]]; then
        IFS= read -r response </dev/tty || return 1
    else
        IFS= read -r response || return 1
    fi
    printf '%s\n' "$response"
}

setup_require_linux_debian_system_consent() {
    local reason="$1"
    local response

    setup_yes_enabled && return 0

    if ! setup_interactive_consent_available; then
        fatal_error "$reason Run 'basectl setup --dry-run' to review the apt commands, then rerun with '--yes' to apply them."
    fi

    log_info "$reason"
    if [[ -n "${BASE_SETUP_TEST_STATE_DIR:-}" ]]; then
        setup_allow_test_hooks && touch "$BASE_SETUP_TEST_STATE_DIR/linux-consent-prompted"
    fi
    printf "Proceed with Ubuntu/Debian setup changes? [y/N] " >&2
    response="$(setup_read_confirmation_response)" || fatal_error "Ubuntu/Debian setup was not approved."
    case "${response,,}" in
        y|yes)
            setup_enable_yes
            return 0
            ;;
        *)
            fatal_error "Ubuntu/Debian setup was not approved."
            ;;
    esac
}

setup_enable_recreate_venv() {
    export BASE_SETUP_RECREATE_VENV=true
}

setup_enable_notifications() {
    export BASE_SETUP_NOTIFY=true
    export BASE_SETUP_NOTIFY_FORCE=true
}

setup_disable_notifications() {
    export BASE_SETUP_NOTIFY=false
}

setup_enable_ci_mode() {
    export BASE_CI=true
    export CI=true
    export BASE_SETUP_NOTIFY=false
    export BASE_SETUP_ALLOW_SYSTEM_PYTHON=true
    export BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=false
}

setup_notify_min_seconds() {
    printf '%s\n' "${BASE_SETUP_NOTIFY_MIN_SECONDS:-30}"
}

setup_notifications_enabled() {
    [[ "${BASE_SETUP_NOTIFY:-true}" == true ]]
}

setup_notifications_forced() {
    [[ "${BASE_SETUP_NOTIFY_FORCE:-false}" == true ]]
}

setup_ci_runtime_only() {
    [[ "${BASE_CI:-false}" == true && "$OSTYPE" != darwin* ]]
}

setup_current_platform() {
    local platform

    if [[ -n "${BASE_SETUP_TEST_PLATFORM+x}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_TEST_PLATFORM
        platform="$BASE_SETUP_TEST_PLATFORM"
    else
        platform="${BASE_PLATFORM:-unsupported}"
    fi
    if [[ -z "$platform" ]]; then
        platform=unsupported
    fi
    printf '%s\n' "$platform"
}

setup_current_host_env() {
    local host_env

    if [[ -n "${BASE_SETUP_TEST_HOST_ENV+x}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_TEST_HOST_ENV
        host_env="$BASE_SETUP_TEST_HOST_ENV"
    else
        host_env="${BASE_HOST_ENV:-native}"
    fi
    if [[ -z "$host_env" ]]; then
        host_env=native
    fi
    printf '%s\n' "$host_env"
}

setup_platform_supported() {
    local platform="${1:-}"

    if [[ -z "$platform" ]]; then
        platform="$(setup_current_platform)" || return 1
    fi
    case "$platform" in
        macos|linux-debian)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

setup_unsupported_platform_message() {
    local platform="$1"
    local host_env

    host_env="$(setup_current_host_env)" || return 1

    printf "The setup/check platform path currently supports macOS and Ubuntu/Debian Linux only (BASE_PLATFORM='%s', BASE_HOST_ENV='%s').\n" "$platform" "$host_env"
    if [[ "$host_env" == wsl2 ]]; then
        printf "%s\n" "Ubuntu/Debian under WSL2 uses the Linux source-checkout path; other WSL distributions and native Windows are not supported."
    fi
}

setup_unsupported_install_platform_message() {
    local platform="$1"
    local host_env

    host_env="$(setup_current_host_env)" || return 1

    printf "The setup platform path currently supports macOS and Ubuntu/Debian Linux only (BASE_PLATFORM='%s', BASE_HOST_ENV='%s').\n" "$platform" "$host_env"
    if [[ "$host_env" == wsl2 ]]; then
        printf "%s\n" "Ubuntu/Debian under WSL2 uses the Linux source-checkout path; other WSL distributions and native Windows are not supported."
    fi
}

setup_allow_test_hooks() {
    [[ "${BASE_TEST_MODE:-false}" == true || "${CI:-false}" == true ]]
}

setup_reject_test_hook_if_disallowed() {
    local variable_name="$1"

    setup_allow_test_hooks && return 0
    fatal_error "$variable_name is a test-only setup override. Set BASE_TEST_MODE=true or CI=true to use it."
}

setup_recovery_base_bash_libraries() {
    printf "%s\n" "Clone basefoundry/base-bash-libs next to Base, install it with 'brew install basefoundry/base/base-bash-libs', or set BASE_BASH_LIBS_DIR."
}

setup_recovery_project_layer() {
    printf "%s\n" "Review the Python error above, then rerun 'basectl setup -v' for more detail."
}

setup_notify_completion() {
    local exit_code="$1"
    local current_seconds
    local elapsed_seconds=0
    local message title
    local min_seconds

    setup_notifications_enabled || return 0
    setup_is_dry_run && return 0
    [[ "$OSTYPE" == darwin* ]] || return 0
    if ! command -v osascript >/dev/null 2>&1; then
        if setup_notifications_forced; then
            log_warn "Setup notification was requested, but 'osascript' is not available on this Mac."
        fi
        return 0
    fi

    min_seconds="$(setup_notify_min_seconds)"
    if ! [[ "$min_seconds" =~ ^[0-9]+$ ]]; then
        min_seconds=30
    fi
    if [[ -n "${BASE_SETUP_START_TIME:-}" && "$BASE_SETUP_START_TIME" =~ ^[0-9]+$ ]]; then
        current_seconds="$(setup_epoch_seconds)" || current_seconds="$BASE_SETUP_START_TIME"
        elapsed_seconds=$((current_seconds - BASE_SETUP_START_TIME))
    fi
    if ! setup_notifications_forced && ((elapsed_seconds < min_seconds)); then
        return 0
    fi

    if ((exit_code == 0)); then
        title="Base setup complete"
        message="Base CLI setup completed successfully."
    else
        title="Base setup failed"
        message="Base CLI setup failed. Check the terminal for details."
    fi

    osascript -e 'on run argv
display notification (item 2 of argv) with title (item 1 of argv)
end run' "$title" "$message" >/dev/null 2>&1 || true
}

setup_command_path() {
    command -v "$1" 2>/dev/null || return 1
}

setup_current_machine() {
    uname -m 2>/dev/null || printf 'unknown\n'
}

setup_executable_architecture() {
    local output path="$1"

    [[ -n "$path" ]] || return 1
    command -v file >/dev/null 2>&1 || return 1
    output="$(file -L "$path" 2>/dev/null || true)"
    case "$output" in
        *x86_64*arm64*|*arm64*x86_64*)
            printf '%s\n' "universal"
            ;;
        *arm64*)
            printf '%s\n' "arm64"
            ;;
        *x86_64*)
            printf '%s\n' "x86_64"
            ;;
        *)
            return 1
            ;;
    esac
}

setup_rosetta_translation_state() {
    local translated

    [[ "$(setup_current_platform)" == macos ]] || {
        printf '%s\n' "n/a"
        return 0
    }

    translated="$(sysctl -in sysctl.proc_translated 2>/dev/null || true)"
    case "$translated" in
        1)
            printf '%s\n' "yes"
            ;;
        0)
            printf '%s\n' "no"
            ;;
        *)
            printf '%s\n' "unknown"
            ;;
    esac
}

setup_gh_version_line() {
    local version

    version="$(gh --version 2>/dev/null | head -n 1)" || return 1
    [[ -n "$version" ]] || return 1
    printf '%s\n' "$version"
}

setup_print_runtime_chain_summary() {
    local brew_bin brew_prefix gh_arch gh_bin gh_version home_path host_env platform pyvenv_cfg python_arch python_bin shell_machine shell_path translated venv_dir

    platform="$(setup_current_platform 2>/dev/null || printf 'unsupported\n')"
    host_env="$(setup_current_host_env)" || return 1
    shell_path="${BASH:-}"
    [[ -n "$shell_path" ]] || shell_path="$(setup_command_path bash 2>/dev/null || true)"
    shell_machine="$(setup_current_machine)"
    translated="$(setup_rosetta_translation_state)"
    venv_dir="$(setup_venv_dir)"
    python_bin="$venv_dir/bin/python"

    log_info "Runtime chain: BASE_OS=${BASE_OS:-unknown} BASE_PLATFORM=$platform BASE_HOST_ENV=$host_env BASE_HOST=${BASE_HOST:-unknown}"
    log_info "Shell: path=${shell_path:-unknown} version=${BASH_VERSION:-unknown} machine=${shell_machine:-unknown} translated=${translated:-unknown}"

    if [[ -x "$python_bin" ]]; then
        pyvenv_cfg="$venv_dir/pyvenv.cfg"
        python_arch="$(setup_python_machine "$python_bin" 2>/dev/null || setup_executable_architecture "$python_bin" 2>/dev/null || true)"
        home_path="$(setup_pyvenv_cfg_value home "$pyvenv_cfg" 2>/dev/null || true)"
        log_info "Python: path=$python_bin machine=${python_arch:-unknown} home=${home_path:-unknown}"
    else
        log_info "Python: path=$python_bin status=missing"
    fi

    if [[ "$platform" == macos ]]; then
        if brew_bin="$(setup_find_brew_bin 2>/dev/null)"; then
            brew_prefix="$(setup_homebrew_prefix 2>/dev/null || true)"
            log_info "Homebrew: path=$brew_bin prefix=${brew_prefix:-unknown}"
        else
            log_info "Homebrew: status=missing"
        fi
    fi

    if gh_bin="$(setup_command_path gh 2>/dev/null)"; then
        gh_version="$(setup_gh_version_line 2>/dev/null || true)"
        gh_arch="$(setup_executable_architecture "$gh_bin" 2>/dev/null || true)"
        log_info "GitHub CLI: path=$gh_bin version=${gh_version:-unknown} arch=${gh_arch:-unknown}"
    fi
}

setup_base_bash_libraries_status() {
    case "${BASE_BASH_LIBS_SOURCE:-unknown}" in
        explicit|sibling|homebrew)
            printf '%s\n' "ok"
            ;;
        unknown|*)
            printf '%s\n' "warn"
            ;;
    esac
}

setup_base_bash_libraries_check_message() {
    case "${BASE_BASH_LIBS_SOURCE:-unknown}" in
        explicit)
            printf "Base is using reusable Bash libraries from explicit BASE_BASH_LIBS_DIR '%s'.\n" "${BASE_BASH_LIBS_DIR:-unknown}"
            ;;
        sibling)
            printf "Base is using reusable Bash libraries from sibling base-bash-libs checkout '%s'.\n" "${BASE_BASH_LIBS_DIR:-unknown}"
            ;;
        homebrew)
            printf "Base is using reusable Bash libraries from Homebrew package '%s'.\n" "${BASE_BASH_LIBS_DIR:-unknown}"
            ;;
        *)
            printf "Base Bash library source could not be determined.\n"
            ;;
    esac
}

setup_add_base_bash_libraries_check_result() {
    local recovery=""
    local status

    status="$(setup_base_bash_libraries_status)"
    if [[ "$status" != ok ]]; then
        recovery="$(setup_recovery_base_bash_libraries)"
    fi

    setup_add_check_result_with_status \
        "base_bash_libraries" \
        "$status" \
        "$(setup_base_bash_libraries_check_message)" \
        "$recovery"
}

setup_pythonpath() {
    setup_ensure_cached_paths
    printf '%s\n' "$_BASE_SETUP_PYTHONPATH_CACHE"
}

setup_diagnostics_python_bin() {
    local candidate python_bin venv_dir
    local candidates=()

    setup_ensure_cached_paths
    if command -v python3 >/dev/null 2>&1; then
        candidates+=("$(command -v python3)")
    fi
    if python_bin="$(setup_find_python_bin)"; then
        candidates+=("$python_bin")
    fi
    candidates+=("/usr/bin/python3")
    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate" ]] && env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$candidate" -c 'import base_setup.diagnostics' >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    if python_bin="$(setup_base_venv_python_bin "$venv_dir")" && env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -c 'import base_setup.diagnostics' >/dev/null 2>&1; then
        printf '%s\n' "$python_bin"
        return 0
    fi
    return 1
}

setup_run_diagnostics_json() {
    local python_bin

    python_bin="$(setup_diagnostics_python_bin)" ||
        fatal_error "Python is required to render Base diagnostic JSON."
    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -m base_setup.diagnostics "$@"
}

setup_base_check_metadata_fallback_finding_id() {
    case "$1" in
        homebrew)
            printf '%s\n' "BASE-D001"
            ;;
        xcode_command_line_tools)
            printf '%s\n' "BASE-D002"
            ;;
        python)
            printf '%s\n' "BASE-D003"
            ;;
        base_virtualenv)
            printf '%s\n' "BASE-D004"
            ;;
        pyyaml)
            printf '%s\n' "BASE-D005"
            ;;
        click)
            printf '%s\n' "BASE-D006"
            ;;
        base_bash_libraries)
            printf '%s\n' "BASE-D007"
            ;;
        bash)
            printf '%s\n' "BASE-D008"
            ;;
        python_venv)
            printf '%s\n' "BASE-D009"
            ;;
        git)
            printf '%s\n' "BASE-D010"
            ;;
        gh)
            printf '%s\n' "BASE-D011"
            ;;
        bats)
            printf '%s\n' "BASE-D012"
            ;;
        shellcheck)
            printf '%s\n' "BASE-D013"
            ;;
        jq)
            printf '%s\n' "BASE-D014"
            ;;
        go)
            printf '%s\n' "BASE-D015"
            ;;
        *)
            printf '%s\n' "BASE-D000"
            ;;
    esac
}

setup_base_check_metadata_fallback_display_name() {
    case "$1" in
        homebrew)
            printf '%s\n' "Homebrew"
            ;;
        xcode_command_line_tools)
            printf '%s\n' "Xcode Command Line Tools"
            ;;
        python)
            printf '%s\n' "Python"
            ;;
        base_virtualenv)
            printf '%s\n' "Base virtualenv"
            ;;
        pyyaml)
            setup_pyyaml_package
            ;;
        click)
            setup_click_package
            ;;
        base_bash_libraries)
            printf '%s\n' "Base Bash libraries"
            ;;
        bash)
            printf '%s\n' "Bash"
            ;;
        python_venv)
            printf '%s\n' "Python venv support"
            ;;
        git)
            printf '%s\n' "Git"
            ;;
        gh)
            printf '%s\n' "GitHub CLI"
            ;;
        bats)
            printf '%s\n' "BATS"
            ;;
        shellcheck)
            printf '%s\n' "ShellCheck"
            ;;
        jq)
            printf '%s\n' "jq"
            ;;
        go)
            printf '%s\n' "Go"
            ;;
        *)
            printf '%s\n' "$1"
            ;;
    esac
}

setup_base_check_metadata_fallback() {
    local display_name finding_id name

    for name in "$@"; do
        finding_id="$(setup_base_check_metadata_fallback_finding_id "$name")"
        display_name="$(setup_base_check_metadata_fallback_display_name "$name")"
        printf '%s\t%s\t%s\n' "$name" "$finding_id" "$display_name"
    done
}

setup_base_check_metadata() {
    local args=()
    local name python_bin

    for name in "$@"; do
        args+=(--name "$name")
    done

    if python_bin="$(setup_diagnostics_python_bin)"; then
        setup_ensure_cached_paths
        if env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$python_bin" -m base_setup.diagnostics base-check-metadata "${args[@]}"; then
            return 0
        fi
    fi

    setup_base_check_metadata_fallback "$@"
}

setup_resolve_project_manifest() {
    local requested_project="$1"
    local python_bin="$2"
    local output_name_var="$3"
    local output_root_var="$4"
    local output_manifest_var="$5"
    local protocol_output result_manifest result_name result_root

    if [[ -n "${BASE_SETUP_MANIFEST:-}" ]]; then
        if [[ -z "$requested_project" ]]; then
            setup_ensure_cached_paths
            protocol_output="$(
                env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
                    "$python_bin" -m base_projects manifest "$BASE_SETUP_MANIFEST" --format command-protocol
            )" || return $?
            base_command_protocol_decode_one project-reference "$protocol_output" || return 1
            result_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
            result_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
            result_manifest="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
        else
            result_name="$requested_project"
            result_manifest="$BASE_SETUP_MANIFEST"
            result_root="$(setup_project_root_from_manifest "$result_manifest")" || return 1
        fi
    else
        [[ -n "$requested_project" ]] || requested_project=base
        if [[ "$requested_project" == base ]]; then
            result_name=base
            result_root="$BASE_HOME"
            result_manifest="$BASE_HOME/base_manifest.yaml"
        else
            setup_ensure_cached_paths
            protocol_output="$(
                env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
                    "$python_bin" -m base_projects resolve "$requested_project" --format command-protocol
            )" || return 1
            base_command_protocol_decode_one project-route "$protocol_output" || return 1
            result_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
            result_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
            result_manifest="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
            [[ "$result_name" == "$requested_project" ]] || return 1
        fi
    fi

    [[ -n "$result_name" && -n "$result_root" && -n "$result_manifest" ]] || return 1
    printf -v "$output_name_var" '%s' "$result_name"
    printf -v "$output_root_var" '%s' "$result_root"
    printf -v "$output_manifest_var" '%s' "$result_manifest"
}

setup_project_venv_dir() {
    local project="$1"

    if [[ "$project" != base && -n "${BASE_PROJECT_VENV_DIR:-}" && ( -z "${BASE_PROJECT:-}" || "${BASE_PROJECT:-}" == "$project" ) ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi
    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

setup_project_root_from_manifest() {
    local manifest_path="$1"

    (cd -- "$(dirname -- "$manifest_path")" && pwd -P)
}

setup_resolve_project_route() {
    local project="$1"
    local manifest_path="$2"
    local python_bin="$3"

    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -m base_setup --manifest "$manifest_path" --action route --format command-protocol "$project"
}

setup_project_check_record_path() {
    local project="$1"

    printf '%s\n' "$HOME/.base.d/$project/checks/last.json"
}

setup_record_project_check_result() {
    local checked_at path project="$1" status="$2"

    [[ -n "$project" ]] || return 0
    case "$status" in
        ok|warn|error)
            ;;
        *)
            status=error
            ;;
    esac

    path="$(setup_project_check_record_path "$project")"
    # Keep external date -u here so persisted JSON records carry explicit UTC
    # without mutating shell TZ; Bash printf time formatting follows local time.
    checked_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')" || return 0
    setup_run_diagnostics_json record-check \
        --project "$project" \
        --status "$status" \
        --checked-at "$checked_at" \
        --output-path "$path" >/dev/null || return 0
}

setup_user_config_path() {
    printf '%s\n' "$HOME/.base.d/config.yaml"
}

setup_seed_user_config() {
    local config_dir config_path temp_file

    config_path="$(setup_user_config_path)"
    if [[ -e "$config_path" || -L "$config_path" ]]; then
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would create Base user config at '$config_path'."
        return 0
    fi

    config_dir="$(dirname "$config_path")"
    safe_mkdir -p "$config_dir"
    if [[ -e "$config_path" || -L "$config_path" ]]; then
        return 0
    fi

    temp_file="$(mktemp "$config_path.XXXXXX")" ||
        fatal_error "Unable to create temporary Base user config for '$config_path'."
    {
        printf 'workspace:\n'
        printf '  root: ~/work\n'
    } > "$temp_file" || {
        rm -f -- "$temp_file"
        fatal_error "Unable to write Base user config '$config_path'."
    }
    mv -n -- "$temp_file" "$config_path" || {
        rm -f -- "$temp_file"
        fatal_error "Unable to create Base user config '$config_path'."
    }
    if [[ -e "$temp_file" ]]; then
        rm -f -- "$temp_file"
        return 0
    fi
    log_info "Created Base user config at '$config_path'."
}

setup_project_venv_python_bin() {
    local project="$1"
    local venv_dir

    venv_dir="$(setup_project_venv_dir "$project")"
    [[ -x "$venv_dir/bin/python" ]] || return 1
    printf '%s\n' "$venv_dir/bin/python"
}

setup_recovery_project_venv() {
    local project="$1"
    local project_root="${2:-}"
    local project_venv_dir="${3:-}"

    if [[ "$project" != base && -n "$project_root" && "$project_venv_dir" == "$project_root/.venv" ]]; then
        printf "Run 'basectl setup %s --recreate-venv' to back up and recreate the project virtual environment. Base now defaults non-Base project virtual environments to '%s'; to keep using '%s', set python.venv_location: external in base_manifest.yaml or export BASE_PROJECT_VENV_DIR.\n" "$project" "$project_venv_dir" "$HOME/.base.d/$project/.venv"
        return 0
    fi
    printf "Run 'basectl setup %s --recreate-venv' to back up and recreate the project virtual environment.\n" "$project"
}

setup_doctor_visual_status_enabled() {
    [[ "${BASE_SETUP_DOCTOR_NO_COLOR:-false}" != true ]] || return 1
    [[ -z "${NO_COLOR:-}" ]] || return 1
    [[ -n "${TERM:-}" && "${TERM:-}" != dumb ]] || return 1
    [[ -t 1 ]]
}

setup_doctor_status_visual_parts() {
    local status="$1"
    local label color padding

    case "$status" in
        ok)
            label="✓ ok"
            color=$'\033[0;32m'
            padding="   "
            ;;
        warn)
            label="! warn"
            color=$'\033[0;33m'
            padding=" "
            ;;
        error)
            label="✗ error"
            color=$'\033[0;31m'
            padding=""
            ;;
        *)
            label="$status"
            color=""
            padding=""
            ;;
    esac

    printf '%s\t%s\t%s\n' "$label" "$color" "$padding"
}

setup_print_doctor_finding() {
    local status="$1"
    local finding_id="$2"
    local name="$3"
    local message="$4"
    local fix="${5:-}"
    local color fix_indent label padding reset

    if setup_doctor_visual_status_enabled; then
        IFS=$'\t' read -r label color padding <<<"$(setup_doctor_status_visual_parts "$status")"
        reset=$'\033[0m'
        printf '%b%s%b%s  %-9s  %-26s  %s\n' "$color" "$label" "$reset" "$padding" "$finding_id" "$name" "$message"
        fix_indent=9
    else
        printf '%-5s  %-9s  %-26s  %s\n' "$status" "$finding_id" "$name" "$message"
        fix_indent=7
    fi
    if [[ -n "$fix" ]]; then
        printf '%*sFix: %s\n' "$fix_indent" '' "$fix"
    fi
}

setup_print_project_check_json_with_venv() {
    local precheck_json="$1"
    local ok="$2"
    local message="$3"
    local fix="$4"
    local project="$5"
    local status

    status="$(setup_diagnostic_status_from_ok "$ok")"
    setup_run_diagnostics_json project-venv-check-json \
        --project "$project" \
        --status "$status" \
        --message "$message" \
        --fix "$fix" \
        --precheck-json "$precheck_json"
}

setup_print_project_venv_check_json() {
    local ok="$1"
    local message="$2"
    local fix="$3"
    local project="$4"
    local status

    status="$(setup_diagnostic_status_from_ok "$ok")"
    setup_run_diagnostics_json project-venv-check-json \
        --project "$project" \
        --status "$status" \
        --message "$message" \
        --fix "$fix"
}

setup_print_project_venv_doctor_json() {
    local precheck_json="$1"
    local status="$2"
    local message="$3"
    local fix="$4"

    setup_run_diagnostics_json project-venv-doctor-json \
        --status "$status" \
        --message "$message" \
        --fix "$fix" \
        --precheck-json "$precheck_json"
}

setup_run_project_pre_venv_layer() {
    local action="$1"
    local output_format="$2"
    local manifest_path="$3"
    local project="$4"
    local project_root="$5"
    local project_venv_dir="$6"
    local remote_network="${7:-${BASE_SETUP_REMOTE_NETWORK:-}}"
    local python_bin venv_dir
    local args=()

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || fatal_error "Base virtual environment Python was not found at '$venv_dir/bin/python'. $(setup_recovery_venv)"

    args+=(--manifest "$manifest_path")
    args+=(--action "$action")
    args+=(--format "$output_format")
    if [[ "$remote_network" == true ]]; then
        args+=(--remote-network)
    fi
    args+=("$project")

    env \
        BASE_HOME="$BASE_HOME" \
        BASE_PROJECT="$project" \
        BASE_PROJECT_ROOT="$project_root" \
        BASE_PROJECT_MANIFEST="$manifest_path" \
        BASE_PROJECT_VENV_DIR="$project_venv_dir" \
        PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -m base_setup "${args[@]}"
}

setup_run_project_artifact_setup() {
    setup_run_project_artifact_layer setup text
}

setup_run_project_bootstrap_layer() {
    local manifest_path="$1"
    local project="$2"
    local output_format="$3"
    local project_root="$4"
    local project_venv_dir="$5"
    local python_bin venv_dir
    local args=()
    local project_env_args=()

    if setup_is_dry_run && ! setup_base_python_package_installed "$(setup_pyyaml_package)"; then
        log_info "[DRY-RUN] Would bootstrap project Python runtime after PyYAML is installed."
        return 0
    fi

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || fatal_error "Base virtual environment Python was not found at '$venv_dir/bin/python'. $(setup_recovery_venv)"

    if setup_is_dry_run; then
        args+=(--dry-run)
    fi
    args+=(--manifest "$manifest_path" --action bootstrap "$project")

    if [[ "$output_format" != json ]]; then
        log_info "Bootstrapping Python runtime for project '$project'."
    fi

    setup_ensure_cached_paths
    if [[ "$project" == base ]]; then
        project_env_args=(
            -u BASE_PROJECT
            -u BASE_PROJECT_ROOT
            -u BASE_PROJECT_MANIFEST
            -u BASE_PROJECT_VENV_DIR
        )
    fi
    if setup_project_recreate_venv_enabled "$project"; then
        env "${project_env_args[@]}" \
            BASE_HOME="$BASE_HOME" \
            BASE_PROJECT="$project" \
            BASE_PROJECT_ROOT="$project_root" \
            BASE_PROJECT_MANIFEST="$manifest_path" \
            BASE_PROJECT_VENV_DIR="$project_venv_dir" \
            BASE_SETUP_RECREATE_PROJECT_VENV=true \
            PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$python_bin" -m base_setup "${args[@]}"
    else
        env "${project_env_args[@]}" \
            BASE_HOME="$BASE_HOME" \
            BASE_PROJECT="$project" \
            BASE_PROJECT_ROOT="$project_root" \
            BASE_PROJECT_MANIFEST="$manifest_path" \
            BASE_PROJECT_VENV_DIR="$project_venv_dir" \
            PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$python_bin" -m base_setup "${args[@]}"
    fi
}

setup_run_project_artifact_layer() {
    local action="$1"
    local output_format="$2"
    local exit_code manifest_path platform precheck_json project project_requires_python project_uses_uv_manager project_venv_dir python_bin remote_network resolved_root route_output venv_dir
    local args=()
    local project_env_args=()

    if setup_is_dry_run && ! setup_base_python_package_installed "$(setup_pyyaml_package)"; then
        log_info "[DRY-RUN] Would run Python project setup layer after PyYAML is installed."
        return 0
    fi

    project="${BASE_SETUP_PROJECT_NAME:-}"
    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || fatal_error "Base virtual environment Python was not found at '$venv_dir/bin/python'. $(setup_recovery_venv)"
    setup_resolve_project_manifest "$project" "$python_bin" project resolved_root manifest_path || {
        log_error "Unable to resolve Base project '$project'."
        log_error "Run 'basectl projects list' to see projects Base can discover."
        return 1
    }
    if [[ "$project" != base ]]; then
        if [[ "$output_format" != json ]]; then
            if [[ "$action" == setup ]]; then
                log_info "Resolved project '$project' at '$resolved_root'."
            else
                log_debug "Resolved project '$project' at '$resolved_root'."
            fi
        fi
    fi
    route_output="$(setup_resolve_project_route "$project" "$manifest_path" "$python_bin")" || {
        log_error "Unable to resolve Base project environment for '$project'."
        return 1
    }
    base_command_protocol_decode_one project-setup-route "$route_output" || {
        log_error "Python project routing returned invalid metadata for '$project'."
        return 1
    }
    project="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    resolved_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    export BASE_CLI_HISTORY_PROJECT="$project"
    export BASE_CLI_HISTORY_PROJECT_ROOT="$resolved_root"
    export BASE_CLI_HISTORY_MANIFEST="$manifest_path"
    project_venv_dir="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    project_uses_uv_manager="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    project_requires_python="${BASE_COMMAND_PROTOCOL_FIELDS[requires_project_python]}"
    if [[ -z "$project" || -z "$resolved_root" || -z "$manifest_path" || -z "$project_venv_dir" ]]; then
        log_error "Python project routing returned incomplete metadata for '$project'."
        return 1
    fi
    if [[ "$project_uses_uv_manager" != true && "$project_uses_uv_manager" != false ]]; then
        log_error "Python project routing returned invalid uv-manager metadata for '$project'."
        return 1
    fi
    if [[ "$project_requires_python" != true && "$project_requires_python" != false ]]; then
        log_error "Python project routing returned invalid project-Python metadata for '$project'."
        return 1
    fi
    if [[ "$project" == base ]]; then
        project_env_args=(
            -u BASE_PROJECT
            -u BASE_PROJECT_ROOT
            -u BASE_PROJECT_MANIFEST
            -u BASE_PROJECT_VENV_DIR
        )
    fi

    if setup_is_dry_run; then
        args+=(--dry-run)
    fi
    args+=(--manifest "$manifest_path")
    args+=(--action "$action")
    if [[ "$action" == check || "$action" == doctor ]]; then
        args+=(--format "$output_format")
    fi
    remote_network=false
    if [[ "${BASE_SETUP_REMOTE_NETWORK:-}" == true && ( "$action" == check || "$action" == doctor ) ]]; then
        args+=(--remote-network)
        remote_network=true
    fi
    args+=("$project")
    platform="$(setup_current_platform)" || return 1

    if [[ "$output_format" != json ]]; then
        if [[ "$action" == setup ]]; then
            log_info "Running Python project $action layer."
        else
            log_debug "Running Python project $action layer."
        fi
    fi

    if [[ "$action" == setup && "$project_requires_python" == true && "$project_uses_uv_manager" != true ]]; then
        setup_run_project_bootstrap_layer "$manifest_path" "$project" "$output_format" "$resolved_root" "$project_venv_dir"
        exit_code=$?
        if ((exit_code)); then
            log_error "$(setup_recovery_project_layer)"
            log_error "Python project $action layer failed."
            return "$exit_code"
        fi
    fi

    if [[ "$project_requires_python" == true && "$project_uses_uv_manager" != true ]] && ! setup_virtualenv_healthy_path "$project_venv_dir"; then
        if setup_is_dry_run && [[ "$action" == setup ]]; then
            log_info "[DRY-RUN] Would run Python project setup layer through base-wrapper for project '$project'."
            return 0
        fi
        if [[ "$output_format" == json ]]; then
            if [[ "$action" == doctor ]]; then
                precheck_json="$(setup_run_project_pre_venv_layer predoctor json "$manifest_path" "$project" "$resolved_root" "$project_venv_dir" "$remote_network")" || true
                [[ -n "$precheck_json" ]] || precheck_json="[]"
                setup_print_project_venv_doctor_json \
                    "$precheck_json" \
                    "error" \
                    "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
                    "$(setup_recovery_project_venv "$project" "$resolved_root" "$project_venv_dir")"
            else
                precheck_json="$(setup_run_project_pre_venv_layer precheck json "$manifest_path" "$project" "$resolved_root" "$project_venv_dir" "$remote_network")" || true
                [[ -n "$precheck_json" ]] || precheck_json="[]"
                setup_print_project_check_json_with_venv \
                    "$precheck_json" \
                    false \
                    "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
                    "$(setup_recovery_project_venv "$project" "$resolved_root" "$project_venv_dir")" \
                    "$project"
            fi
        elif [[ "$action" == doctor ]]; then
            setup_run_project_pre_venv_layer predoctor text "$manifest_path" "$project" "$resolved_root" "$project_venv_dir" "$remote_network" || true
            setup_print_doctor_finding \
                "error" \
                "BASE-P050" \
                "Project virtualenv" \
                "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
                "$(setup_recovery_project_venv "$project" "$resolved_root" "$project_venv_dir")"
        elif [[ "$action" == check ]]; then
            setup_run_project_pre_venv_layer precheck text "$manifest_path" "$project" "$resolved_root" "$project_venv_dir" "$remote_network" || true
            log_error "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
            log_error "$(setup_recovery_project_venv "$project" "$resolved_root" "$project_venv_dir")"
        else
            log_warn "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
            log_warn "$(setup_recovery_project_venv "$project" "$resolved_root" "$project_venv_dir")"
        fi
        return 1
    fi

    if [[ "$project_uses_uv_manager" == true || "$project_requires_python" != true ]]; then
        env "${project_env_args[@]}" \
            BASE_HOME="$BASE_HOME" \
            BASE_PLATFORM="$platform" \
            BASE_PROJECT="$project" \
            BASE_PROJECT_ROOT="$resolved_root" \
            BASE_PROJECT_MANIFEST="$manifest_path" \
            BASE_PROJECT_VENV_DIR="$project_venv_dir" \
            PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$python_bin" -m base_setup "${args[@]}"
    else
        env "${project_env_args[@]}" \
            BASE_PLATFORM="$platform" \
            BASE_PROJECT="$project" \
            BASE_PROJECT_ROOT="$resolved_root" \
            BASE_PROJECT_MANIFEST="$manifest_path" \
            BASE_PROJECT_VENV_DIR="$project_venv_dir" \
            "$BASE_HOME/bin/base-wrapper" --project "$project" base_setup "${args[@]}"
    fi
    exit_code=$?

    if ((exit_code)) && [[ "$action" == setup ]]; then
        log_error "$(setup_recovery_project_layer)"
        log_error "Python project $action layer failed."
        return "$exit_code"
    fi
    if ((exit_code)) && [[ "$action" == check ]]; then
        log_error "Python project check layer found missing requirements."
        return "$exit_code"
    fi
    if ((exit_code)); then
        return "$exit_code"
    fi
}

setup_run_project_artifact_check() {
    setup_run_project_artifact_layer check text
}

setup_run_project_artifact_check_json() {
    if [[ -n "${1:-}" ]]; then
        BASE_SETUP_REMOTE_NETWORK="$1"
        export BASE_SETUP_REMOTE_NETWORK
    fi
    setup_run_project_artifact_layer check json
}

setup_run_project_artifact_doctor() {
    setup_run_project_artifact_layer doctor text
}

setup_run_project_artifact_doctor_json() {
    if [[ -n "${1:-}" ]]; then
        BASE_SETUP_REMOTE_NETWORK="$1"
        export BASE_SETUP_REMOTE_NETWORK
    fi
    setup_run_project_artifact_layer doctor json
}

setup_wait_for_base_check_probes() {
    local failed=0
    local pid

    for pid in "$@"; do
        wait "$pid" || failed=1
    done

    return "$failed"
}

setup_collect_platform_base_check_results() {
    local platform

    platform="$(setup_current_platform)" || return 1
    case "$platform" in
        macos)
            setup_collect_macos_base_check_results "$@"
            ;;
        linux-debian)
            setup_collect_linux_debian_base_check_results "$@"
            ;;
        *)
            fatal_error "$(setup_unsupported_platform_message "$platform")"
            ;;
    esac
}

setup_collect_base_check_results() {
    setup_clear_check_results
    if setup_ci_runtime_only; then
        setup_collect_ci_runtime_check_results
        return $?
    fi

    setup_collect_platform_base_check_results "$@"
}

setup_print_check_text_results() {
    local count i status

    count="${#_BASE_SETUP_CHECK_NAMES[@]}"
    for ((i = 0; i < count; i++)); do
        status="${_BASE_SETUP_CHECK_STATUSES[$i]:-$(setup_diagnostic_status_from_ok "${_BASE_SETUP_CHECK_OK[$i]}")}"
        case "$status" in
            ok)
                log_info "${_BASE_SETUP_CHECK_MESSAGES[$i]}"
                if [[ -n "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}" ]]; then
                    log_debug "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}"
                fi
                ;;
            warn)
                log_warn "${_BASE_SETUP_CHECK_MESSAGES[$i]}"
                if [[ -n "${_BASE_SETUP_CHECK_RECOVERIES[$i]}" ]]; then
                    log_warn "${_BASE_SETUP_CHECK_RECOVERIES[$i]}"
                fi
                ;;
            error)
                log_error "${_BASE_SETUP_CHECK_MESSAGES[$i]}"
                if [[ -n "${_BASE_SETUP_CHECK_RECOVERIES[$i]}" ]]; then
                    log_error "${_BASE_SETUP_CHECK_RECOVERIES[$i]}"
                fi
                ;;
            *)
                fatal_error "Invalid Base check status '$status'."
                ;;
        esac
    done
}

setup_check_result_status() {
    local index="$1"
    local status

    status="${_BASE_SETUP_CHECK_STATUSES[$index]:-}"
    if [[ -z "$status" ]]; then
        status="$(setup_diagnostic_status_from_ok "${_BASE_SETUP_CHECK_OK[$index]}")"
    fi
    printf '%s\n' "$status"
}

setup_check_result_recovery() {
    local index="$1"
    local status

    status="$(setup_check_result_status "$index")"
    if [[ "$status" == ok ]]; then
        printf '\n'
        return 0
    fi

    printf '%s\n' "${_BASE_SETUP_CHECK_RECOVERIES[$index]}"
}

setup_write_collected_check_result_files() {
    local count i output_dir="$1" output_path

    mkdir -p -- "$output_dir" || fatal_error "Unable to create Base check result directory '$output_dir'."

    count="${#_BASE_SETUP_CHECK_NAMES[@]}"
    for ((i = 0; i < count; i++)); do
        output_path="$output_dir/check-$i.result"
        setup_write_check_result_file \
            "$output_path" \
            "${_BASE_SETUP_CHECK_NAMES[$i]}" \
            "${_BASE_SETUP_CHECK_OK[$i]}" \
            "${_BASE_SETUP_CHECK_MESSAGES[$i]}" \
            "${_BASE_SETUP_CHECK_RECOVERIES[$i]}" \
            "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}" \
            "$(setup_check_result_status "$i")"
        printf '%s\n' "$output_path"
    done
}

setup_run_check() {
    local missing=0
    local project="${BASE_SETUP_PROJECT_NAME:-}"

    setup_collect_base_check_results fatal || missing=1
    setup_print_check_text_results

    if setup_profiles_enabled; then
        setup_run_base_dev_layer check || missing=1
    fi

    if [[ -n "$project" ]]; then
        setup_run_project_artifact_check || missing=1
    fi

    if ((missing == 0)); then
        setup_record_project_check_result "$project" ok
        if [[ -n "$project" ]]; then
            log_info "Base CLI environment and project '$project' check passed."
        else
            log_info "Base CLI environment check passed."
        fi
        return 0
    fi

    setup_record_project_check_result "$project" error
    if [[ -n "$project" ]]; then
        log_error "Base CLI environment or project '$project' check found missing requirements."
        log_error "Review the specific Fix lines above and rerun 'basectl check $project' after resolving the missing requirements."
    else
        log_error "Base CLI environment check found missing requirements."
        log_error "Review the specific Fix lines above and rerun 'basectl check' after resolving the missing requirements."
    fi
    return 1
}

setup_diagnostic_status_from_ok() {
    if [[ "$1" == true ]]; then
        printf '%s\n' "ok"
    else
        printf '%s\n' "error"
    fi
}

setup_run_check_json() {
    local args=()
    local checked_at=""
    local check_result_dir check_result_file check_result_paths
    local profile_json=""
    local project="${BASE_SETUP_PROJECT_NAME:-}"
    local project_json=""
    local remote_network="${1:-${BASE_SETUP_REMOTE_NETWORK:-}}"

    setup_collect_base_check_results warn || true

    if setup_profiles_enabled; then
        if ! profile_json="$(setup_run_base_dev_layer check --format json)"; then
            if [[ -z "$profile_json" ]]; then
                return 1
            fi
        fi
    fi

    if [[ -n "$project" ]]; then
        if ! project_json="$(setup_run_project_artifact_check_json "$remote_network")"; then
            if [[ -z "$project_json" ]]; then
                return 1
            fi
        fi
        # Keep external date -u here so persisted JSON records carry explicit UTC
        # without mutating shell TZ; Bash printf time formatting follows local time.
        checked_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')" || return 1
    fi

    args+=(check-json)
    if [[ -n "$project" ]]; then
        args+=(--project "$project")
    fi
    std_make_temp_dir check_result_dir base-check-json ||
        fatal_error "Unable to create temporary Base check JSON result directory."
    check_result_paths="$(setup_write_collected_check_result_files "$check_result_dir")" || return 1
    if [[ -n "$check_result_paths" ]]; then
        while IFS= read -r check_result_file; do
            args+=(--check-result-file "$check_result_file")
        done <<<"$check_result_paths"
    fi
    if setup_profiles_enabled; then
        args+=(--embedded-payload "$(setup_profile_json_key checks)" "$profile_json")
    fi
    if [[ -n "$project" ]]; then
        args+=(--embedded-payload "project_checks" "$project_json")
        args+=(--record-path "$(setup_project_check_record_path "$project")" --checked-at "$checked_at")
    fi
    setup_run_diagnostics_json "${args[@]}"
}

setup_run_platform_install() {
    local platform

    platform="$(setup_current_platform)" || return 1
    case "$platform" in
        macos)
            setup_run_macos_install
            ;;
        linux-debian)
            setup_run_linux_debian_install
            ;;
        *)
            fatal_error "$(setup_unsupported_install_platform_message "$platform")"
            ;;
    esac
}

setup_run_install() {
    if setup_ci_runtime_only; then
        setup_run_ci_runtime_install
        return $?
    fi

    setup_run_platform_install
}
