#!/usr/bin/env bash

[[ -n "${_base_command_protocol_sourced:-}" ]] && return 0
_base_command_protocol_sourced=1
readonly _base_command_protocol_sourced

readonly BASE_COMMAND_PROTOCOL_HEADER="BASE_COMMAND_PROTOCOL_V1"
readonly BASE_COMMAND_PROTOCOL_MAX_RECORD_COUNT=1000000
declare -gA BASE_COMMAND_PROTOCOL_FIELDS=()
declare -gA BASE_COMMAND_PROTOCOL_NULL_FIELDS=()
declare -g BASE_COMMAND_PROTOCOL_RECORD_COUNT=0

base_command_protocol_error() {
    printf 'ERROR: Invalid Base command protocol: %s\n' "$*" >&2
    return 1
}

base_command_protocol_record_fields() {
    case "$1" in
        project-list-entry)
            printf '%s\n' project_name project_root
            ;;
        project-reference)
            printf '%s\n' project_name project_root manifest_path
            ;;
        project-route)
            printf '%s\n' \
                project_name project_root manifest_path project_venv_dir \
                uses_uv_manager requires_project_python manifest_command_trust_required
            ;;
        project-command)
            printf '%s\n' \
                project_name project_root manifest_path project_venv_dir \
                uses_uv_manager requires_project_python manifest_command_trust_required command runner
            ;;
        named-command)
            printf '%s\n' project_name project_root manifest_path command_name command runner
            ;;
        build-target)
            printf '%s\n' \
                project_name project_root manifest_path project_venv_dir \
                uses_uv_manager requires_project_python manifest_command_trust_required target_name \
                working_dir command description runner
            ;;
        demo)
            printf '%s\n' \
                project_name project_root manifest_path project_venv_dir \
                uses_uv_manager requires_project_python manifest_command_trust_required demo_script runner
            ;;
        activation-source)
            printf '%s\n' source_path
            ;;
        *)
            return 1
            ;;
    esac
}

base_command_protocol_field_spec() {
    local record_type="$1"
    local field_name="$2"

    case "$record_type:$field_name" in
        project-list-entry:project_name|project-list-entry:project_root|\
        project-reference:project_name|project-reference:project_root|project-reference:manifest_path|\
        project-route:project_name|project-route:project_root|project-route:manifest_path|\
        project-route:project_venv_dir|\
        project-command:project_name|project-command:project_root|project-command:manifest_path|\
        project-command:project_venv_dir|project-command:command|\
        named-command:project_name|named-command:project_root|named-command:manifest_path|\
        named-command:command_name|named-command:command|\
        build-target:project_name|build-target:project_root|build-target:manifest_path|\
        build-target:project_venv_dir|build-target:target_name|build-target:working_dir|\
        build-target:command|\
        demo:project_name|demo:project_root|demo:manifest_path|demo:project_venv_dir|\
        demo:demo_script|activation-source:source_path)
            printf 'string\n'
            ;;
        project-route:uses_uv_manager|project-route:requires_project_python|\
        project-route:manifest_command_trust_required|project-command:uses_uv_manager|\
        project-command:requires_project_python|project-command:manifest_command_trust_required|\
        build-target:uses_uv_manager|build-target:requires_project_python|\
        build-target:manifest_command_trust_required|demo:uses_uv_manager|\
        demo:requires_project_python|demo:manifest_command_trust_required)
            printf 'boolean\n'
            ;;
        project-command:runner|named-command:runner|build-target:description|\
        build-target:runner|demo:runner)
            printf 'nullable-string\n'
            ;;
        *)
            return 1
            ;;
    esac
}

base_command_protocol_decode_hex() {
    local encoded="$1"
    local decoded=""
    local byte pair
    local index

    if (( ${#encoded} % 2 != 0 )) || [[ "$encoded" == *[!0-9a-f]* ]]; then
        base_command_protocol_error "string field has invalid lowercase hexadecimal data"
        return 1
    fi
    base_command_protocol_validate_utf8_hex "$encoded" || return 1

    for ((index = 0; index < ${#encoded}; index += 2)); do
        pair="${encoded:index:2}"
        [[ "$pair" != 00 ]] || {
            base_command_protocol_error "string field cannot contain NUL"
            return 1
        }
        printf -v byte '%b' "\\x$pair"
        decoded+="$byte"
    done
    BASE_COMMAND_PROTOCOL_DECODED_VALUE="$decoded"
}

base_command_protocol_validate_utf8_hex() {
    local encoded="$1"
    local byte continuation first index=0 length=${#1}
    local continuation_count continuation_min continuation_max

    while ((index < length)); do
        byte=$((16#${encoded:index:2}))
        ((index += 2))
        if ((byte <= 0x7f)); then
            continue
        elif ((byte >= 0xc2 && byte <= 0xdf)); then
            continuation_count=1
            continuation_min=0x80
            continuation_max=0xbf
        elif ((byte >= 0xe0 && byte <= 0xef)); then
            continuation_count=2
            if ((byte == 0xe0)); then
                continuation_min=0xa0
                continuation_max=0xbf
            elif ((byte == 0xed)); then
                continuation_min=0x80
                continuation_max=0x9f
            else
                continuation_min=0x80
                continuation_max=0xbf
            fi
        elif ((byte >= 0xf0 && byte <= 0xf4)); then
            continuation_count=3
            if ((byte == 0xf0)); then
                continuation_min=0x90
                continuation_max=0xbf
            elif ((byte == 0xf4)); then
                continuation_min=0x80
                continuation_max=0x8f
            else
                continuation_min=0x80
                continuation_max=0xbf
            fi
        else
            base_command_protocol_error "string field has invalid UTF-8 data"
            return 1
        fi

        ((index + continuation_count * 2 <= length)) || {
            base_command_protocol_error "string field has invalid UTF-8 data"
            return 1
        }
        first=$((16#${encoded:index:2}))
        ((first >= continuation_min && first <= continuation_max)) || {
            base_command_protocol_error "string field has invalid UTF-8 data"
            return 1
        }
        ((index += 2))
        for ((continuation = 1; continuation < continuation_count; continuation += 1)); do
            byte=$((16#${encoded:index:2}))
            ((byte >= 0x80 && byte <= 0xbf)) || {
                base_command_protocol_error "string field has invalid UTF-8 data"
                return 1
            }
            ((index += 2))
        done
    done
}

base_command_protocol_validate_record() {
    local record_type="$1"
    local field_name

    while IFS= read -r field_name; do
        [[ -n "$field_name" ]] || continue
        [[ -n "${BASE_COMMAND_PROTOCOL_FIELDS[$field_name]+present}" ]] || {
            base_command_protocol_error "record is missing field '$field_name' for '$record_type'"
            return 1
        }
    done < <(base_command_protocol_record_fields "$record_type")
}

base_command_protocol_parse_field() {
    local record_type="$1"
    local line="$2"
    local descriptor encoded field_name field_spec key value wire_type

    [[ "$line" == *=* ]] || {
        base_command_protocol_error "expected field.<name>:<type>=<payload>"
        return 1
    }
    key="${line%%=*}"
    encoded="${line#*=}"
    [[ "$key" == field.*:* ]] || {
        base_command_protocol_error "expected field.<name>:<type>=<payload>"
        return 1
    }
    descriptor="${key#field.}"
    field_name="${descriptor%%:*}"
    wire_type="${descriptor#*:}"
    [[ -n "$field_name" && -n "$wire_type" ]] || {
        base_command_protocol_error "expected field.<name>:<type>=<payload>"
        return 1
    }
    field_spec="$(base_command_protocol_field_spec "$record_type" "$field_name")" || {
        base_command_protocol_error "record has unknown field '$field_name' for '$record_type'"
        return 1
    }
    [[ -z "${BASE_COMMAND_PROTOCOL_FIELDS[$field_name]+present}" ]] || {
        base_command_protocol_error "record duplicates field '$field_name'"
        return 1
    }

    case "$field_spec:$wire_type" in
        string:string|nullable-string:string)
            base_command_protocol_decode_hex "$encoded" || return 1
            value="$BASE_COMMAND_PROTOCOL_DECODED_VALUE"
            ;;
        nullable-string:null)
            [[ -z "$encoded" ]] || {
                base_command_protocol_error "null field '$field_name' must have an empty payload"
                return 1
            }
            value=""
            BASE_COMMAND_PROTOCOL_NULL_FIELDS["$field_name"]=1
            ;;
        boolean:boolean)
            [[ "$encoded" == true || "$encoded" == false ]] || {
                base_command_protocol_error "boolean field '$field_name' must be true or false"
                return 1
            }
            value="$encoded"
            ;;
        *)
            base_command_protocol_error "field '$field_name' has wire type '$wire_type', expected '$field_spec'"
            return 1
            ;;
    esac
    BASE_COMMAND_PROTOCOL_FIELDS["$field_name"]="$value"
}

_base_command_protocol_parse_pass() {
    local expected_record_type="$1"
    local payload="$2"
    local callback="${3:-}"
    local count_text="" ended=0 in_record=0 line record_index=-1 record_type=""
    local line_number=0 next_record=0

    BASE_COMMAND_PROTOCOL_RECORD_COUNT=0
    BASE_COMMAND_PROTOCOL_FIELDS=()
    BASE_COMMAND_PROTOCOL_NULL_FIELDS=()

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_number += 1))
        case "$line_number" in
            1)
                [[ "$line" == "$BASE_COMMAND_PROTOCOL_HEADER" ]] || {
                    base_command_protocol_error "unsupported protocol header"
                    return 1
                }
                continue
                ;;
            2)
                [[ "$line" == record_type=* ]] || {
                    base_command_protocol_error "missing record_type metadata"
                    return 1
                }
                record_type="${line#record_type=}"
                [[ "$record_type" == "$expected_record_type" ]] || {
                    base_command_protocol_error "expected record_type '$expected_record_type', got '$record_type'"
                    return 1
                }
                base_command_protocol_record_fields "$record_type" >/dev/null || {
                    base_command_protocol_error "unsupported record_type '$record_type'"
                    return 1
                }
                continue
                ;;
            3)
                [[ "$line" == record_count=* ]] || {
                    base_command_protocol_error "missing record_count metadata"
                    return 1
                }
                count_text="${line#record_count=}"
                [[ "$count_text" =~ ^(0|[1-9][0-9]*)$ ]] || {
                    base_command_protocol_error "record_count must be a canonical non-negative integer"
                    return 1
                }
                ((${#count_text} <= ${#BASE_COMMAND_PROTOCOL_MAX_RECORD_COUNT})) || {
                    base_command_protocol_error \
                        "record_count exceeds protocol maximum of $BASE_COMMAND_PROTOCOL_MAX_RECORD_COUNT"
                    return 1
                }
                BASE_COMMAND_PROTOCOL_RECORD_COUNT="$((10#$count_text))"
                ((BASE_COMMAND_PROTOCOL_RECORD_COUNT <= BASE_COMMAND_PROTOCOL_MAX_RECORD_COUNT)) || {
                    base_command_protocol_error \
                        "record_count exceeds protocol maximum of $BASE_COMMAND_PROTOCOL_MAX_RECORD_COUNT"
                    return 1
                }
                continue
                ;;
        esac

        ((ended == 0)) || {
            base_command_protocol_error "unexpected data after end_protocol marker"
            return 1
        }
        if ((in_record == 0)); then
            if [[ "$line" == "record=$next_record" && next_record -lt BASE_COMMAND_PROTOCOL_RECORD_COUNT ]]; then
                record_index="$next_record"
                BASE_COMMAND_PROTOCOL_FIELDS=()
                # shellcheck disable=SC2034 # Nullable state is an output contract read by callbacks.
                BASE_COMMAND_PROTOCOL_NULL_FIELDS=()
                in_record=1
                continue
            fi
            if [[ "$line" == "end_protocol=" && next_record -eq BASE_COMMAND_PROTOCOL_RECORD_COUNT ]]; then
                ended=1
                continue
            fi
            base_command_protocol_error "expected record=$next_record or end_protocol marker"
            return 1
        fi

        if [[ "$line" == field.* ]]; then
            base_command_protocol_parse_field "$record_type" "$line" || return 1
            continue
        fi
        if [[ "$line" == "end_record=$record_index" ]]; then
            base_command_protocol_validate_record "$record_type" || return 1
            if [[ -n "$callback" ]]; then
                "$callback" || return $?
            fi
            ((next_record += 1))
            in_record=0
            continue
        fi
        base_command_protocol_error "expected a field or end_record=$record_index"
        return 1
    done <<<"$payload"

    ((line_number >= 3)) || {
        base_command_protocol_error "incomplete protocol metadata"
        return 1
    }
    ((in_record == 0 && ended == 1)) || {
        base_command_protocol_error "protocol ended before all records were complete"
        return 1
    }
}

base_command_protocol_parse() {
    _base_command_protocol_parse_pass "$1" "$2"
}

base_command_protocol_decode_one() {
    local expected_record_type="$1"
    local payload="$2"

    base_command_protocol_parse "$expected_record_type" "$payload" || return 1
    ((BASE_COMMAND_PROTOCOL_RECORD_COUNT == 1)) || {
        base_command_protocol_error "expected exactly one '$expected_record_type' record"
        return 1
    }
}

base_command_protocol_each() {
    local expected_record_type="$1"
    local payload="$2"
    local callback="$3"

    [[ -n "$callback" ]] || {
        base_command_protocol_error "record callback is required"
        return 1
    }
    # Validate the entire envelope before exposing the first record. The second
    # pass invokes callbacks only after framing, count, schema, and types for all
    # records are known to be valid.
    base_command_protocol_parse "$expected_record_type" "$payload" || return 1
    _base_command_protocol_parse_pass "$expected_record_type" "$payload" "$callback"
}
