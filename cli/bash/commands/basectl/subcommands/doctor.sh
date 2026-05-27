#!/usr/bin/env bash

[[ -n "${_base_doctor_subcommand_sourced:-}" ]] && return
_base_doctor_subcommand_sourced=1
readonly _base_doctor_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_doctor_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl doctor [options]

Options:
  --dev       Include developer/test dependency checks such as BATS and gh.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Diagnose the local Base CLI environment and suggest fixes.
EOF
}

base_doctor_print_finding() {
    local status="$1"
    local name="$2"
    local message="$3"
    local fix="${4:-}"

    printf '%-5s  %-26s  %s\n' "$status" "$name" "$message"
    if [[ -n "$fix" ]]; then
        printf '       Fix: %s\n' "$fix"
    fi
}

base_doctor_check_homebrew() {
    local brew_bin

    if brew_bin="$(setup_find_brew_bin)"; then
        if setup_refresh_brew_path; then
            base_doctor_print_finding "ok" "Homebrew" "Homebrew is installed."
            log_debug "Resolved Homebrew binary: $brew_bin"
            return 0
        fi
        base_doctor_print_finding "error" "Homebrew" \
            "Homebrew is installed, but its bin directory could not be added to PATH." \
            "Check Homebrew installation and PATH."
        return 1
    fi

    base_doctor_print_finding "error" "Homebrew" "Homebrew is not installed." "basectl setup"
    return 1
}

base_doctor_check_xcode() {
    if setup_xcode_tools_installed; then
        base_doctor_print_finding "ok" "Xcode Command Line Tools" "Xcode Command Line Tools are installed."
        return 0
    fi

    base_doctor_print_finding "error" "Xcode Command Line Tools" \
        "Xcode Command Line Tools are not installed." \
        "basectl setup"
    return 1
}

base_doctor_check_python() {
    local formula

    formula="$(setup_python_formula)"
    if setup_python_installed; then
        base_doctor_print_finding "ok" "Python" "Python formula '$formula' is installed via Homebrew."
        return 0
    fi

    base_doctor_print_finding "error" "Python" \
        "Python formula '$formula' is not installed via Homebrew." \
        "basectl setup"
    return 1
}

base_doctor_check_bats() {
    local formula

    formula="$(setup_bats_formula)"
    if setup_bats_installed; then
        base_doctor_print_finding "ok" "BATS" "BATS formula '$formula' is installed via Homebrew."
        return 0
    fi

    base_doctor_print_finding "error" "BATS" \
        "BATS formula '$formula' is not installed via Homebrew." \
        "basectl setup --dev"
    return 1
}

base_doctor_check_github_cli() {
    local gh_bin

    if gh_bin="$(command -v gh 2>/dev/null)"; then
        base_doctor_print_finding "ok" "GitHub CLI" "GitHub CLI is installed."
        log_debug "Resolved GitHub CLI binary: $gh_bin"
        return 0
    fi

    base_doctor_print_finding "error" "GitHub CLI" \
        "GitHub CLI command 'gh' is not installed or not on PATH." \
        "brew install gh"
    return 1
}

base_doctor_check_virtualenv() {
    local venv_dir

    venv_dir="$(setup_venv_dir)"
    if setup_virtualenv_exists; then
        base_doctor_print_finding "ok" "Base virtualenv" "Virtual environment exists at '$venv_dir'."
        return 0
    fi

    base_doctor_print_finding "error" "Base virtualenv" \
        "Virtual environment is missing at '$venv_dir'." \
        "basectl setup"
    return 1
}

base_doctor_check_python_package() {
    local package="$1"

    if setup_base_python_package_installed "$package"; then
        base_doctor_print_finding "ok" "$package" "$(setup_base_python_package_check_message "$package" true)"
        return 0
    fi

    base_doctor_print_finding "error" "$package" \
        "$(setup_base_python_package_check_message "$package" false)" \
        "basectl setup"
    return 1
}

base_doctor_subcommand_main() {
    local errors=0

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_doctor_subcommand_usage
                return 0
                ;;
            --dev)
                setup_enable_dev_dependencies
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                print_error "Unknown option '$1'."
                base_doctor_subcommand_usage >&2
                return 2
                ;;
        esac
        shift
    done

    log_debug "Running 'basectl doctor'."
    setup_require_macos

    printf 'Base doctor\n\n'

    base_doctor_check_homebrew || errors=$((errors + 1))
    base_doctor_check_xcode || errors=$((errors + 1))
    base_doctor_check_python || errors=$((errors + 1))
    if setup_dev_dependencies_enabled; then
        base_doctor_check_bats || errors=$((errors + 1))
        base_doctor_check_github_cli || errors=$((errors + 1))
    fi
    base_doctor_check_virtualenv || errors=$((errors + 1))
    base_doctor_check_python_package "$(setup_pyyaml_package)" || errors=$((errors + 1))
    base_doctor_check_python_package "$(setup_click_package)" || errors=$((errors + 1))

    printf '\n'
    if ((errors == 0)); then
        printf 'Base doctor found no blocking issues.\n'
        return 0
    fi

    printf 'Base doctor found %s blocking issue(s).\n' "$errors"
    return 1
}
