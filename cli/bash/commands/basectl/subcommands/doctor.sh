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
  basectl doctor [project] [options]

Options:
  --dev       Include manifest-declared developer prerequisite checks.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Diagnose the local Base CLI environment and, when provided, project artifacts.
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
    local dev_errors=0 errors=0 project=""

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
                if [[ "$1" == -* ]]; then
                    print_error "Unknown option '$1'."
                    base_doctor_subcommand_usage >&2
                    return 2
                fi
                if [[ -n "$project" ]]; then
                    print_error "The 'doctor' command accepts at most one project name."
                    base_doctor_subcommand_usage >&2
                    return 2
                fi
                project="$1"
                ;;
        esac
        shift
    done

    BASE_SETUP_PROJECT_NAME="$project"
    export BASE_SETUP_PROJECT_NAME
    log_debug "Running 'basectl doctor'."
    setup_require_macos

    if [[ -n "$project" ]]; then
        printf "Base doctor for project '%s'\n\n" "$project"
    else
        printf 'Base doctor\n\n'
    fi

    base_doctor_check_homebrew || errors=$((errors + 1))
    base_doctor_check_xcode || errors=$((errors + 1))
    base_doctor_check_python || errors=$((errors + 1))
    base_doctor_check_virtualenv || errors=$((errors + 1))
    base_doctor_check_python_package "$(setup_pyyaml_package)" || errors=$((errors + 1))
    base_doctor_check_python_package "$(setup_click_package)" || errors=$((errors + 1))
    if setup_dev_dependencies_enabled; then
        setup_run_base_dev_layer doctor
        dev_errors=$?
        errors=$((errors + dev_errors))
    fi
    if [[ -n "$project" ]]; then
        setup_run_project_artifact_doctor
        errors=$((errors + $?))
    fi

    printf '\n'
    if ((errors == 0)); then
        if [[ -n "$project" ]]; then
            printf "Base doctor found no blocking issues for project '%s'.\n" "$project"
        else
            printf 'Base doctor found no blocking issues.\n'
        fi
        return 0
    fi

    if [[ -n "$project" ]]; then
        printf "Base doctor found %s blocking issue(s) for project '%s'.\n" "$errors" "$project"
    else
        printf 'Base doctor found %s blocking issue(s).\n' "$errors"
    fi
    return 1
}
