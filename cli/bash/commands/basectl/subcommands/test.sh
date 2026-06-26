#!/usr/bin/env bash

[[ -n "${_base_test_subcommand_sourced:-}" ]] && return 0
_base_test_subcommand_sourced=1
readonly _base_test_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

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
    print_error "$*"
    return 2
}

base_test_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path test_command command_runner
    local command_to_run display_command
    local dry_run=0 workspace_requested=0
    local args=() extra_args=()
    local resolve_fields=()

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
    IFS=$'\t' read -r -a resolve_fields <<<"$resolve_output"
    resolved_name="${resolve_fields[0]:-}"
    project_root="${resolve_fields[1]:-}"
    manifest_path="${resolve_fields[2]:-}"
    test_command="${resolve_fields[3]:-}"
    command_runner="$(base_project_command_runner_from_field "${resolve_fields[4]:-}" || true)"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$test_command" ]] || {
        fatal_error "Unable to resolve test command for project '$project'."
    }

    base_project_activate_environment "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "${resolve_fields[@]:4}" >/dev/null

    command_runner="${command_runner:-}"
    command_to_run="$(base_command_with_runner "$command_runner" "$test_command" "${extra_args[@]}")" || return $?
    display_command="$(base_display_command_with_runner "$command_runner" "$test_command" "${extra_args[@]}")" || return $?

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run tests for project %q in %q: %s\n' "$resolved_name" "$project_root" "$display_command"
        return 0
    fi

    log_info "Running tests for project '$resolved_name': $display_command"
    base_validate_command_runner "$command_runner"
    base_project_run_shell_command "$project_root" "$command_to_run" basectl-test "${extra_args[@]}"
}
