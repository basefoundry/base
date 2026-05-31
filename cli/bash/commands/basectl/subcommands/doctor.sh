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
  --dev                 Include manifest-declared developer prerequisite checks.
  --format <text|json>  Select output format. Defaults to text.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

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

base_doctor_print_json_finding() {
    local trailing_comma="$1"
    local status="$2"
    local name="$3"
    local message="$4"
    local fix="${5:-}"

    printf '    {"status":"%s","name":"%s","message":"%s","fix":"%s"}%s\n' \
        "$(setup_json_escape "$status")" \
        "$(setup_json_escape "$name")" \
        "$(setup_json_escape "$message")" \
        "$(setup_json_escape "$fix")" \
        "$trailing_comma"
}

base_doctor_print_check_json_results() {
    local count fix i status trailing_comma

    count="${#_BASE_SETUP_CHECK_NAMES[@]}"
    for ((i = 0; i < count; i++)); do
        trailing_comma=","
        if ((i == count - 1)); then
            trailing_comma=""
        fi

        fix="${_BASE_SETUP_CHECK_RECOVERIES[$i]}"
        if [[ "${_BASE_SETUP_CHECK_OK[$i]}" == true ]]; then
            status="ok"
            fix=""
            if [[ -n "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}" ]]; then
                log_debug "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}"
            fi
        else
            status="error"
        fi

        base_doctor_print_json_finding \
            "$trailing_comma" \
            "$status" \
            "${_BASE_SETUP_CHECK_NAMES[$i]}" \
            "${_BASE_SETUP_CHECK_MESSAGES[$i]}" \
            "$fix"
    done
}

base_doctor_count_check_errors() {
    local count errors=0 i

    count="${#_BASE_SETUP_CHECK_NAMES[@]}"
    for ((i = 0; i < count; i++)); do
        if [[ "${_BASE_SETUP_CHECK_OK[$i]}" != true ]]; then
            errors=$((errors + 1))
        fi
    done

    printf '%s\n' "$errors"
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

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
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

base_doctor_run_json() {
    local dev_errors=0 dev_json="[]" errors=0
    local project="$1"
    local project_errors=0 project_json="[]"

    setup_collect_base_check_results warn || true
    errors="$(base_doctor_count_check_errors)"

    if setup_dev_dependencies_enabled; then
        if dev_json="$(setup_run_base_dev_layer doctor --format json)"; then
            dev_errors=0
        else
            dev_errors=$?
            [[ -n "$dev_json" ]] || dev_json="[]"
            errors=$((errors + dev_errors))
        fi
    fi

    if [[ -n "$project" ]]; then
        if project_json="$(setup_run_project_artifact_doctor_json)"; then
            project_errors=0
        else
            project_errors=$?
            [[ -n "$project_json" ]] || project_json="[]"
            errors=$((errors + project_errors))
        fi
    fi

    printf '{\n'
    printf '  "ok": %s' "$([[ "$errors" -eq 0 ]] && printf true || printf false)"
    if [[ -n "$project" ]]; then
        printf ',\n'
        printf '  "project": "%s"' "$(setup_json_escape "$project")"
    fi
    printf ',\n'
    printf '  "findings": [\n'
    base_doctor_print_check_json_results
    printf '  ]'
    if setup_dev_dependencies_enabled || [[ -n "$project" ]]; then
        printf ',\n'
    else
        printf '\n'
    fi
    if setup_dev_dependencies_enabled; then
        setup_print_json_property_value "dev_findings" "$dev_json"
        if [[ -n "$project" ]]; then
            printf ',\n'
        else
            printf '\n'
        fi
    fi
    if [[ -n "$project" ]]; then
        setup_print_json_property_value "project_findings" "$project_json"
    fi
    printf '}\n'

    [[ "$errors" -eq 0 ]]
}

base_doctor_subcommand_main() {
    local dev_errors=0 errors=0 output_format="text" project=""

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_doctor_subcommand_usage
                return 0
                ;;
            --dev)
                setup_enable_dev_dependencies
                ;;
            --format)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--format' requires an argument."
                    base_doctor_subcommand_usage >&2
                    return 2
                fi
                case "$1" in
                    text|json)
                        output_format="$1"
                        ;;
                    *)
                        print_error "Unsupported doctor output format '$1'."
                        base_doctor_subcommand_usage >&2
                        return 2
                        ;;
                esac
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

    if [[ "$output_format" == json ]]; then
        base_doctor_run_json "$project"
        return $?
    fi

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
