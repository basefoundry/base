#!/usr/bin/env bash

[[ -n "${_base_project_command_helpers_sourced:-}" ]] && return
_base_project_command_helpers_sourced=1
readonly _base_project_command_helpers_sourced

base_project_venv_dir() {
    local project="$1"

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

base_format_extra_args() {
    local arg quoted output=""

    for arg in "$@"; do
        printf -v quoted '%q' "$arg"
        output+=" $quoted"
    done
    printf '%s\n' "$output"
}

base_command_with_extra_args() {
    local command="$1"
    shift

    if (($# == 0)); then
        printf '%s\n' "$command"
        return 0
    fi

    if [[ "$command" == mise\ run\ * ]]; then
        printf '%s -- "$@"\n' "$command"
    else
        printf '%s "$@"\n' "$command"
    fi
}

base_display_command() {
    local command="$1"
    shift

    if (($# == 0)); then
        printf '%s\n' "$command"
        return 0
    fi

    if [[ "$command" == mise\ run\ * ]]; then
        printf '%s --%s\n' "$command" "$(base_format_extra_args "$@")"
    else
        printf '%s%s\n' "$command" "$(base_format_extra_args "$@")"
    fi
}
