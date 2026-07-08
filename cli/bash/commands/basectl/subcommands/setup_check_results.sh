#!/usr/bin/env bash

[[ -n "${_base_setup_check_results_sourced:-}" ]] && return 0
_base_setup_check_results_sourced=1
readonly _base_setup_check_results_sourced

_BASE_SETUP_CHECK_NAMES=()
_BASE_SETUP_CHECK_OK=()
_BASE_SETUP_CHECK_STATUSES=()
_BASE_SETUP_CHECK_MESSAGES=()
_BASE_SETUP_CHECK_RECOVERIES=()
_BASE_SETUP_CHECK_DEBUG_MESSAGES=()
_BASE_SETUP_PARSED_CHECK_NAME=""
_BASE_SETUP_PARSED_CHECK_OK=""
_BASE_SETUP_PARSED_CHECK_STATUS=""
_BASE_SETUP_PARSED_CHECK_MESSAGE=""
_BASE_SETUP_PARSED_CHECK_RECOVERY=""
_BASE_SETUP_PARSED_CHECK_DEBUG_MESSAGE=""

setup_clear_check_results() {
    _BASE_SETUP_CHECK_NAMES=()
    _BASE_SETUP_CHECK_OK=()
    _BASE_SETUP_CHECK_STATUSES=()
    _BASE_SETUP_CHECK_MESSAGES=()
    _BASE_SETUP_CHECK_RECOVERIES=()
    _BASE_SETUP_CHECK_DEBUG_MESSAGES=()
}

setup_add_check_result_with_status() {
    local name="$1"
    local status="$2"
    local message="$3"
    local recovery="${4:-}"
    local debug_message="${5:-}"
    local ok=true

    case "$status" in
        ok|warn)
            ok=true
            ;;
        error)
            ok=false
            ;;
        *)
            fatal_error "Invalid Base check status '$status'."
            ;;
    esac

    _BASE_SETUP_CHECK_NAMES+=("$name")
    _BASE_SETUP_CHECK_OK+=("$ok")
    _BASE_SETUP_CHECK_STATUSES+=("$status")
    _BASE_SETUP_CHECK_MESSAGES+=("$message")
    _BASE_SETUP_CHECK_RECOVERIES+=("$recovery")
    _BASE_SETUP_CHECK_DEBUG_MESSAGES+=("$debug_message")
}

setup_add_check_result() {
    local name="$1"
    local ok="$2"
    local message="$3"
    local recovery="${4:-}"
    local debug_message="${5:-}"
    local status

    status="$(setup_diagnostic_status_from_ok "$ok")"
    setup_add_check_result_with_status "$name" "$status" "$message" "$recovery" "$debug_message"
}

setup_write_check_result_file() {
    local debug_message="${6:-}"
    local message="$4"
    local name="$2"
    local ok="$3"
    local path="$1"
    local recovery="${5:-}"
    local status="${7:-}"

    if [[ -z "$status" ]]; then
        status="$(setup_diagnostic_status_from_ok "$ok")"
    fi

    {
        printf 'name=%s\n' "$name"
        printf 'ok=%s\n' "$ok"
        printf 'status=%s\n' "$status"
        printf 'message=%s\n' "$message"
        printf 'recovery=%s\n' "$recovery"
        printf 'debug=%s\n' "$debug_message"
    } >"$path"
}

setup_parse_check_result_file() {
    local line path="$1"

    [[ -f "$path" ]] || fatal_error "Base check probe did not produce result file '$path'."

    _BASE_SETUP_PARSED_CHECK_NAME=""
    _BASE_SETUP_PARSED_CHECK_OK=""
    _BASE_SETUP_PARSED_CHECK_STATUS=""
    _BASE_SETUP_PARSED_CHECK_MESSAGE=""
    _BASE_SETUP_PARSED_CHECK_RECOVERY=""
    _BASE_SETUP_PARSED_CHECK_DEBUG_MESSAGE=""

    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            name=*)
                _BASE_SETUP_PARSED_CHECK_NAME="${line#name=}"
                ;;
            ok=*)
                _BASE_SETUP_PARSED_CHECK_OK="${line#ok=}"
                ;;
            status=*)
                _BASE_SETUP_PARSED_CHECK_STATUS="${line#status=}"
                ;;
            message=*)
                _BASE_SETUP_PARSED_CHECK_MESSAGE="${line#message=}"
                ;;
            recovery=*)
                _BASE_SETUP_PARSED_CHECK_RECOVERY="${line#recovery=}"
                ;;
            debug=*)
                _BASE_SETUP_PARSED_CHECK_DEBUG_MESSAGE="${line#debug=}"
                ;;
        esac
    done <"$path"

    [[ -n "$_BASE_SETUP_PARSED_CHECK_NAME" ]] || fatal_error "Base check probe result '$path' is missing a name."
    case "$_BASE_SETUP_PARSED_CHECK_OK" in
        true|false)
            ;;
        *)
            fatal_error "Base check probe result '$path' has invalid ok value '$_BASE_SETUP_PARSED_CHECK_OK'."
            ;;
    esac
    if [[ -z "$_BASE_SETUP_PARSED_CHECK_STATUS" ]]; then
        _BASE_SETUP_PARSED_CHECK_STATUS="$(setup_diagnostic_status_from_ok "$_BASE_SETUP_PARSED_CHECK_OK")"
    fi
    case "$_BASE_SETUP_PARSED_CHECK_STATUS" in
        ok|warn|error)
            ;;
        *)
            fatal_error "Base check probe result '$path' has invalid status value '$_BASE_SETUP_PARSED_CHECK_STATUS'."
            ;;
    esac
    [[ -n "$_BASE_SETUP_PARSED_CHECK_MESSAGE" ]] || fatal_error "Base check probe result '$path' is missing a message."
}

setup_add_parsed_check_result() {
    setup_add_check_result_with_status \
        "$_BASE_SETUP_PARSED_CHECK_NAME" \
        "$_BASE_SETUP_PARSED_CHECK_STATUS" \
        "$_BASE_SETUP_PARSED_CHECK_MESSAGE" \
        "$_BASE_SETUP_PARSED_CHECK_RECOVERY" \
        "$_BASE_SETUP_PARSED_CHECK_DEBUG_MESSAGE"
}

setup_read_check_result_file() {
    setup_parse_check_result_file "$1"
    setup_add_parsed_check_result
    [[ "$_BASE_SETUP_PARSED_CHECK_STATUS" != error ]]
}
