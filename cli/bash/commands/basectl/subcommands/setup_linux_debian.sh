#!/usr/bin/env bash

#
# setup_linux_debian.sh
#     Ubuntu/Debian-specific setup and check helpers for setup_common.sh.
#
# This file is sourced by setup_common.sh. It intentionally preserves the
# existing setup_* function names so setup/check/doctor call sites remain
# behavior-compatible while Linux/Debian ownership moves out of the shared file.
#

[[ -n "${_base_setup_linux_debian_sourced:-}" ]] && return 0
_base_setup_linux_debian_sourced=1
readonly _base_setup_linux_debian_sourced

setup_recovery_linux_python() {
    printf "%s\n" "Install python3 and python3-venv, or set BASE_SETUP_PYTHON_BIN, then rerun 'basectl check'."
}

setup_recovery_linux_apt_package() {
    local display_name="$1"
    local package_name="$2"

    printf "Install %s with 'sudo apt-get install %s', then rerun 'basectl check'.\n" "$display_name" "$package_name"
}

setup_linux_debian_github_cli_install_url() {
    printf '%s\n' "https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian"
}

setup_linux_debian_github_cli_keyring_url() {
    printf '%s\n' "https://cli.github.com/packages/githubcli-archive-keyring.gpg"
}

setup_linux_debian_github_cli_keyring_path() {
    printf '%s\n' "/etc/apt/keyrings/githubcli-archive-keyring.gpg"
}

setup_linux_debian_github_cli_source_path() {
    printf '%s\n' "/etc/apt/sources.list.d/github-cli.list"
}

setup_linux_debian_github_cli_source_line() {
    local arch="${1:-\$(dpkg --print-architecture)}"

    printf 'deb [arch=%s signed-by=%s] https://cli.github.com/packages stable main\n' \
        "$arch" \
        "$(setup_linux_debian_github_cli_keyring_path)"
}

setup_linux_debian_github_cli_install_guidance() {
    printf "Configure GitHub CLI's official Debian/Ubuntu apt repository before installing 'gh': %s.\n" "$(setup_linux_debian_github_cli_install_url)"
}

setup_recovery_linux_github_cli() {
    printf "%s Run 'sudo apt update' and 'sudo apt install gh -y', then rerun 'basectl check'.\n" "$(setup_linux_debian_github_cli_install_guidance)"
}

setup_find_linux_python_bin() {
    if [[ -n "${BASE_SETUP_PYTHON_BIN:-}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_PYTHON_BIN
        [[ -x "${BASE_SETUP_PYTHON_BIN}" ]] || return 1
        printf '%s\n' "${BASE_SETUP_PYTHON_BIN}"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    return 1
}

setup_test_linux_tool_forced_missing() {
    local missing_tools="${BASE_SETUP_TEST_MISSING_LINUX_TOOLS:-}"
    local tool="$1"

    [[ -n "${BASE_SETUP_TEST_MISSING_LINUX_TOOLS+x}" ]] || return 1
    setup_reject_test_hook_if_disallowed BASE_SETUP_TEST_MISSING_LINUX_TOOLS
    case ",$missing_tools," in
        *,"$tool",*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

setup_linux_command_path() {
    local command_name="$1"

    setup_test_linux_tool_forced_missing "$command_name" && return 1
    command -v "$command_name" 2>/dev/null
}

setup_linux_python_venv_available() {
    local python_bin="$1"

    [[ -n "$python_bin" ]] || return 1
    "$python_bin" -m venv --help >/dev/null 2>&1
}

setup_linux_bash_version_supported() {
    local major="${BASH_VERSINFO[0]:-0}"
    local minor="${BASH_VERSINFO[1]:-0}"

    ((major > 4 || (major == 4 && minor >= 2)))
}

setup_add_linux_bash_check_result() {
    if setup_linux_bash_version_supported; then
        setup_add_check_result \
            "bash" \
            true \
            "Bash 4.2+ is available for Base shell runtime." \
            "" \
            "Resolved Bash version: ${BASH_VERSION:-unknown}"
    else
        setup_add_check_result \
            "bash" \
            false \
            "Bash 4.2+ is not available for Base shell runtime." \
            "$(setup_recovery_linux_apt_package Bash bash)"
        return 1
    fi
}

setup_add_linux_python_venv_check_result() {
    local python_bin="$1"

    if setup_linux_python_venv_available "$python_bin"; then
        setup_add_check_result \
            "python_venv" \
            true \
            "Python venv support is available for Ubuntu/Debian runtime checks."
    else
        setup_add_check_result \
            "python_venv" \
            false \
            "Python venv support is not available for Ubuntu/Debian runtime checks." \
            "$(setup_recovery_linux_apt_package python3-venv python3-venv)"
        return 1
    fi
}

setup_add_linux_command_check_result() {
    local command_name="$1"
    local finding_name="$2"
    local display_name="$3"
    local recovery="$4"
    local missing_status="${5:-error}"
    local check_context="${6:-runtime checks}"
    local command_path

    case "$missing_status" in
        warn|error)
            ;;
        *)
            fatal_error "Invalid Linux command check missing status '$missing_status'."
            ;;
    esac

    if command_path="$(setup_linux_command_path "$command_name")"; then
        setup_add_check_result \
            "$finding_name" \
            true \
            "$display_name is available for Ubuntu/Debian $check_context." \
            "" \
            "Resolved $display_name binary: $command_path"
    else
        setup_add_check_result_with_status \
            "$finding_name" \
            "$missing_status" \
            "$display_name is not available for Ubuntu/Debian $check_context." \
            "$recovery"
        [[ "$missing_status" != error ]] && return 0
        return 1
    fi
}

setup_collect_linux_debian_base_check_results() {
    local click_package
    local missing=0
    local pyyaml_package
    local python_bin

    click_package="$(setup_click_package)"
    pyyaml_package="$(setup_pyyaml_package)"
    setup_ensure_cached_paths

    setup_add_linux_bash_check_result || missing=1
    setup_add_base_bash_libraries_check_result

    if python_bin="$(setup_find_linux_python_bin)"; then
        setup_add_check_result \
            "python" \
            true \
            "Python is available for Ubuntu/Debian runtime checks." \
            "" \
            "Resolved Python binary: $python_bin"
    else
        setup_add_check_result \
            "python" \
            false \
            "Python is not available for Ubuntu/Debian runtime checks." \
            "$(setup_recovery_linux_python)"
        missing=1
    fi
    setup_add_linux_python_venv_check_result "$python_bin" || missing=1

    if setup_virtualenv_healthy; then
        setup_add_check_result "base_virtualenv" true "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
    else
        setup_add_check_result \
            "base_virtualenv" \
            false \
            "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
            "$(setup_recovery_venv)"
        missing=1
    fi

    if setup_base_python_package_installed "$pyyaml_package"; then
        setup_add_check_result "pyyaml" true "$(setup_base_python_package_check_message "$pyyaml_package" true)"
    else
        setup_add_check_result \
            "pyyaml" \
            false \
            "$(setup_base_python_package_check_message "$pyyaml_package" false)" \
            "$(setup_recovery_base_python_package)"
        missing=1
    fi

    if setup_base_python_package_installed "$click_package"; then
        setup_add_check_result "click" true "$(setup_base_python_package_check_message "$click_package" true)"
    else
        setup_add_check_result \
            "click" \
            false \
            "$(setup_base_python_package_check_message "$click_package" false)" \
            "$(setup_recovery_base_python_package)"
        missing=1
    fi

    setup_add_linux_command_check_result \
        "git" \
        "git" \
        "Git" \
        "$(setup_recovery_linux_apt_package git git)" || missing=1
    setup_add_linux_command_check_result \
        "gh" \
        "gh" \
        "GitHub CLI 'gh'" \
        "$(setup_recovery_linux_github_cli)" \
        warn \
        "developer tooling checks" || missing=1
    setup_add_linux_command_check_result \
        "bats" \
        "bats" \
        "BATS" \
        "$(setup_recovery_linux_apt_package bats bats)" \
        warn \
        "developer tooling checks" || missing=1
    setup_add_linux_command_check_result \
        "shellcheck" \
        "shellcheck" \
        "ShellCheck" \
        "$(setup_recovery_linux_apt_package shellcheck shellcheck)" \
        warn \
        "developer tooling checks" || missing=1
    setup_add_linux_command_check_result \
        "jq" \
        "jq" \
        "jq" \
        "$(setup_recovery_linux_apt_package jq jq)" \
        warn \
        "developer tooling checks" || missing=1
    setup_add_linux_command_check_result \
        "go" \
        "go" \
        "Go" \
        "$(setup_recovery_linux_apt_package Go golang-go)" \
        warn \
        "developer tooling checks" || missing=1

    return "$missing"
}

setup_linux_debian_apt_packages() {
    printf '%s\n' "bash git python3 python3-venv python3-pip bats shellcheck jq golang-go"
}

setup_linux_debian_apt_update_command() {
    printf '%s\n' "sudo apt-get update"
}

setup_linux_debian_apt_prerequisite_command() {
    printf 'sudo apt-get install -y %s\n' "$(setup_linux_debian_apt_packages)"
}

setup_linux_debian_apt_prerequisites_installed() {
    local package
    local status

    command -v dpkg-query >/dev/null 2>&1 || return 1

    for package in "$@"; do
        status="$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null)" || return 1
        [[ "$status" == "install ok installed" ]] || return 1
    done
}

setup_run_linux_debian_apt_prerequisites() {
    local packages
    local package_args=()

    packages="$(setup_linux_debian_apt_packages)"
    IFS=' ' read -r -a package_args <<<"$packages"

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would run: $(setup_linux_debian_apt_update_command)"
        log_info "[DRY-RUN] Would run: $(setup_linux_debian_apt_prerequisite_command)"
        return 0
    fi

    if setup_linux_debian_apt_prerequisites_installed "${package_args[@]}"; then
        log_info "Ubuntu/Debian apt prerequisites are already installed."
        return 0
    fi

    setup_require_linux_debian_system_consent \
        "Ubuntu/Debian setup can install apt packages, configure package repositories, and run platform bootstraps." || return $?

    log_info "Installing Ubuntu/Debian apt prerequisites."
    sudo apt-get update || return $?
    sudo apt-get install -y "${package_args[@]}" || return $?
}

setup_run_linux_debian_github_cli_prerequisite() {
    local arch
    local keyring_tmp
    local source_tmp

    if setup_linux_command_path gh >/dev/null 2>&1; then
        log_info "GitHub CLI 'gh' is already installed; authentication remains user-owned."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "$(setup_linux_debian_github_cli_install_guidance)"
        log_info "[DRY-RUN] Would run: sudo install -d -m 0755 /etc/apt/keyrings"
        log_info "[DRY-RUN] Would fetch: $(setup_linux_debian_github_cli_keyring_url)"
        log_info "[DRY-RUN] Would run: sudo install -m 0644 <downloaded GitHub CLI keyring> $(setup_linux_debian_github_cli_keyring_path)"
        log_info "[DRY-RUN] Would run: sudo install -d -m 0755 /etc/apt/sources.list.d"
        log_info "[DRY-RUN] Would write apt source: $(setup_linux_debian_github_cli_source_line)"
        log_info "[DRY-RUN] Would run: sudo apt-get update"
        log_info "[DRY-RUN] Would run: sudo apt-get install -y gh"
        return 0
    fi

    setup_require_linux_debian_system_consent \
        "Ubuntu/Debian setup can install apt packages, configure package repositories, and run platform bootstraps." || return $?

    command -v curl >/dev/null 2>&1 || fatal_error "curl is required to install GitHub CLI 'gh' from its official Debian/Ubuntu apt repository."
    command -v dpkg >/dev/null 2>&1 || fatal_error "dpkg is required to configure GitHub CLI's official Debian/Ubuntu apt repository."
    arch="$(dpkg --print-architecture)" || fatal_error "Unable to read Debian architecture for GitHub CLI apt repository setup."
    [[ -n "$arch" ]] || fatal_error "Unable to read Debian architecture for GitHub CLI apt repository setup."

    std_make_temp_file keyring_tmp base-github-cli-keyring || fatal_error "Failed to create a temporary GitHub CLI keyring file."
    std_make_temp_file source_tmp base-github-cli-source || {
        fatal_error "Failed to create a temporary GitHub CLI apt source file."
    }

    if ! curl -fsSL -o "$keyring_tmp" "$(setup_linux_debian_github_cli_keyring_url)"; then
        fatal_error "Failed to download GitHub CLI's official Debian/Ubuntu apt keyring."
    fi
    setup_linux_debian_github_cli_source_line "$arch" >"$source_tmp" || {
        fatal_error "Failed to prepare GitHub CLI apt source configuration."
    }

    log_info "Installing GitHub CLI 'gh' from GitHub CLI's official Debian/Ubuntu apt repository."
    sudo install -d -m 0755 /etc/apt/keyrings || {
        return 1
    }
    sudo install -m 0644 "$keyring_tmp" "$(setup_linux_debian_github_cli_keyring_path)" || {
        return 1
    }
    sudo install -d -m 0755 /etc/apt/sources.list.d || {
        return 1
    }
    sudo install -m 0644 "$source_tmp" "$(setup_linux_debian_github_cli_source_path)" || {
        return 1
    }
    sudo apt-get update || return $?
    sudo apt-get install -y gh || return $?
}

setup_run_linux_debian_install() {
    setup_run_linux_debian_apt_prerequisites || return $?
    if setup_profile_enabled dev; then
        setup_run_linux_debian_github_cli_prerequisite || return $?
    fi
    setup_create_virtualenv
    setup_install_pyyaml
    setup_install_click
    if setup_profiles_enabled; then
        if setup_is_dry_run; then
            setup_run_base_dev_layer setup --dry-run || fatal_error "Python prerequisite profile layer failed."
        else
            setup_run_base_dev_layer setup || fatal_error "Python prerequisite profile layer failed."
        fi
    fi
    setup_run_project_artifact_setup || return $?
    setup_seed_user_config

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Base CLI setup check is complete."
    else
        log_info "Base CLI setup is complete."
    fi
}
