#!/usr/bin/env bash

[[ -n "${_base_doctor_subcommand_sourced:-}" ]] && return 0
_base_doctor_subcommand_sourced=1
readonly _base_doctor_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_doctor_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl doctor [project] [options]
  basectl doctor explain <finding-id> [--format text|json]

Options:
  --ci                  Run diagnostics with CI-safe defaults.
  --profile <list>      Include named prerequisite profiles. Known profiles: dev, sre, ai, linux-lab.
  --format <text|json>  Select output format. Defaults to text.
  --manifest <path>     Use a specific base_manifest.yaml path for project diagnostics.
  --remote-network      Opt in to bounded project Git origin reachability diagnostics.
  --no-color            Disable doctor status colors and symbols in text output.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev       - Base development tooling for this repository.
  sre       - production/SRE prerequisite tooling.
  ai        - AI coding assistant tooling.
  linux-lab - Multipass tooling for local Ubuntu lab VMs on macOS hosts.

Purpose:
  Diagnose the local Base CLI environment and, when provided, project artifacts.
  Use doctor for finding IDs and fix hints; use check for a quick pass/fail result.
  Use doctor explain for local, provider-neutral guidance about a stable finding ID.

See also:
  basectl check [project] [options]
  basectl ci doctor [project] [options]  Compatibility alias for doctor --ci.
EOF
}

base_doctor_usage_error() {
    print_error "$*"
    printf "Run 'basectl doctor --help' for usage.\n" >&2
    return 2
}

base_doctor_explain_usage() {
    cat <<'EOF'
Usage:
  basectl doctor explain <finding-id> [--format text|json]

Options:
  --format <text|json>  Select output format. Defaults to text.
  -h, --help            Show this help text.

Purpose:
  Print local, deterministic guidance for a stable Base finding ID.
EOF
}

base_doctor_explain_usage_error() {
    print_error "$*"
    printf "Run 'basectl doctor explain --help' for usage.\n" >&2
    return 2
}

base_doctor_explain_finding() {
    local finding_id="$1"
    local output_format="$2"
    local python_bin

    python_bin="$(setup_diagnostics_python_bin)" ||
        fatal_error "Python is required to render Base finding explanations."
    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -m base_setup.finding_explanations "$finding_id" --format "$output_format"
}

base_doctor_explain_main() {
    local finding_id=""
    local output_format="text"

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_doctor_explain_usage
                return 0
                ;;
            --format)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_doctor_explain_usage_error "Option '--format' requires an argument."
                    return $?
                fi
                case "$1" in
                    text|json)
                        output_format="$1"
                        ;;
                    *)
                        base_doctor_explain_usage_error "Unsupported doctor explain output format '$1'."
                        return $?
                        ;;
                esac
                ;;
            --format=*)
                case "${1#--format=}" in
                    text|json)
                        output_format="${1#--format=}"
                        ;;
                    *)
                        base_doctor_explain_usage_error "Unsupported doctor explain output format '${1#--format=}'."
                        return $?
                        ;;
                esac
                ;;
            *)
                if [[ "$1" == -* ]]; then
                    base_doctor_explain_usage_error "Unknown option '$1'."
                    return $?
                fi
                if [[ -n "$finding_id" ]]; then
                    base_doctor_explain_usage_error "The 'doctor explain' command accepts exactly one finding ID."
                    return $?
                fi
                finding_id="$1"
                ;;
        esac
        shift
    done

    if [[ -z "$finding_id" ]]; then
        base_doctor_explain_usage_error "The 'doctor explain' command requires a finding ID."
        return $?
    fi

    base_doctor_explain_finding "$finding_id" "$output_format"
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
    local count display_name finding_id fix i metadata_line metadata_name metadata_output status
    local metadata_lines=()

    count="${#_BASE_SETUP_CHECK_NAMES[@]}"
    if ((count > 0)); then
        metadata_output="$(setup_base_check_metadata "${_BASE_SETUP_CHECK_NAMES[@]}")" ||
            fatal_error "Base diagnostic metadata renderer failed."
        while IFS= read -r metadata_line; do
            metadata_lines+=("$metadata_line")
        done <<<"$metadata_output"
        if ((${#metadata_lines[@]} != count)); then
            fatal_error "Base diagnostic metadata renderer returned ${#metadata_lines[@]} rows for $count checks."
        fi
    fi

    for ((i = 0; i < count; i++)); do
        status="$(setup_check_result_status "$i")"
        fix="$(setup_check_result_recovery "$i")"
        IFS=$'\t' read -r metadata_name finding_id display_name <<<"${metadata_lines[$i]}"
        if [[ "$metadata_name" != "${_BASE_SETUP_CHECK_NAMES[$i]}" || -z "$finding_id" || -z "$display_name" ]]; then
            fatal_error "Base diagnostic metadata renderer returned invalid metadata for '${_BASE_SETUP_CHECK_NAMES[$i]}'."
        fi
        if [[ "$status" == ok && -n "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}" ]]; then
            log_debug "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}"
        fi
        if [[ "$status" == ok ]]; then
            fix=""
        fi

        base_doctor_print_finding \
            "$status" \
            "$finding_id" \
            "$display_name" \
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

    setup_print_runtime_chain_summary
    printf '\n'

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

base_doctor_run_json() {
    local args=()
    local check_result_dir check_result_file check_result_paths
    local profile_json="[]"
    local project="$1"
    local project_json="[]"
    local remote_network="${2:-${BASE_SETUP_REMOTE_NETWORK:-}}"

    BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_collect_base_check_results warn || true

    if setup_profiles_enabled; then
        if ! profile_json="$(setup_run_base_dev_layer doctor --format json)"; then
            [[ -n "$profile_json" ]] || profile_json="[]"
        fi
    fi

    if [[ -n "$project" ]]; then
        if ! project_json="$(setup_run_project_artifact_doctor_json "$remote_network")"; then
            [[ -n "$project_json" ]] || project_json="[]"
        fi
    fi

    args+=(doctor-json)
    if [[ -n "$project" ]]; then
        args+=(--project "$project")
    fi
    std_make_temp_dir check_result_dir base-doctor-json ||
        fatal_error "Unable to create temporary Base doctor JSON result directory."
    check_result_paths="$(setup_write_collected_check_result_files "$check_result_dir")" || return 1
    if [[ -n "$check_result_paths" ]]; then
        while IFS= read -r check_result_file; do
            args+=(--finding-result-file "$check_result_file")
        done <<<"$check_result_paths"
    fi
    if setup_profiles_enabled; then
        args+=(--embedded-payload "$(setup_profile_json_key findings)" "$profile_json")
    fi
    if [[ -n "$project" ]]; then
        args+=(--embedded-payload "project_findings" "$project_json")
    fi
    setup_run_diagnostics_json "${args[@]}"
}

base_doctor_subcommand_main() {
    local errors=0 output_format="text" profile_errors=0 project=""
    local remote_network=false

    setup_clear_run_state

    if [[ "${1:-}" == explain ]]; then
        shift
        base_doctor_explain_main "$@"
        return $?
    fi

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_doctor_subcommand_usage
                return 0
                ;;
            --ci)
                setup_enable_ci_mode
                ;;
            --profile)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_doctor_usage_error "Option '--profile' requires an argument."
                    return $?
                fi
                if ! setup_enable_profile_argument "$1"; then
                    base_doctor_usage_error "$BASE_SETUP_PROFILE_ERROR"
                    return $?
                fi
                ;;
            --format)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_doctor_usage_error "Option '--format' requires an argument."
                    return $?
                fi
                case "$1" in
                    text|json)
                        output_format="$1"
                        ;;
                    *)
                        base_doctor_usage_error "Unsupported doctor output format '$1'."
                        return $?
                        ;;
                esac
                ;;
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_doctor_usage_error "Option '--manifest' requires an argument."
                    return $?
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
                    base_doctor_usage_error "Unknown option '$1'."
                    return $?
                fi
                if [[ -n "$project" ]]; then
                    base_doctor_usage_error "The 'doctor' command accepts at most one project name."
                    return $?
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

    if [[ "$output_format" == json ]]; then
        base_doctor_run_json "$project" "$remote_network"
        return $?
    fi

    setup_print_runtime_chain_summary
    printf '\n'

    BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_collect_base_check_results warn || true
    errors="$(base_doctor_count_check_errors)"
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
