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
  --manifest <path>     Use this base_manifest.yaml; infer an omitted project.
  --remote-network      Check project Git origin; requires project or --manifest.
  --verify-project-runtime
                        Authorize project runtime/configuration execution for this check.
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
EOF
}

base_doctor_usage_error() {
    base_std_print_error "$*"
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
    base_std_print_error "$*"
    printf "Run 'basectl doctor explain --help' for usage.\n" >&2
    return 2
}

base_doctor_explain_finding() {
    local finding_id="$1"
    local output_format="$2"
    local python_bin

    python_bin="$(setup_diagnostics_python_bin)" ||
        base_std_fatal_error "Python is required to render Base finding explanations."
    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -I "$BASE_HOME/cli/python/base_cli_adapters/module_entrypoint.py" base_setup.finding_explanations "$finding_id" --format "$output_format"
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
            base_std_fatal_error "Base diagnostic metadata renderer failed."
        while IFS= read -r metadata_line; do
            metadata_lines+=("$metadata_line")
        done <<<"$metadata_output"
        if ((${#metadata_lines[@]} != count)); then
            base_std_fatal_error "Base diagnostic metadata renderer returned ${#metadata_lines[@]} rows for $count checks."
        fi
    fi

    for ((i = 0; i < count; i++)); do
        status="$(setup_check_result_status "$i")"
        fix="$(setup_check_result_recovery "$i")"
        IFS=$'\t' read -r metadata_name finding_id display_name <<<"${metadata_lines[$i]}"
        if [[ "$metadata_name" != "${_BASE_SETUP_CHECK_NAMES[$i]}" || -z "$finding_id" || -z "$display_name" ]]; then
            base_std_fatal_error "Base diagnostic metadata renderer returned invalid metadata for '${_BASE_SETUP_CHECK_NAMES[$i]}'."
        fi
        if [[ "$status" == ok && -n "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}" ]]; then
            base_std_log_debug "${_BASE_SETUP_CHECK_DEBUG_MESSAGES[$i]}"
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

    base_doctor_print_collected_check_results
    if setup_profiles_enabled; then
        setup_run_base_dev_layer doctor
        profile_errors=$?
        errors=$((errors + profile_errors))
    fi
    if [[ -n "$project" || -n "${BASE_SETUP_MANIFEST:-}" ]]; then
        setup_run_project_artifact_doctor
        errors=$((errors + $?))
        project="${BASE_SETUP_PROJECT_NAME:-}"
    fi

    if ((errors == 0)); then
        if [[ -n "$project" ]]; then
            base_std_log_info "Base CI doctor found no blocking issues for project '$project'."
        else
            base_std_log_info 'Base CI doctor found no blocking issues.'
        fi
        return 0
    fi

    if [[ -n "$project" ]]; then
        base_std_log_error "Base CI doctor found $errors blocking issue(s) for project '$project'."
    else
        base_std_log_error "Base CI doctor found $errors blocking issue(s)."
    fi
    return 1
}

base_doctor_run_json() {
    local args=()
    local check_result_dir check_result_file check_result_paths
    local profile_json="[]"
    local project="$1"
    local project_json="[]"
    local project_json_file project_status=0 requested_project="$1"
    local remote_network="${2:-${BASE_SETUP_REMOTE_NETWORK:-}}"

    BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_collect_base_check_results warn || true
    base_std_make_temp_dir check_result_dir base-doctor-json ||
        base_std_fatal_error "Unable to create temporary Base doctor JSON result directory."

    if setup_profiles_enabled; then
        if ! profile_json="$(setup_run_base_dev_layer doctor --format json)"; then
            [[ -n "$profile_json" ]] || profile_json="[]"
        fi
    fi

    if [[ -n "$project" || -n "${BASE_SETUP_MANIFEST:-}" ]]; then
        project_json_file="$check_result_dir/project.json"
        setup_run_project_artifact_doctor_json "$remote_network" > "$project_json_file"
        project_status=$?
        project_json="$(<"$project_json_file")"
        if ((project_status)) && [[ -z "$project_json" ]]; then
            if [[ -z "$requested_project" && -n "${BASE_SETUP_MANIFEST:-}" ]]; then
                return 1
            fi
            project_json="[]"
        fi
        project="${BASE_SETUP_PROJECT_NAME:-$project}"
    fi

    args+=(doctor-json)
    if [[ -n "$project" ]]; then
        args+=(--project "$project")
    fi
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
    local remote_network=false verify_project_runtime=false

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
            --verify-project-runtime)
                verify_project_runtime=true
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

    if [[ "$remote_network" == true && -z "$project" && -z "${BASE_SETUP_MANIFEST:-}" ]]; then
        base_doctor_usage_error "Option '--remote-network' requires a project or '--manifest <path>'."
        return $?
    fi
    if [[ "$verify_project_runtime" == true && -z "$project" && -z "${BASE_SETUP_MANIFEST:-}" ]]; then
        base_doctor_usage_error "Option '--verify-project-runtime' requires a project or '--manifest <path>'."
        return $?
    fi
    BASE_SETUP_VERIFY_PROJECT_RUNTIME="$verify_project_runtime"
    export BASE_SETUP_VERIFY_PROJECT_RUNTIME
    BASE_SETUP_PROJECT_NAME="$project"
    BASE_SETUP_REMOTE_NETWORK="$remote_network"
    export BASE_SETUP_PROJECT_NAME
    export BASE_SETUP_REMOTE_NETWORK
    base_std_log_debug "Running 'basectl doctor'."
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

    BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_collect_base_check_results warn || true
    errors="$(base_doctor_count_check_errors)"
    base_doctor_print_collected_check_results
    if setup_profiles_enabled; then
        setup_run_base_dev_layer doctor
        profile_errors=$?
        errors=$((errors + profile_errors))
    fi
    if [[ -n "$project" || -n "${BASE_SETUP_MANIFEST:-}" ]]; then
        setup_run_project_artifact_doctor
        errors=$((errors + $?))
        project="${BASE_SETUP_PROJECT_NAME:-}"
    fi

    if ((errors == 0)); then
        if [[ -n "$project" ]]; then
            base_std_log_info "Base doctor found no blocking issues for project '$project'."
        else
            base_std_log_info 'Base doctor found no blocking issues.'
        fi
        return 0
    fi

    if [[ -n "$project" ]]; then
        base_std_log_error "Base doctor found $errors blocking issue(s) for project '$project'."
    else
        base_std_log_error "Base doctor found $errors blocking issue(s)."
    fi
    return 1
}
