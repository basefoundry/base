#!/usr/bin/env bash

[[ -n "${_base_project_command_helpers_sourced:-}" ]] && return 0
_base_project_command_helpers_sourced=1
readonly _base_project_command_helpers_sourced

base_project_venv_dir() {
    local project="$1"
    local project_root="${2:-}"
    local route_venv_dir="${3:-}"

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    if [[ -n "$route_venv_dir" ]]; then
        printf '%s\n' "$route_venv_dir"
        return 0
    fi

    if [[ "$project" != base && -n "$project_root" ]]; then
        printf '%s\n' "$project_root/.venv"
        return 0
    fi

    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

base_project_venv_uses_project_local_default() {
    local project="$1"
    local project_root="${2:-}"
    local venv_dir="${3:-}"

    [[ "$project" != base && -n "$project_root" && "$venv_dir" == "$project_root/.venv" ]]
}

base_project_venv_fix() {
    local project="$1"
    local project_root="${2:-}"
    local venv_dir="${3:-}"
    local uses_uv_manager="${4:-false}"

    if [[ -z "${BASE_PROJECT_VENV_DIR:-}" && "$uses_uv_manager" == true ]]; then
        printf "Run 'uv sync' in '%s' first." "$project_root"
        return 0
    fi
    if [[ -z "${BASE_PROJECT_VENV_DIR:-}" ]] && base_project_venv_uses_project_local_default "$project" "$project_root" "$venv_dir"; then
        printf "Run 'basectl setup %s' first. To keep using an external Base-managed virtual environment, set python.venv_location: external in base_manifest.yaml or export BASE_PROJECT_VENV_DIR." "$project"
        return 0
    fi
    printf "Run 'basectl setup %s' first." "$project"
}

base_project_require_manifest_command_trust() {
    local project="$1"
    local manifest_path="$2"
    local trust_required="${3:-false}"
    local wrapper="$BASE_HOME/bin/base-wrapper"

    [[ "$trust_required" == true ]] || return 0
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    "$wrapper" --project base base_trust require "$project" --manifest "$manifest_path"
}

base_project_activate_environment() {
    local project="$1"
    local project_root="$2"
    local manifest_path="$3"
    local dry_run="${4:-0}"
    local route_venv_dir="${5:-}"
    local uses_uv_manager="${6:-false}"
    local venv_dir venv_fix

    venv_dir="$(base_project_venv_dir "$project" "$project_root" "$route_venv_dir")"
    venv_fix="$(base_project_venv_fix "$project" "$project_root" "$venv_dir" "$uses_uv_manager")"
    export BASE_PROJECT="$project"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"

    if [[ -d "$venv_dir/bin" ]]; then
        PATH="$venv_dir/bin:$PATH"
        export PATH
    elif [[ "$dry_run" != "1" ]]; then
        log_warn "Project virtual environment was not found at '$venv_dir'. $venv_fix"
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
