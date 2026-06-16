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
  --profile <list>      Include named prerequisite profiles. Known profiles: dev, sre, ai.
  --format <text|json>  Select output format. Defaults to text.
  --manifest <path>     Use a specific base_manifest.yaml path for project diagnostics.
  --remote-network      Opt in to bounded project Git origin reachability diagnostics.
  --no-color            Disable doctor status colors and symbols in text output.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev - Base development tooling for this repository.
  sre - production/SRE prerequisite tooling.
  ai  - AI coding assistant tooling.

Purpose:
  Diagnose the local Base CLI environment and, when provided, project artifacts.
  Use doctor for finding IDs and fix hints; use check for a quick pass/fail result.

See also:
  basectl check [project] [options]
EOF
}

base_doctor_print_finding() {
    local status="$1"
    local finding_id="$2"
    local name="$3"
    local message="$4"
    local fix="${5:-}"

    setup_print_doctor_finding "$status" "$finding_id" "$name" "$message" "$fix"
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

base_doctor_print_collected_check_results() {
    local count fix i status

    count="${#_BASE_SETUP_CHECK_NAMES[@]}"
    for ((i = 0; i < count; i++)); do
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

        base_doctor_print_finding \
            "$status" \
            "$(base_doctor_base_finding_id "${_BASE_SETUP_CHECK_NAMES[$i]}")" \
            "${_BASE_SETUP_CHECK_NAMES[$i]}" \
            "${_BASE_SETUP_CHECK_MESSAGES[$i]}" \
            "$fix"
    done
}

base_doctor_run_ci_runtime_text() {
    local errors=0 profile_errors=0 project="$1"

    setup_collect_base_check_results warn || true
    errors="$(base_doctor_count_check_errors)"

    if [[ -n "$project" ]]; then
        printf "Base CI doctor for project '%s'\n\n" "$project"
    else
        printf 'Base CI doctor\n\n'
    fi

    base_doctor_print_collected_check_results
    if setup_profiles_enabled; then
        setup_run_base_dev_layer doctor
        profile_errors=$?
        errors=$((errors + profile_errors))
    fi
    if [[ -n "$project" ]]; then
        setup_run_project_artifact_doctor
        errors=$((errors + $?))
    fi

    printf '\n'
    if ((errors == 0)); then
        if [[ -n "$project" ]]; then
            printf "Base CI doctor found no blocking issues for project '%s'.\n" "$project"
        else
            printf 'Base CI doctor found no blocking issues.\n'
        fi
        return 0
    fi

    if [[ -n "$project" ]]; then
        printf "Base CI doctor found %s blocking issue(s) for project '%s'.\n" "$errors" "$project"
    else
        printf 'Base CI doctor found %s blocking issue(s).\n' "$errors"
    fi
    return 1
}

base_doctor_check_homebrew() {
    local brew_bin

    if brew_bin="$(setup_find_brew_bin)"; then
        if setup_refresh_brew_path; then
            base_doctor_print_finding "ok" "BASE-D001" "Homebrew" "Homebrew is installed."
            log_debug "Resolved Homebrew binary: $brew_bin"
            return 0
        fi
        base_doctor_print_finding "error" "BASE-D001" "Homebrew" \
            "Homebrew is installed, but its bin directory could not be added to PATH." \
            "Check Homebrew installation and PATH."
        return 1
    fi

    base_doctor_print_finding "error" "BASE-D001" "Homebrew" "Homebrew is not installed." "basectl setup"
    return 1
}

base_doctor_check_xcode() {
    if setup_xcode_tools_installed; then
        if setup_homebrew_reports_xcode_tools_issue; then
            base_doctor_print_finding \
                "warn" \
                "BASE-D002" \
                "Xcode Command Line Tools" \
                "Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete." \
                "$(setup_recovery_xcode_tools_update)"
            return 0
        fi
        base_doctor_print_finding \
            "ok" \
            "BASE-D002" \
            "Xcode Command Line Tools" \
            "Xcode Command Line Tools are installed."
        return 0
    fi

    base_doctor_print_finding "error" "BASE-D002" "Xcode Command Line Tools" \
        "Xcode Command Line Tools are not installed." \
        "basectl setup"
    return 1
}

base_doctor_check_python() {
    local formula

    formula="$(setup_python_formula)"
    if setup_python_installed; then
        base_doctor_print_finding "ok" "BASE-D003" "Python" "Python formula '$formula' is installed via Homebrew."
        return 0
    fi

    base_doctor_print_finding "error" "BASE-D003" "Python" \
        "Python formula '$formula' is not installed via Homebrew." \
        "basectl setup"
    return 1
}

base_doctor_check_virtualenv() {
    setup_ensure_cached_paths
    if setup_virtualenv_healthy; then
        base_doctor_print_finding "ok" "BASE-D004" "Base virtualenv" "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
        return 0
    fi

    base_doctor_print_finding "error" "BASE-D004" "Base virtualenv" \
        "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
        "basectl setup --recreate-venv"
    return 1
}

base_doctor_check_python_package() {
    local package="$1"
    local finding_id="BASE-D005"

    if [[ "$package" == "$(setup_click_package)" ]]; then
        finding_id="BASE-D006"
    fi

    if setup_base_python_package_installed "$package"; then
        base_doctor_print_finding \
            "ok" \
            "$finding_id" \
            "$package" \
            "$(setup_base_python_package_check_message "$package" true)"
        return 0
    fi

    base_doctor_print_finding "error" "$finding_id" "$package" \
        "$(setup_base_python_package_check_message "$package" false)" \
        "basectl setup"
    return 1
}

base_doctor_run_json() {
    local errors=0 profile_errors=0 profile_json="[]"
    local project="$1"
    local project_errors=0 project_json="[]"
    local remote_network="${2:-${BASE_SETUP_REMOTE_NETWORK:-}}"
    local status="ok"

    BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_collect_base_check_results warn || true
    errors="$(base_doctor_count_check_errors)"
    status="$(setup_check_results_status)"

    if setup_profiles_enabled; then
        if profile_json="$(setup_run_base_dev_layer doctor --format json)"; then
            profile_errors=0
        else
            profile_errors=$?
            [[ -n "$profile_json" ]] || profile_json="[]"
            errors=$((errors + profile_errors))
        fi
        status="$(setup_merge_diagnostic_status "$status" "$(setup_json_payload_status "$profile_json")")"
    fi

    if [[ -n "$project" ]]; then
        if project_json="$(setup_run_project_artifact_doctor_json "$remote_network")"; then
            project_errors=0
        else
            project_errors=$?
            [[ -n "$project_json" ]] || project_json="[]"
            errors=$((errors + project_errors))
        fi
        status="$(setup_merge_diagnostic_status "$status" "$(setup_json_payload_status "$project_json")")"
    fi

    printf '{\n'
    printf '  "schema_version": 1,\n'
    printf '  "status": "%s"' "$(setup_json_escape "$status")"
    if [[ -n "$project" ]]; then
        printf ',\n'
        printf '  "project": "%s"' "$(setup_json_escape "$project")"
    fi
    printf ',\n'
    printf '  "findings": [\n'
    setup_print_check_json_results
    printf '  ]'
    if setup_profiles_enabled || [[ -n "$project" ]]; then
        printf ',\n'
    else
        printf '\n'
    fi
    if setup_profiles_enabled; then
        setup_print_json_property_value "$(setup_profile_json_key findings)" "$profile_json"
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
    local errors=0 output_format="text" profile_errors=0 project=""
    local remote_network=false

    setup_clear_run_state

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_doctor_subcommand_usage
                return 0
                ;;
            --profile)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--profile' requires an argument."
                    base_doctor_subcommand_usage >&2
                    return 2
                fi
                if ! setup_enable_profile_argument "$1"; then
                    print_error "$BASE_SETUP_PROFILE_ERROR"
                    base_doctor_subcommand_usage >&2
                    return 2
                fi
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
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--manifest' requires an argument."
                    base_doctor_subcommand_usage >&2
                    return 2
                fi
                BASE_SETUP_MANIFEST="$1"
                export BASE_SETUP_MANIFEST
                ;;
            --remote-network)
                remote_network=true
                ;;
            --no-color)
                BASE_SETUP_DOCTOR_NO_COLOR=true
                export BASE_SETUP_DOCTOR_NO_COLOR
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
    BASE_SETUP_REMOTE_NETWORK="$remote_network"
    export BASE_SETUP_PROJECT_NAME
    export BASE_SETUP_REMOTE_NETWORK
    log_debug "Running 'basectl doctor'."
    if setup_ci_runtime_only; then
        if [[ "$output_format" == json ]]; then
            base_doctor_run_json "$project" "$remote_network"
        else
            base_doctor_run_ci_runtime_text "$project"
        fi
        return $?
    fi

    setup_require_macos

    if [[ "$output_format" == json ]]; then
        base_doctor_run_json "$project" "$remote_network"
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
    if setup_profiles_enabled; then
        setup_run_base_dev_layer doctor
        profile_errors=$?
        errors=$((errors + profile_errors))
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
