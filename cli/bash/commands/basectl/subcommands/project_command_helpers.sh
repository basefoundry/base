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

base_project_route_manifest_command_trust_required() {
    [[ "$(base_project_route_value "__base_manifest_command_trust_required=" "$@" || true)" == "true" ]]
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

base_project_require_manifest_command_trust() {
    local project="$1"
    local manifest_path="$2"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    shift 2

    base_project_route_manifest_command_trust_required "$@" || return 0
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    "$wrapper" --project base base_trust require "$project" --manifest "$manifest_path"
}

base_project_activate_environment() {
    local project="$1"
    local project_root="$2"
    local manifest_path="$3"
    local dry_run="${4:-0}"
    local route_fields=("${@:5}")
    local venv_dir

    venv_dir="$(base_project_venv_dir "$project" "$project_root" "$manifest_path" "${route_fields[@]}")"
    export BASE_PROJECT="$project"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"

    if [[ -d "$venv_dir/bin" ]]; then
        PATH="$venv_dir/bin:$PATH"
        export PATH
    elif [[ "$dry_run" != "1" ]]; then
        log_warn "Project virtual environment was not found at '$venv_dir'. Run 'basectl setup $project' first."
    fi

    printf '%s\n' "$venv_dir"
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

base_project_run_shell_command() {
    local working_dir="$1"
    local command_to_run="$2"
    local command_name="$3"
    shift 3

    # Bash assigns the word after `bash -c <command>` to `$0`; use a stable
    # sentinel so delegated extra args start at `$1` and populate `$@`.
    (cd "$working_dir" && bash -c "$command_to_run" "$command_name" "$@")
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
