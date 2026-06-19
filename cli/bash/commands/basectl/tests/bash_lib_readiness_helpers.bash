# Shared assertions for Base Bash library readiness diagnostics.

base_bash_libraries_json_status() {
    local payload="$1"

    case "$payload" in
        *'"id":"BASE-D007","status":"ok","name":"base_bash_libraries"'*)
            printf '%s\n' "ok"
            ;;
        *'"id":"BASE-D007","status":"warn","name":"base_bash_libraries"'*)
            printf '%s\n' "warn"
            ;;
        *)
            return 1
            ;;
    esac
}

assert_base_bash_libraries_json_finding() {
    local payload="$1"
    local status

    if ! status="$(base_bash_libraries_json_status "$payload")"; then
        printf 'BASE-D007 finding was not present in diagnostic JSON.\n' >&2
        return 1
    fi

    case "$status" in
        ok)
            [[ "$payload" == *"Base is using reusable Bash libraries from"* ]]
            ;;
        warn)
            [[ "$payload" == *"Base Bash library source could not be determined"* ]]
            [[ "$payload" == *"BASE_BASH_LIBS_DIR"* ]]
            ;;
        *)
            printf 'Unexpected BASE-D007 status: %s\n' "$status" >&2
            return 1
            ;;
    esac
}

assert_base_check_json_status_for_readiness() {
    local payload="$1"
    local readiness_status

    readiness_status="$(base_bash_libraries_json_status "$payload")" || return 1
    if [[ "$readiness_status" == warn ]]; then
        [[ "$payload" == *'"status": "warn"'* ]]
    else
        [[ "$payload" == *'"status": "ok"'* ]]
    fi
}

base_bash_libraries_json_line() {
    local payload="$1"

    printf '%s\n' "$payload" |
        grep -n '"id":"BASE-D007","status":"[a-z]*","name":"base_bash_libraries"' |
        cut -d: -f1
}
