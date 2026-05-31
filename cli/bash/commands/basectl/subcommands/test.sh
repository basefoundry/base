#!/usr/bin/env bash

[[ -n "${_base_test_subcommand_sourced:-}" ]] && return
_base_test_subcommand_sourced=1
readonly _base_test_subcommand_sourced

base_test_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl test [project] [options] [-- extra args...]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --dry-run           Print the resolved test command without running it.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared test command from its project root.
Use -- to pass additional arguments to the declared test command.
EOF
}

base_test_usage_error() {
    base_test_subcommand_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_test_project_venv_dir() {
    local project="$1"

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

base_test_format_extra_args() {
    local arg quoted output=""

    for arg in "$@"; do
        printf -v quoted '%q' "$arg"
        output+=" $quoted"
    done
    printf '%s\n' "$output"
}

base_test_command_with_extra_args() {
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

base_test_display_command() {
    local command="$1"
    shift

    if (($# == 0)); then
        printf '%s\n' "$command"
        return 0
    fi

    if [[ "$command" == mise\ run\ * ]]; then
        printf '%s --%s\n' "$command" "$(base_test_format_extra_args "$@")"
    else
        printf '%s%s\n' "$command" "$(base_test_format_extra_args "$@")"
    fi
}

base_test_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path test_command venv_dir
    local command_to_run display_command
    local dry_run=0 workspace_requested=0
    local args=() extra_args=()

    while (($#)); do
        case "$1" in
            --)
                shift
                extra_args=("$@")
                break
                ;;
            -h|--help|help)
                base_test_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_test_usage_error "Option '--workspace' requires an argument."
                    return $?
                }
                workspace_requested=1
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                workspace_requested=1
                args+=("$1")
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            -*)
                base_test_usage_error "Unknown test option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project" ]]; then
                    base_test_usage_error "The 'test' command accepts exactly one project name."
                    return $?
                fi
                project="$1"
                shift
                ;;
        esac
    done

    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_test_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    local command_args=(test-command)
    [[ -z "$project" ]] || command_args+=("$project")
    resolve_output="$("$wrapper" --project base base_projects "${command_args[@]}" "${args[@]}")" || return $?
    IFS=$'\t' read -r resolved_name project_root manifest_path test_command <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$test_command" ]] || {
        fatal_error "Unable to resolve test command for project '$project'."
    }

    venv_dir="$(base_test_project_venv_dir "$resolved_name")"
    export BASE_PROJECT="$resolved_name"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"

    if [[ -d "$venv_dir/bin" ]]; then
        PATH="$venv_dir/bin:$PATH"
        export PATH
    elif [[ "$dry_run" != "1" ]]; then
        log_warn "Project virtual environment was not found at '$venv_dir'. Run 'basectl setup $resolved_name' first."
    fi

    command_to_run="$(base_test_command_with_extra_args "$test_command" "${extra_args[@]}")"
    display_command="$(base_test_display_command "$test_command" "${extra_args[@]}")"

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run tests for project %q in %q: %s\n' "$resolved_name" "$project_root" "$display_command"
        return 0
    fi

    log_info "Running tests for project '$resolved_name': $display_command"
    (cd "$project_root" && bash -c "$command_to_run" basectl-test "${extra_args[@]}")
}
