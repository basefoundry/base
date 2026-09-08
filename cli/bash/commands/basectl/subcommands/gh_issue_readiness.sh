#!/usr/bin/env bash

[[ -n "${_base_gh_issue_readiness_sourced:-}" ]] && return 0
_base_gh_issue_readiness_sourced=1
readonly _base_gh_issue_readiness_sourced

import_base_lib arg/lib_arg.sh

base_gh_issue_readiness_required_sections() {
    printf '%s\n' \
        "Goal" \
        "Background" \
        "Scope" \
        "Acceptance Criteria" \
        "Validation" \
        "Non-Goals" \
        "Project Fields" \
        "Agent Assignment"
}

base_gh_issue_readiness_required_project_fields() {
    printf '%s\n' Status Priority Size Area Initiative
}

base_gh_issue_readiness_has_section() {
    local section="$1"

    awk -v section="$section" '
        /^##[[:space:]]+/ {
            heading = $0
            sub(/^##[[:space:]]+/, "", heading)
            sub(/[[:space:]]+$/, "", heading)
            in_section = (heading == section)
            next
        }
        in_section && $0 !~ /^[[:space:]]*$/ {
            found = 1
        }
        END {
            exit(found ? 0 : 1)
        }
    '
}

base_gh_lines_to_csv() {
    local line
    local values=()

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] && values+=("$line")
    done

    if ((${#values[@]})); then
        base_gh_join_csv "${values[@]}"
    else
        printf 'none\n'
    fi
}

base_gh_jq_string_literal() {
    local value="$1"

    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    printf '"%s"\n' "$value"
}

base_gh_issue_readiness_project_row() {
    local issue="$1" repo="$2" project_owner="$3" project_number="$4"
    local repo_literal query

    repo_literal="$(base_gh_jq_string_literal "$repo")"
    query=".items[] | select((.content.number == $issue) and (.content.repository == $repo_literal)) | [.status // \"\", .priority // \"\", .size // \"\", .area // \"\", .initiative // \"\"] | join(\"\u001f\")"
    base_cli_gh_run project item-list "$project_number" --owner "$project_owner" --format json --limit 1000 --jq "$query"
}

base_gh_issue_readiness_format_error() {
    local output_format="$1"
    local message="$2"

    if [[ "$output_format" == "json" ]]; then
        base_inspection_json_emit_error "gh issue readiness" usage_error "$message" '{}'
        return 2
    fi
    base_gh_usage_error base_gh_issue_usage "$message"
}

base_gh_issue_readiness_upstream_error() {
    local output_format="$1"
    local operation="$2"
    local status="$3"
    local details_json

    if [[ "$output_format" == "json" ]]; then
        printf -v details_json '{"operation":"%s"}' "$operation"
        base_inspection_json_emit_error \
            "gh issue readiness" upstream_error \
            "GitHub inspection failed during $operation." "$details_json"
    fi
    return "$status"
}

base_gh_issue_readiness_reset() {
    _BASE_GH_ISSUE_READINESS_ISSUE=""
    _BASE_GH_ISSUE_READINESS_REPOSITORY=""
    _BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT="text"
    _BASE_GH_ISSUE_READINESS_PROJECT_OWNER=""
    _BASE_GH_ISSUE_READINESS_PROJECT_NUMBER=""
    _BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED=0
    _BASE_GH_ISSUE_READINESS_EXIT_REQUESTED=0
    _BASE_GH_ISSUE_READINESS_BODY=""
    _BASE_GH_ISSUE_READINESS_LABELS_OUTPUT=""
    _BASE_GH_ISSUE_READINESS_ASSIGNEES_OUTPUT=""
    _BASE_GH_ISSUE_READINESS_LABELS_SUMMARY=""
    _BASE_GH_ISSUE_READINESS_ASSIGNEES_SUMMARY=""
    _BASE_GH_ISSUE_READINESS_PROJECT_ROW=""
    _BASE_GH_ISSUE_READINESS_PROJECT_STATUS=""
    _BASE_GH_ISSUE_READINESS_PROJECT_PRIORITY=""
    _BASE_GH_ISSUE_READINESS_PROJECT_SIZE=""
    _BASE_GH_ISSUE_READINESS_PROJECT_AREA=""
    _BASE_GH_ISSUE_READINESS_PROJECT_INITIATIVE=""
    _BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE="ready"
    _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS=()
    _BASE_GH_ISSUE_READINESS_MISSING_SECTIONS=()
    _BASE_GH_ISSUE_READINESS_LABELS=()
    _BASE_GH_ISSUE_READINESS_ASSIGNEES=()
}

base_gh_issue_readiness_parse_args() {
    local requested_format=""
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "repo|value|--repo"
        "project_owner|value|--project-owner"
        "project_number|value|--project-number"
        "format|value|--format"
    )
    local -a parser_args=() positionals=()
    local -A parsed_options=()

    base_inspection_find_output_format _BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT "$@"

    _BASE_GH_ISSUE_READINESS_ISSUE="${1:-}"
    [[ -n "$_BASE_GH_ISSUE_READINESS_ISSUE" ]] || {
        base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Missing issue number."
        return $?
    }
    if [[ "$_BASE_GH_ISSUE_READINESS_ISSUE" == "help" || "$_BASE_GH_ISSUE_READINESS_ISSUE" == "-h" || "$_BASE_GH_ISSUE_READINESS_ISSUE" == "--help" ]]; then
        base_gh_issue_readiness_usage
        _BASE_GH_ISSUE_READINESS_EXIT_REQUESTED=1
        return 0
    fi
    [[ "$_BASE_GH_ISSUE_READINESS_ISSUE" =~ ^[0-9]+$ ]] || {
        base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Invalid issue number '$_BASE_GH_ISSUE_READINESS_ISSUE'."
        return $?
    }
    parser_args+=("$_BASE_GH_ISSUE_READINESS_ISSUE")
    shift

    while (($#)); do
        case "$1" in
            --repo)
                _BASE_GH_ISSUE_READINESS_REPOSITORY="${2:-}"
                [[ -n "$_BASE_GH_ISSUE_READINESS_REPOSITORY" ]] || {
                    base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Option '--repo' requires an argument."
                    return $?
                }
                parser_args+=("--repo=$2")
                shift
                ;;
            --project-owner)
                _BASE_GH_ISSUE_READINESS_PROJECT_OWNER="${2:-}"
                [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_OWNER" ]] || {
                    base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Option '--project-owner' requires an argument."
                    return $?
                }
                parser_args+=("--project-owner=$2")
                _BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED=1
                shift
                ;;
            --project-number)
                _BASE_GH_ISSUE_READINESS_PROJECT_NUMBER="${2:-}"
                [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER" ]] || {
                    base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Option '--project-number' requires an argument."
                    return $?
                }
                [[ "$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER" =~ ^[0-9]+$ ]] || {
                    base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Invalid project number '$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER'."
                    return $?
                }
                parser_args+=("--project-number=$2")
                _BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED=1
                shift
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Option '--format' requires an argument."
                    return $?
                }
                requested_format="$2"
                case "$requested_format" in
                    text|json)
                        ;;
                    *)
                        base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Unsupported issue readiness format '$requested_format'. Expected text or json."
                        return $?
                        ;;
                esac
                parser_args+=("--format=$2")
                _BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT="$requested_format"
                shift
                ;;
            -h|--help)
                base_gh_issue_readiness_usage
                _BASE_GH_ISSUE_READINESS_EXIT_REQUESTED=1
                return 0
                ;;
            *)
                base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" "Could not parse issue readiness arguments."
        return $?
    fi

    _BASE_GH_ISSUE_READINESS_ISSUE="${positionals[0]}"
    _BASE_GH_ISSUE_READINESS_REPOSITORY="${parsed_options[repo]:-}"
    _BASE_GH_ISSUE_READINESS_PROJECT_OWNER="${parsed_options[project_owner]:-}"
    _BASE_GH_ISSUE_READINESS_PROJECT_NUMBER="${parsed_options[project_number]:-}"
    _BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT="${parsed_options[format]:-text}"
    if [[ -n "${parsed_options[project_owner]+set}" || -n "${parsed_options[project_number]+set}" ]]; then
        _BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED=1
    fi

    if ((_BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED)) &&
        { [[ -z "$_BASE_GH_ISSUE_READINESS_PROJECT_OWNER" ]] || [[ -z "$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER" ]]; }; then
        base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" \
            "Options '--project-owner' and '--project-number' must be used together."
        return $?
    fi
}

base_gh_issue_readiness_resolve_repository() {
    [[ -n "$_BASE_GH_ISSUE_READINESS_REPOSITORY" ]] ||
        _BASE_GH_ISSUE_READINESS_REPOSITORY="$(base_gh_infer_github_repo || true)"
    [[ -n "$_BASE_GH_ISSUE_READINESS_REPOSITORY" ]] || {
        base_gh_issue_readiness_format_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" \
            "Unable to infer GitHub repository. Pass --repo <owner/name>."
        return $?
    }
}

base_gh_issue_readiness_fetch_remote_data() {
    local status

    _BASE_GH_ISSUE_READINESS_BODY="$(base_cli_gh_run issue view "$_BASE_GH_ISSUE_READINESS_ISSUE" \
        --repo "$_BASE_GH_ISSUE_READINESS_REPOSITORY" --json body --jq .body)"
    status=$?
    ((status == 0)) || {
        base_gh_issue_readiness_upstream_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" issue_view_body "$status"
        return $?
    }
    _BASE_GH_ISSUE_READINESS_LABELS_OUTPUT="$(base_cli_gh_run issue view "$_BASE_GH_ISSUE_READINESS_ISSUE" \
        --repo "$_BASE_GH_ISSUE_READINESS_REPOSITORY" --json labels --jq '.labels[].name')"
    status=$?
    ((status == 0)) || {
        base_gh_issue_readiness_upstream_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" issue_view_labels "$status"
        return $?
    }
    _BASE_GH_ISSUE_READINESS_ASSIGNEES_OUTPUT="$(base_cli_gh_run issue view "$_BASE_GH_ISSUE_READINESS_ISSUE" \
        --repo "$_BASE_GH_ISSUE_READINESS_REPOSITORY" --json assignees --jq '.assignees[].login')"
    status=$?
    ((status == 0)) || {
        base_gh_issue_readiness_upstream_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" issue_view_assignees "$status"
        return $?
    }
}

base_gh_issue_readiness_collect_body_findings() {
    local section

    while IFS= read -r section || [[ -n "$section" ]]; do
        [[ -n "$section" ]] || continue
        if ! base_gh_issue_readiness_has_section "$section" <<<"$_BASE_GH_ISSUE_READINESS_BODY"; then
            _BASE_GH_ISSUE_READINESS_MISSING_SECTIONS+=("$section")
        fi
    done < <(base_gh_issue_readiness_required_sections)
}

base_gh_issue_readiness_collect_project_findings() {
    local status field

    if ((_BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED)); then
        _BASE_GH_ISSUE_READINESS_PROJECT_ROW="$(base_gh_issue_readiness_project_row \
            "$_BASE_GH_ISSUE_READINESS_ISSUE" "$_BASE_GH_ISSUE_READINESS_REPOSITORY" \
            "$_BASE_GH_ISSUE_READINESS_PROJECT_OWNER" "$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER")"
        status=$?
        ((status == 0)) || {
            base_gh_issue_readiness_upstream_error "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" project_item_list "$status"
            return $?
        }
        if [[ -z "$_BASE_GH_ISSUE_READINESS_PROJECT_ROW" ]]; then
            _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS=("Project item")
            while IFS= read -r field || [[ -n "$field" ]]; do
                [[ -n "$field" ]] &&
                    _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS+=("$field")
            done < <(base_gh_issue_readiness_required_project_fields)
        else
            IFS=$'\037' read -r \
                _BASE_GH_ISSUE_READINESS_PROJECT_STATUS \
                _BASE_GH_ISSUE_READINESS_PROJECT_PRIORITY \
                _BASE_GH_ISSUE_READINESS_PROJECT_SIZE \
                _BASE_GH_ISSUE_READINESS_PROJECT_AREA \
                _BASE_GH_ISSUE_READINESS_PROJECT_INITIATIVE \
                <<<"$_BASE_GH_ISSUE_READINESS_PROJECT_ROW"
            [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_STATUS" ]] ||
                _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS+=("Status")
            [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_PRIORITY" ]] ||
                _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS+=("Priority")
            [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_SIZE" ]] ||
                _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS+=("Size")
            [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_AREA" ]] ||
                _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS+=("Area")
            [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_INITIATIVE" ]] ||
                _BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS+=("Initiative")
        fi
    fi
}

base_gh_issue_readiness_classify() {
    _BASE_GH_ISSUE_READINESS_LABELS_SUMMARY="$(
        base_gh_lines_to_csv <<<"$_BASE_GH_ISSUE_READINESS_LABELS_OUTPUT"
    )"
    _BASE_GH_ISSUE_READINESS_ASSIGNEES_SUMMARY="$(
        base_gh_lines_to_csv <<<"$_BASE_GH_ISSUE_READINESS_ASSIGNEES_OUTPUT"
    )"

    if ((${#_BASE_GH_ISSUE_READINESS_MISSING_SECTIONS[@]} ||
        ${#_BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS[@]})); then
        _BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE="not ready"
    elif ((!_BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED)); then
        _BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE="partial"
    fi
}

base_gh_issue_readiness_render_json() {
    local value
    local body_status=ok project_check_status=skipped envelope_status command_status=0
    local missing_sections_json missing_project_json labels_json assignees_json
    local project_owner_json project_number_json fields_json issue_number_json data_json

    while IFS= read -r value || [[ -n "$value" ]]; do
        [[ -n "$value" ]] && _BASE_GH_ISSUE_READINESS_LABELS+=("$value")
    done <<<"$_BASE_GH_ISSUE_READINESS_LABELS_OUTPUT"
    while IFS= read -r value || [[ -n "$value" ]]; do
        [[ -n "$value" ]] && _BASE_GH_ISSUE_READINESS_ASSIGNEES+=("$value")
    done <<<"$_BASE_GH_ISSUE_READINESS_ASSIGNEES_OUTPUT"

    missing_sections_json="$(base_inspection_json_string_array "${_BASE_GH_ISSUE_READINESS_MISSING_SECTIONS[@]}")"
    missing_project_json="$(base_inspection_json_string_array "${_BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS[@]}")"
    labels_json="$(base_inspection_json_string_array "${_BASE_GH_ISSUE_READINESS_LABELS[@]}")"
    assignees_json="$(base_inspection_json_string_array "${_BASE_GH_ISSUE_READINESS_ASSIGNEES[@]}")"
    project_owner_json="$(base_inspection_json_nullable_string "$_BASE_GH_ISSUE_READINESS_PROJECT_OWNER")"
    if [[ -n "$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER" ]]; then
        project_number_json="$(base_inspection_json_decimal "$_BASE_GH_ISSUE_READINESS_PROJECT_NUMBER")"
    else
        project_number_json=null
    fi
    printf -v fields_json \
        '{"status":%s,"priority":%s,"size":%s,"area":%s,"initiative":%s}' \
        "$(base_inspection_json_nullable_string "$_BASE_GH_ISSUE_READINESS_PROJECT_STATUS")" \
        "$(base_inspection_json_nullable_string "$_BASE_GH_ISSUE_READINESS_PROJECT_PRIORITY")" \
        "$(base_inspection_json_nullable_string "$_BASE_GH_ISSUE_READINESS_PROJECT_SIZE")" \
        "$(base_inspection_json_nullable_string "$_BASE_GH_ISSUE_READINESS_PROJECT_AREA")" \
        "$(base_inspection_json_nullable_string "$_BASE_GH_ISSUE_READINESS_PROJECT_INITIATIVE")"
    ((${#_BASE_GH_ISSUE_READINESS_MISSING_SECTIONS[@]})) && body_status=error
    if ((_BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED)); then
        ((${#_BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS[@]})) && project_check_status=error
    fi
    case "$_BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE" in
        ready)
            envelope_status=ok
            command_status=0
            ;;
        partial)
            envelope_status=warn
            command_status=1
            ;;
        *)
            envelope_status=error
            command_status=1
            ;;
    esac
    issue_number_json="$(base_inspection_json_decimal "$_BASE_GH_ISSUE_READINESS_ISSUE")"
    printf -v data_json \
        '{"issue_number":%s,"repository":%s,"readiness":%s,"body":{"status":%s,"missing_sections":%s},"project":{"requested":%s,"status":%s,"owner":%s,"number":%s,"missing_fields":%s,"fields":%s},"labels":%s,"assignees":%s}' \
        "$issue_number_json" \
        "$(base_inspection_json_string "$_BASE_GH_ISSUE_READINESS_REPOSITORY")" \
        "$(base_inspection_json_string "${_BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE// /_}")" \
        "$(base_inspection_json_string "$body_status")" \
        "$missing_sections_json" \
        "$( [[ "$_BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED" -eq 1 ]] && printf true || printf false )" \
        "$(base_inspection_json_string "$project_check_status")" \
        "$project_owner_json" \
        "$project_number_json" \
        "$missing_project_json" \
        "$fields_json" \
        "$labels_json" \
        "$assignees_json"
    base_inspection_json_envelope "gh issue readiness" "$envelope_status" "$data_json" null
    return "$command_status"
}

base_gh_issue_readiness_render_text() {
    printf 'Issue #%s readiness: %s\n' "$_BASE_GH_ISSUE_READINESS_ISSUE" \
        "$_BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE"
    printf 'Repository: %s\n' "$_BASE_GH_ISSUE_READINESS_REPOSITORY"
    if ((${#_BASE_GH_ISSUE_READINESS_MISSING_SECTIONS[@]})); then
        printf 'Body sections: missing %s\n' \
            "$(base_gh_join_csv "${_BASE_GH_ISSUE_READINESS_MISSING_SECTIONS[@]}")"
    else
        printf 'Body sections: ok\n'
    fi
    if ((_BASE_GH_ISSUE_READINESS_PROJECT_VALIDATION_REQUESTED)); then
        if ((${#_BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS[@]})); then
            printf 'Project fields: missing %s\n' \
                "$(base_gh_join_csv "${_BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS[@]}")"
        else
            printf 'Project fields: ok\n'
        fi
    else
        printf 'Project fields: skipped\n'
        printf 'Pass --project-owner and --project-number to validate Project fields.\n'
    fi
    printf 'Labels: %s\n' "$_BASE_GH_ISSUE_READINESS_LABELS_SUMMARY"
    printf 'Assignees: %s\n' "$_BASE_GH_ISSUE_READINESS_ASSIGNEES_SUMMARY"

    if ((${#_BASE_GH_ISSUE_READINESS_MISSING_SECTIONS[@]})); then
        printf 'Fix hint: add non-empty ## sections for the missing issue context.\n'
    fi
    if ((${#_BASE_GH_ISSUE_READINESS_MISSING_PROJECT_FIELDS[@]})); then
        printf 'Fix hint: set missing Project fields before assigning implementation work.\n'
    fi

    [[ "$_BASE_GH_ISSUE_READINESS_ISSUE_READY_STATE" == "ready" ]]
}

base_gh_issue_readiness() {
    base_gh_issue_readiness_reset
    base_gh_issue_readiness_parse_args "$@" || return $?
    (( _BASE_GH_ISSUE_READINESS_EXIT_REQUESTED )) && return 0
    base_gh_issue_readiness_resolve_repository || return $?
    base_gh_issue_readiness_fetch_remote_data || return $?
    base_gh_issue_readiness_collect_body_findings
    base_gh_issue_readiness_collect_project_findings || return $?
    base_gh_issue_readiness_classify

    if [[ "$_BASE_GH_ISSUE_READINESS_OUTPUT_FORMAT" == "json" ]]; then
        base_gh_issue_readiness_render_json
    else
        base_gh_issue_readiness_render_text
    fi
}
