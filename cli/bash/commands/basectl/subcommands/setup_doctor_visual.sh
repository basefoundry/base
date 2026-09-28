#!/usr/bin/env bash

[[ -n "${_base_setup_doctor_visual_sourced:-}" ]] && return 0
_base_setup_doctor_visual_sourced=1
readonly _base_setup_doctor_visual_sourced

setup_doctor_visual_status_enabled() {
    [[ "${BASE_SETUP_DOCTOR_NO_COLOR:-false}" != true ]] || return 1
    [[ -z "${NO_COLOR:-}" ]] || return 1
    [[ -n "${TERM:-}" && "${TERM:-}" != dumb ]] || return 1
    [[ -t 1 ]]
}

setup_doctor_status_visual_parts() {
    local status="$1"
    local label color padding

    case "$status" in
        ok)
            label="✓ ok"
            color=$'\033[0;32m'
            padding="   "
            ;;
        warn)
            label="! warn"
            color=$'\033[0;33m'
            padding=" "
            ;;
        error)
            label="✗ error"
            color=$'\033[0;31m'
            padding=""
            ;;
        *)
            label="$status"
            color=""
            padding=""
            ;;
    esac

    printf '%s\t%s\t%s\n' "$label" "$color" "$padding"
}

setup_print_doctor_finding() {
    local status="$1"
    local finding_id="$2"
    local name="$3"
    local message="$4"
    local fix="${5:-}"
    local color fix_indent label padding reset status_prefix

    if setup_doctor_visual_status_enabled; then
        IFS=$'\t' read -r label color padding <<<"$(setup_doctor_status_visual_parts "$status")"
        reset=$'\033[0m'
        status_prefix="${label}${padding}  "
        printf '%b%s%b%s  %-9s  %-26s  %s\n' "$color" "$label" "$reset" "$padding" "$finding_id" "$name" "$message"
        fix_indent=${#status_prefix}
    else
        status_prefix="$(printf '%-5s  ' "$status")"
        printf '%s%-9s  %-26s  %s\n' "$status_prefix" "$finding_id" "$name" "$message"
        fix_indent=${#status_prefix}
    fi
    if [[ -n "$fix" ]]; then
        printf '%*sFix: %s\n' "$fix_indent" '' "$fix"
    fi
}
