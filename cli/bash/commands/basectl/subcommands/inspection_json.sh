#!/usr/bin/env bash

[[ -n "${_base_inspection_json_sourced:-}" ]] && return 0
_base_inspection_json_sourced=1
readonly _base_inspection_json_sourced

BASE_INSPECTION_JSON_SCHEMA_VERSION=1
readonly BASE_INSPECTION_JSON_SCHEMA_VERSION

base_inspection_find_output_format() {
    local result_name="$1"
    local candidate
    local format="text"
    shift

    while (($#)); do
        if [[ "$1" == "--format" ]]; then
            candidate="${2:-}"
            case "$candidate" in
                text|json) format="$candidate" ;;
            esac
            (($# >= 2)) && shift
        fi
        shift
    done

    printf -v "$result_name" '%s' "$format"
}

base_inspection_json_escape() {
    local value="$1"
    local char code index=0 length next1 next2 next3 width
    local LC_ALL=C

    length="${#value}"
    while ((index < length)); do
        char="${value:index:1}"
        # shellcheck disable=SC1003 # The backslash branch emits JSON's two-backslash escape.
        case "$char" in
            '"') printf '\\"'; index=$((index + 1)); continue ;;
            \\) printf '%s' '\\'; index=$((index + 1)); continue ;;
            $'\b') printf '\\b'; index=$((index + 1)); continue ;;
            $'\f') printf '\\f'; index=$((index + 1)); continue ;;
            $'\n') printf '\\n'; index=$((index + 1)); continue ;;
            $'\r') printf '\\r'; index=$((index + 1)); continue ;;
            $'\t') printf '\\t'; index=$((index + 1)); continue ;;
            *)
                printf -v code '%d' "'$char"
                if ((code < 32)); then
                    printf '\\u%04x' "$code"
                elif ((code < 128)); then
                    printf '%s' "$char"
                else
                    next1=-1
                    next2=-1
                    next3=-1
                    width=0
                    if ((index + 1 < length)); then
                        printf -v next1 '%d' "'${value:index+1:1}"
                    fi
                    if ((index + 2 < length)); then
                        printf -v next2 '%d' "'${value:index+2:1}"
                    fi
                    if ((index + 3 < length)); then
                        printf -v next3 '%d' "'${value:index+3:1}"
                    fi
                    if ((code >= 194 && code <= 223 && next1 >= 128 && next1 <= 191)); then
                        width=2
                    elif ((code == 224 && next1 >= 160 && next1 <= 191 && next2 >= 128 && next2 <= 191)); then
                        width=3
                    elif ((code >= 225 && code <= 236 && next1 >= 128 && next1 <= 191 && next2 >= 128 && next2 <= 191)); then
                        width=3
                    elif ((code == 237 && next1 >= 128 && next1 <= 159 && next2 >= 128 && next2 <= 191)); then
                        width=3
                    elif ((code >= 238 && code <= 239 && next1 >= 128 && next1 <= 191 && next2 >= 128 && next2 <= 191)); then
                        width=3
                    elif ((code == 240 && next1 >= 144 && next1 <= 191 && next2 >= 128 && next2 <= 191 && next3 >= 128 && next3 <= 191)); then
                        width=4
                    elif ((code >= 241 && code <= 243 && next1 >= 128 && next1 <= 191 && next2 >= 128 && next2 <= 191 && next3 >= 128 && next3 <= 191)); then
                        width=4
                    elif ((code == 244 && next1 >= 128 && next1 <= 143 && next2 >= 128 && next2 <= 191 && next3 >= 128 && next3 <= 191)); then
                        width=4
                    fi
                    if ((width)); then
                        printf '%s' "${value:index:width}"
                        index=$((index + width))
                        continue
                    fi
                    printf '\\u%04x' "$code"
                fi
                ;;
        esac
        index=$((index + 1))
    done
}

base_inspection_json_decimal() {
    local value="$1"

    while [[ "${#value}" -gt 1 && "$value" == 0* ]]; do
        value="${value#0}"
    done
    printf '%s' "$value"
}

base_inspection_json_decimal_fits_bash_integer() {
    local value="$1"
    local prefix suffix

    [[ "$value" =~ ^[0-9]+$ ]] || return 1
    if ((${#value} < 19)); then
        return 0
    fi
    if ((${#value} > 19)); then
        return 1
    fi
    prefix="${value:0:9}"
    suffix="${value:9}"
    if ((10#$prefix < 922337203)); then
        return 0
    fi
    if ((10#$prefix > 922337203)); then
        return 1
    fi
    ((10#$suffix <= 6854775807))
}

base_inspection_json_string() {
    printf '"'
    base_inspection_json_escape "$1"
    printf '"'
}

base_inspection_json_nullable_string() {
    if [[ -n "$1" ]]; then
        base_inspection_json_string "$1"
    else
        printf 'null'
    fi
}

base_inspection_json_string_array() {
    local separator=""
    local value

    printf '['
    for value in "$@"; do
        printf '%s' "$separator"
        base_inspection_json_string "$value"
        separator=,
    done
    printf ']'
}

base_inspection_json_error_object() {
    local error_type="$1"
    local message="$2"
    local details_json="${3:-}"

    [[ -n "$details_json" ]] || details_json='{}'

    printf '{"type":'
    base_inspection_json_string "$error_type"
    printf ',"message":'
    base_inspection_json_string "$message"
    printf ',"details":%s}' "$details_json"
}

base_inspection_json_envelope() {
    local command="$1"
    local status="$2"
    local data_json="${3:-}"
    local error_json="${4:-null}"

    [[ -n "$data_json" ]] || data_json='{}'

    printf '{"schema_version":%d,"command":' "$BASE_INSPECTION_JSON_SCHEMA_VERSION"
    base_inspection_json_string "$command"
    printf ',"status":'
    base_inspection_json_string "$status"
    printf ',"data":%s,"error":%s}\n' "$data_json" "$error_json"
}

base_inspection_json_emit_error() {
    local command="$1"
    local error_type="$2"
    local message="$3"
    local details_json="${4:-}"
    local error_json

    [[ -n "$details_json" ]] || details_json='{}'

    error_json="$(base_inspection_json_error_object "$error_type" "$message" "$details_json")"
    base_inspection_json_envelope "$command" error '{}' "$error_json"
}
