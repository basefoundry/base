# Deterministic implementation of the Python diagnostics module for fake
# interpreters used by the setup/check/doctor BATS suites.

base_test_diagnostics_json_string() {
    local LC_ALL=C char code index=0 length next

    printf '"'
    length="${#1}"
    while ((index < length)); do
        char="${1:index:1}"
        case "$char" in
            '"') printf '\\"' ;;
            \\) printf '\\\\' ;;
            $'\b') printf '\\b' ;;
            $'\f') printf '\\f' ;;
            $'\n') printf '\\n' ;;
            $'\r') printf '\\r' ;;
            $'\t') printf '\\t' ;;
            *)
                printf -v code '%d' "'$char"
                if ((code < 32)); then
                    printf '\\u%04x' "$code"
                else
                    printf '%s' "$char"
                fi
                ;;
        esac
        index=$((index + 1))
    done
    printf '"'
}

base_test_diagnostics_finding_id() {
    case "$1" in
        homebrew) printf 'BASE-D001' ;;
        xcode_command_line_tools) printf 'BASE-D002' ;;
        python) printf 'BASE-D003' ;;
        base_virtualenv) printf 'BASE-D004' ;;
        pyyaml) printf 'BASE-D005' ;;
        click) printf 'BASE-D006' ;;
        base_bash_libraries) printf 'BASE-D007' ;;
        bash) printf 'BASE-D008' ;;
        python_venv) printf 'BASE-D009' ;;
        git) printf 'BASE-D010' ;;
        gh) printf 'BASE-D011' ;;
        bats) printf 'BASE-D012' ;;
        shellcheck) printf 'BASE-D013' ;;
        jq) printf 'BASE-D014' ;;
        go) printf 'BASE-D015' ;;
        *) printf 'BASE-D000' ;;
    esac
}

base_test_diagnostics_metadata() {
    local name

    for name in "$@"; do
        printf '%s\t%s\t%s\n' \
            "$name" \
            "$(base_test_diagnostics_finding_id "$name")" \
            "$name"
    done
}

base_test_diagnostics_result_field() {
    local field="$1" path="$2" line

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" == "$field="* ]] && {
            printf '%s\n' "${line#*=}"
            return 0
        }
    done <"$path"
    return 1
}

base_test_diagnostics_result_json() {
    local name status message recovery path="$1"

    name="$(base_test_diagnostics_result_field name "$path")"
    status="$(base_test_diagnostics_result_field status "$path")"
    message="$(base_test_diagnostics_result_field message "$path")"
    recovery="$(base_test_diagnostics_result_field recovery "$path" || true)"
    [[ "$status" == ok ]] && recovery=""
    printf '{"id":'
    base_test_diagnostics_json_string "$(base_test_diagnostics_finding_id "$name")"
    printf ',"status":'
    base_test_diagnostics_json_string "$status"
    printf ',"name":'
    base_test_diagnostics_json_string "$name"
    printf ',"message":'
    base_test_diagnostics_json_string "$message"
    printf ',"fix":'
    base_test_diagnostics_json_string "$recovery"
    printf '}'
}

base_test_diagnostics_append_item() {
    local output_name="$1" list="$2" item="$3"

    if [[ "$list" == "[]" ]]; then
        printf -v "$output_name" '%s' "[$item]"
    else
        printf -v "$output_name" '%s' "${list%]},$item]"
    fi
}

base_test_diagnostics_payload_status() {
    case "$1" in
        *'"status":"error"'*|*'"status": "error"'*) printf error ;;
        *'"status":"warn"'*|*'"status": "warn"'*) printf warn ;;
        *) printf ok ;;
    esac
}

base_test_diagnostics_merge_status() {
    if [[ "$1" == error || "$2" == error ]]; then
        printf error
    elif [[ "$1" == warn || "$2" == warn ]]; then
        printf warn
    else
        printf ok
    fi
}

base_test_diagnostics_record_check() {
    local checked_at="" path="" project="" status="" tmp_path

    while (($#)); do
        case "$1" in
            --project) project="${2:-}"; shift 2 ;;
            --status) status="${2:-}"; shift 2 ;;
            --checked-at) checked_at="${2:-}"; shift 2 ;;
            --output-path) path="${2:-}"; shift 2 ;;
            *) return 2 ;;
        esac
    done
    mkdir -p -- "$(dirname -- "$path")" 2>/dev/null || return 1
    tmp_path="${path}.tmp.$$"
    if ! {
        printf '{"schema_version":1,"project":'
        base_test_diagnostics_json_string "$project"
        printf ',"command":"basectl check","status":'
        base_test_diagnostics_json_string "$status"
        printf ',"checked_at":'
        base_test_diagnostics_json_string "$checked_at"
        printf '}\n'
    } >"$tmp_path" 2>/dev/null; then
        rm -f -- "$tmp_path"
        return 1
    fi
    if ! mv -- "$tmp_path" "$path" 2>/dev/null; then
        rm -f -- "$tmp_path"
        return 1
    fi
}

base_test_diagnostics_record_warning() {
    local path="$1"

    printf '{"status":"warn","message":'
    base_test_diagnostics_json_string "Latest check record could not be saved."
    printf ',"fix":'
    base_test_diagnostics_json_string "Ensure the Base state directory is writable, then rerun the check."
    printf ',"path":'
    base_test_diagnostics_json_string "$path"
    printf '}'
}

base_test_diagnostics_module() {
    local command="${1:-}"
    shift || true
    local project="" record_path="" checked_at="" status="ok" item_key="checks"
    local result_file item_json output_json embedded_key embedded_payload aggregate_status
    local check_name check_status check_message check_fix
    local check_names=() check_statuses=() check_messages=() check_fixes=()
    local result_files=() embedded_keys=() embedded_values=() i

    case "$command" in
        -h|--help)
            printf 'Base diagnostics fixture\n'
            return 0
            ;;
        base-check-metadata)
            local metadata_names=()
            while (($#)); do
                [[ "$1" == --name ]] || return 2
                metadata_names+=("${2:-}")
                shift 2
            done
            base_test_diagnostics_metadata "${metadata_names[@]}"
            return 0
            ;;
        record-check)
            base_test_diagnostics_record_check "$@"
            return $?
            ;;
        project-venv-check-json|project-venv-doctor-json)
            local fix="" message="" precheck_json="[]"
            while (($#)); do
                case "$1" in
                    --project) project="${2:-}"; shift 2 ;;
                    --status) status="${2:-}"; shift 2 ;;
                    --message) message="${2:-}"; shift 2 ;;
                    --fix) fix="${2:-}"; shift 2 ;;
                    --precheck-json) precheck_json="${2:-[]}"; shift 2 ;;
                    *) return 2 ;;
                esac
            done
            item_json='{"id":"BASE-P050","status":'
            item_json+="$(base_test_diagnostics_json_string "$status")"
            item_json+=',"name":"project_virtualenv","message":'
            item_json+="$(base_test_diagnostics_json_string "$message")"
            item_json+=',"fix":'
            item_json+="$(base_test_diagnostics_json_string "$fix")"
            item_json+='}'
            base_test_diagnostics_append_item output_json "$precheck_json" "$item_json"
            if [[ "$command" == project-venv-check-json ]]; then
                aggregate_status="$(base_test_diagnostics_merge_status "$(base_test_diagnostics_payload_status "$precheck_json")" "$status")"
                printf '{"schema_version": 1, "status": '
                base_test_diagnostics_json_string "$aggregate_status"
                printf ', "project": '
                base_test_diagnostics_json_string "$project"
                printf ', "checks": %s}\n' "$output_json"
            else
                printf '%s\n' "$output_json"
            fi
            [[ "$status" != error ]]
            return $?
            ;;
        check-json|doctor-json)
            [[ "$command" == doctor-json ]] && item_key="findings"
            while (($#)); do
                case "$1" in
                    --project) project="${2:-}"; shift 2 ;;
                    --check|--finding)
                        check_names+=("${2:-}")
                        check_statuses+=("${3:-}")
                        check_messages+=("${4:-}")
                        check_fixes+=("${5:-}")
                        shift 5
                        ;;
                    --check-result-file|--finding-result-file)
                        result_files+=("${2:-}")
                        shift 2
                        ;;
                    --embedded-payload)
                        embedded_keys+=("${2:-}")
                        embedded_values+=("${3:-}")
                        shift 3
                        ;;
                    --record-path) record_path="${2:-}"; shift 2 ;;
                    --checked-at) checked_at="${2:-}"; shift 2 ;;
                    *) return 2 ;;
                esac
            done
            output_json='[]'
            for ((i = 0; i < ${#check_names[@]}; i++)); do
                printf -v item_json '{"id":%s,"status":%s,"name":%s,"message":%s,"fix":%s}' \
                    "$(base_test_diagnostics_json_string "$(base_test_diagnostics_finding_id "${check_names[$i]}")")" \
                    "$(base_test_diagnostics_json_string "${check_statuses[$i]}")" \
                    "$(base_test_diagnostics_json_string "${check_names[$i]}")" \
                    "$(base_test_diagnostics_json_string "${check_messages[$i]}")" \
                    "$(base_test_diagnostics_json_string "${check_fixes[$i]}")"
                base_test_diagnostics_append_item output_json "$output_json" "$item_json"
                status="$(base_test_diagnostics_merge_status "$status" "${check_statuses[$i]}")"
            done
            for result_file in "${result_files[@]}"; do
                item_json="$(base_test_diagnostics_result_json "$result_file")"
                base_test_diagnostics_append_item output_json "$output_json" "$item_json"
                status="$(base_test_diagnostics_merge_status "$status" "$(base_test_diagnostics_result_field status "$result_file")")"
            done
            for ((i = 0; i < ${#embedded_values[@]}; i++)); do
                status="$(base_test_diagnostics_merge_status "$status" "$(base_test_diagnostics_payload_status "${embedded_values[$i]}")")"
            done
            printf '{"schema_version": 1, "status": '
            base_test_diagnostics_json_string "$status"
            [[ -n "$project" ]] && {
                printf ', "project": '
                base_test_diagnostics_json_string "$project"
            }
            printf ', "%s": %s' "$item_key" "$output_json"
            for ((i = 0; i < ${#embedded_keys[@]}; i++)); do
                printf ', '
                base_test_diagnostics_json_string "${embedded_keys[$i]}"
                printf ': %s' "${embedded_values[$i]}"
            done
            if [[ -n "$record_path" && -n "$project" && -n "$checked_at" && "$command" == check-json ]]; then
                if ! base_test_diagnostics_record_check \
                    --project "$project" --status "$status" --checked-at "$checked_at" --output-path "$record_path"; then
                    printf ', "record": '
                    base_test_diagnostics_record_warning "$record_path"
                fi
            fi
            printf '}\n'
            [[ "$status" != error ]]
            return $?
            ;;
        *)
            return 2
            ;;
    esac
}
