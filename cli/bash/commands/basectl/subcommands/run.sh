#!/usr/bin/env bash

[[ -n "${_base_run_subcommand_sourced:-}" ]] && return
_base_run_subcommand_sourced=1
readonly _base_run_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

base_run_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl run <project> <command> [options] [-- extra args...]
  basectl run [project] --list [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --dry-run           Print the resolved command without running it.
  --list              List runnable commands for a project. Defaults to the nearest project.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared command from its project root.
Use -- to pass additional arguments to the declared command.
EOF
}

base_run_usage_error() {
    base_run_subcommand_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_run_list_commands() {
    local project="$1"
    shift
    local args=("$@")
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local command_args=(run-commands)
    local list_output line resolved_name project_root manifest_path command_name command_text
    local printed_header=0

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    [[ -z "$project" ]] || command_args+=("$project")

    list_output="$("$wrapper" --project base base_projects "${command_args[@]}" "${args[@]}")" || return $?
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        IFS=$'\t' read -r resolved_name project_root manifest_path command_name command_text <<<"$line"
        [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$command_name" ]] || {
            fatal_error "Unable to parse runnable commands for project '$project'."
        }
        if ((printed_header == 0)); then
            printf "Commands for project '%s'\n\n" "$resolved_name"
            printed_header=1
        fi
        printf '%-20s %s\n' "$command_name" "$command_text"
    done <<<"$list_output"
}

base_run_subcommand_main() {
    local project="" command_name="" wrapper resolve_output resolved_name project_root manifest_path run_command venv_dir
    local command_to_run display_command
    local dry_run=0 list_commands=0 workspace_requested=0
    local args=() extra_args=()

    while (($#)); do
        case "$1" in
            --)
                shift
                extra_args=("$@")
                break
                ;;
            -h|--help|help)
                base_run_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_run_usage_error "Option '--workspace' requires an argument."
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
            --list)
                list_commands=1
                shift
                ;;
            -*)
                base_run_usage_error "Unknown run option '$1'."
                return $?
                ;;
            *)
                if [[ -z "$project" ]]; then
                    project="$1"
                elif [[ -z "$command_name" ]]; then
                    command_name="$1"
                else
                    base_run_usage_error "The 'run' command accepts one project name and one command name."
                    return $?
                fi
                shift
                ;;
        esac
    done

    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_run_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }
    if [[ "$list_commands" == "1" ]]; then
        [[ -z "$command_name" ]] || {
            base_run_usage_error "Option '--list' cannot be combined with a command name."
            return $?
        }
        [[ ${#extra_args[@]} -eq 0 ]] || {
            base_run_usage_error "Option '--list' cannot be combined with extra command arguments."
            return $?
        }
        base_run_list_commands "$project" "${args[@]}"
        return $?
    fi

    [[ -n "$project" ]] || {
        base_run_usage_error "Project name is required."
        return $?
    }
    [[ -n "$command_name" ]] || {
        base_run_usage_error "Command name is required."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    resolve_output="$("$wrapper" --project base base_projects run-command "$project" "$command_name" "${args[@]}")" || return $?
    IFS=$'\t' read -r resolved_name project_root manifest_path run_command <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$run_command" ]] || {
        fatal_error "Unable to resolve command '$command_name' for project '$project'."
    }

    venv_dir="$(base_project_venv_dir "$resolved_name")"
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

    command_to_run="$(base_command_with_extra_args "$run_command" "${extra_args[@]}")"
    display_command="$(base_display_command "$run_command" "${extra_args[@]}")"

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run command %q for project %q in %q: %s\n' \
            "$command_name" "$resolved_name" "$project_root" "$display_command"
        return 0
    fi

    log_info "Running command '$command_name' for project '$resolved_name': $display_command"
    (cd "$project_root" && bash -c "$command_to_run" basectl-run "${extra_args[@]}")
}
