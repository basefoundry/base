#!/usr/bin/env bash

[[ -n "${_base_setup_diagnostics_fallback_sourced:-}" ]] && return 0
_base_setup_diagnostics_fallback_sourced=1
readonly _base_setup_diagnostics_fallback_sourced

# Keep JSON diagnostics available when the Python renderer cannot start. This
# file is sourced by setup_common.sh after the check-result helpers; the
# functions it calls are resolved when the fallback is invoked.
import_base_lib arg/lib_arg.sh
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/inspection_json.sh"

setup_diagnostics_fallback_payload_status() {
    local payload="$1"

    if [[ "$payload" == *'"status":"error"'* || "$payload" == *'"status": "error"'* ]]; then
        printf '%s\n' error
    elif [[ "$payload" == *'"status":"warn"'* || "$payload" == *'"status": "warn"'* ]]; then
        printf '%s\n' warn
    else
        printf '%s\n' ok
    fi
}

setup_diagnostics_fallback_check_item() {
    local finding_id metadata name="$1" status="$2" message="$3" recovery="$4"

    metadata="$(setup_base_check_metadata "$name")"
    IFS=$'\t' read -r _ finding_id _ <<<"$metadata"
    [[ "$status" == ok ]] && recovery=""
    printf '{"id":'
    base_inspection_json_string "$finding_id"
    printf ',"status":'
    base_inspection_json_string "$status"
    printf ',"name":'
    base_inspection_json_string "$name"
    printf ',"message":'
    base_inspection_json_string "$message"
    printf ',"fix":'
    base_inspection_json_string "$recovery"
    printf '}'
}

setup_diagnostics_fallback_project_venv_item() {
    local status="$1" message="$2" recovery="$3"

    [[ "$status" == ok ]] && recovery=""
    printf '{"id":"BASE-P050","status":'
    base_inspection_json_string "$status"
    printf ',"name":"project_virtualenv","message":'
    base_inspection_json_string "$message"
    printf ',"fix":'
    base_inspection_json_string "$recovery"
    printf '}'
}

setup_diagnostics_fallback_append_item() {
    local output_name="$1" list="$2" item="$3"

    if [[ "$list" == "[]" ]]; then
        printf -v "$output_name" '%s' "[$item]"
    elif [[ "$list" == \[*\] ]]; then
        printf -v "$output_name" '%s' "${list%]},$item]"
    else
        printf -v "$output_name" '%s' "[$item]"
    fi
}

setup_diagnostics_fallback_record_warning() {
    local path="$1"

    printf '{"status":"warn","message":'
    base_inspection_json_string "Latest check record could not be saved."
    printf ',"fix":'
    base_inspection_json_string "Ensure the Base state directory is writable, then rerun the check."
    printf ',"path":'
    base_inspection_json_string "$path"
    printf '}'
}

# Without the Python identity writer, preserve the legacy optional record format.
# Workspace readers treat these unbound records as unavailable evidence.
setup_diagnostics_fallback_record_check() {
    local checked_at="" path="" project="" status="" tmp_path
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "project|value|--project"
        "status|value|--status"
        "checked_at|value|--checked-at"
        "project_root|value|--project-root"
        "manifest_path|value|--manifest-path"
        "path|value|--output-path"
    )
    local -a positionals=()
    local -A parsed_options=()

    if ! base_arg_parse parsed_options positionals option_specs -- "$@"; then
        base_std_fatal_error "Unsupported diagnostics fallback argument '${1:-}'."
    fi
    if ((${#positionals[@]} > 0)); then
        base_std_fatal_error "Unsupported diagnostics fallback argument '${positionals[0]}'."
    fi
    project="${parsed_options[project]:-}"
    status="${parsed_options[status]:-}"
    checked_at="${parsed_options[checked_at]:-}"
    path="${parsed_options[path]:-}"

    case "$status" in
        ok|warn|error) ;;
        *) base_std_fatal_error "Invalid diagnostics record status '$status'." ;;
    esac
    [[ -n "$project" && -n "$checked_at" && -n "$path" ]] ||
        base_std_fatal_error "Diagnostics record fallback requires project, status, checked-at, and output-path."

    mkdir -p -- "$(dirname -- "$path")" 2>/dev/null || return 1
    tmp_path="${path}.tmp.$$"
    if ! {
        printf '{\n  "schema_version": 1,\n  "project": '
        base_inspection_json_string "$project"
        printf ',\n  "command": "basectl check",\n  "status": '
        base_inspection_json_string "$status"
        printf ',\n  "checked_at": '
        base_inspection_json_string "$checked_at"
        printf '\n}\n'
    } >"$tmp_path" 2>/dev/null; then
        rm -f -- "$tmp_path"
        return 1
    fi
    if ! mv -- "$tmp_path" "$path" 2>/dev/null; then
        rm -f -- "$tmp_path"
        return 1
    fi
}

setup_diagnostics_fallback_json() {
    local command="${1:-}"
    shift || true

    case "$command" in
        record-check)
            setup_diagnostics_fallback_record_check "$@"
            return $?
            ;;
        project-venv-check-json|project-venv-doctor-json)
            local fix="" message="" precheck_json="[]" project="" status="" item_json output_json aggregate_status
            # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
            local -a option_specs=(
                "project|value|--project"
                "status|value|--status"
                "message|value|--message"
                "fix|value|--fix"
                "precheck_json|value|--precheck-json"
            )
            local -a positionals=()
            local -A parsed_options=()

            if ! base_arg_parse parsed_options positionals option_specs -- "$@"; then
                base_std_fatal_error "Unsupported diagnostics fallback argument '${1:-}'."
            fi
            if ((${#positionals[@]} > 0)); then
                base_std_fatal_error "Unsupported diagnostics fallback argument '${positionals[0]}'."
            fi
            project="${parsed_options[project]:-}"
            status="${parsed_options[status]:-}"
            message="${parsed_options[message]:-}"
            fix="${parsed_options[fix]:-}"
            precheck_json="${parsed_options[precheck_json]:-[]}"
            item_json="$(setup_diagnostics_fallback_project_venv_item "$status" "$message" "$fix")"
            setup_diagnostics_fallback_append_item output_json "$precheck_json" "$item_json"
            aggregate_status="$(setup_diagnostics_fallback_payload_status "$precheck_json")"
            aggregate_status="$(setup_merge_diagnostic_status "$aggregate_status" "$status")"
            if [[ "$command" == project-venv-check-json ]]; then
                printf '{"schema_version": 1, "status": '
                base_inspection_json_string "$aggregate_status"
                printf ', "project": '
                base_inspection_json_string "$project"
                printf ', "checks": %s}\n' "$output_json"
            else
                printf '%s\n' "$output_json"
            fi
            [[ "$aggregate_status" != error ]]
            return $?
            ;;
        check-json|doctor-json)
            local checked_at="" embedded_key embedded_payload project="" record_path=""
            local result_file status="ok" item_json output_json
            local check_names=() check_statuses=() check_messages=() check_fixes=()
            local result_files=() embedded_keys=() embedded_values=() item_key="checks"
            local -a parser_args=() positionals=()
            # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
            local -a option_specs=(
                "project|value|--project"
                "check_names|repeatable|--check-name"
                "check_statuses|repeatable|--check-status"
                "check_messages|repeatable|--check-message"
                "check_fixes|repeatable|--check-fix"
                "result_files|repeatable|--check-result-file"
                "embedded_keys|repeatable|--embedded-key"
                "embedded_values|repeatable|--embedded-value"
                "record_path|value|--record-path"
                "checked_at|value|--checked-at"
                "project_root|value|--project-root"
                "manifest_path|value|--manifest-path"
            )
            local -A parsed_options=()
            local i

            [[ "$command" == doctor-json ]] && item_key="findings"
            while (($#)); do
                case "$1" in
                    --project|--record-path|--checked-at|--project-root|--manifest-path)
                        [[ $# -ge 2 ]] || base_std_fatal_error "Option '$1' requires an argument."
                        parser_args+=("$1" "$2")
                        shift 2
                        ;;
                    --check|--finding)
                        [[ $# -ge 5 ]] || base_std_fatal_error "Option '$1' requires four arguments."
                        parser_args+=(
                            --check-name "$2"
                            --check-status "$3"
                            --check-message "$4"
                            --check-fix "$5"
                        )
                        shift 5
                        ;;
                    --check-result-file|--finding-result-file)
                        [[ $# -ge 2 ]] || base_std_fatal_error "Option '$1' requires an argument."
                        parser_args+=(--check-result-file "$2")
                        shift 2
                        ;;
                    --embedded-payload)
                        [[ $# -ge 3 ]] || base_std_fatal_error "Option '$1' requires two arguments."
                        parser_args+=(--embedded-key "$2" --embedded-value "$3")
                        shift 3
                        ;;
                    *)
                        base_std_fatal_error "Unsupported diagnostics fallback argument '$1'."
                        ;;
                esac
            done

            if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
                base_std_fatal_error "Unsupported diagnostics fallback argument '${1:-}'."
            fi
            if ((${#positionals[@]} > 0)); then
                base_std_fatal_error "Unsupported diagnostics fallback argument '${positionals[0]}'."
            fi
            project="${parsed_options[project]:-}"
            record_path="${parsed_options[record_path]:-}"
            checked_at="${parsed_options[checked_at]:-}"

            output_json='[]'
            for ((i = 0; i < ${#check_names[@]}; i++)); do
                item_json="$(setup_diagnostics_fallback_check_item "${check_names[$i]}" "${check_statuses[$i]}" "${check_messages[$i]}" "${check_fixes[$i]}")"
                setup_diagnostics_fallback_append_item output_json "$output_json" "$item_json"
                status="$(setup_merge_diagnostic_status "$status" "${check_statuses[$i]}")"
            done
            for result_file in "${result_files[@]}"; do
                setup_parse_check_result_file "$result_file"
                item_json="$(setup_diagnostics_fallback_check_item \
                    "$_BASE_SETUP_PARSED_CHECK_NAME" \
                    "$_BASE_SETUP_PARSED_CHECK_STATUS" \
                    "$_BASE_SETUP_PARSED_CHECK_MESSAGE" \
                    "$_BASE_SETUP_PARSED_CHECK_RECOVERY")"
                setup_diagnostics_fallback_append_item output_json "$output_json" "$item_json"
                status="$(setup_merge_diagnostic_status "$status" "$_BASE_SETUP_PARSED_CHECK_STATUS")"
            done
            for ((i = 0; i < ${#embedded_keys[@]}; i++)); do
                embedded_key="${embedded_keys[$i]}"
                embedded_payload="${embedded_values[$i]}"
                status="$(setup_merge_diagnostic_status "$status" "$(setup_diagnostics_fallback_payload_status "$embedded_payload")")"
            done

            printf '{"schema_version": 1, "status": '
            base_inspection_json_string "$status"
            if [[ -n "$project" ]]; then
                printf ', "project": '
                base_inspection_json_string "$project"
            fi
            printf ', "%s": %s' "$item_key" "$output_json"
            for ((i = 0; i < ${#embedded_keys[@]}; i++)); do
                embedded_key="${embedded_keys[$i]}"
                embedded_payload="${embedded_values[$i]}"
                printf ', '
                base_inspection_json_string "$embedded_key"
                printf ': %s' "$embedded_payload"
            done
            if [[ -n "$record_path" && -n "$project" && -n "$checked_at" && "$command" == check-json ]]; then
                if ! setup_diagnostics_fallback_record_check \
                    --project "$project" \
                    --status "$status" \
                    --checked-at "$checked_at" \
                    --output-path "$record_path" 2>/dev/null; then
                    printf ', "record": '
                    setup_diagnostics_fallback_record_warning "$record_path"
                fi
            fi
            printf '}\n'
            [[ "$status" != error ]]
            return $?
            ;;
        *)
            base_std_fatal_error "Python is required to render diagnostics command '$command'."
            ;;
    esac
}
