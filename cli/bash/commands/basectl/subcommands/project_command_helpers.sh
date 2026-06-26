#!/usr/bin/env bash

[[ -n "${_base_project_command_helpers_sourced:-}" ]] && return 0
_base_project_command_helpers_sourced=1
readonly _base_project_command_helpers_sourced

base_project_route_value() {
    local marker="$1" field
    shift

    for field in "$@"; do
        case "$field" in
            "$marker"*)
                printf '%s\n' "${field#"$marker"}"
                return 0
                ;;
        esac
    done
    return 1
}

base_project_route_venv_dir() {
    base_project_route_value "__base_project_venv_dir=" "$@"
}

base_project_route_uses_uv_manager() {
    [[ "$(base_project_route_value "__base_uses_uv_manager=" "$@" || true)" == "true" ]]
}

base_project_command_runner_from_field() {
    local candidate="${1:-}"

    [[ -n "$candidate" ]] || return 1
    [[ "$candidate" != __base_* ]] || return 1
    printf '%s\n' "$candidate"
}

base_project_venv_dir() {
    local project="$1"
    local project_root="${2:-}"
    local manifest_path="${3:-}"
    local route_fields=("${@:4}")
    local route_venv_dir=""

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    route_venv_dir="$(base_project_route_venv_dir "${route_fields[@]}" || true)"
    if [[ -n "$route_venv_dir" ]]; then
        printf '%s\n' "$route_venv_dir"
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

base_command_with_runner() {
    local runner="$1" command="$2" command_with_args
    shift 2

    command_with_args="$(base_command_with_extra_args "$command" "$@")"
    case "$runner" in
        "")
            printf '%s\n' "$command_with_args"
            ;;
        uv)
            printf 'uv run -- %s\n' "$command_with_args"
            ;;
        *)
            printf 'Unsupported command runner %q.\n' "$runner" >&2
            return 2
            ;;
    esac
}

base_validate_command_runner() {
    local runner="$1"

    case "$runner" in
        "")
            return 0
            ;;
        uv)
            command -v uv >/dev/null 2>&1 || {
                fatal_error "Command runner 'uv' is not available. Install uv or remove runner: uv from the project manifest."
            }
            ;;
        *)
            fatal_error "Unsupported command runner '$runner'."
            ;;
    esac
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

base_display_command_with_runner() {
    local runner="$1" command="$2" display_command
    shift 2

    display_command="$(base_display_command "$command" "$@")"
    case "$runner" in
        "")
            printf '%s\n' "$display_command"
            ;;
        uv)
            printf 'uv run -- %s\n' "$display_command"
            ;;
        *)
            printf 'Unsupported command runner %q.\n' "$runner" >&2
            return 2
            ;;
    esac
}
