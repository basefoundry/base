#!/usr/bin/env bash

[[ -n "${_base_demo_subcommand_sourced:-}" ]] && return 0
_base_demo_subcommand_sourced=1
readonly _base_demo_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

base_demo_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl demo [project] [options] [-- extra args...]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --dry-run           Print the resolved demo script without running it.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared interactive demo from its project root.
Use -- to pass additional arguments to the demo script.
EOF
}

base_demo_usage_error() {
    base_demo_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_demo_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path demo_script command_runner
    local quoted_demo_script command_to_run display_command
    local dry_run=0 workspace_requested=0
    local args=() extra_args=() project_args=()
    local resolve_fields=()

    while (($#)); do
        case "$1" in
            --)
                shift
                extra_args=("$@")
                break
                ;;
            -h|--help|help)
                base_demo_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_demo_usage_error "Option '--workspace' requires an argument."
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
                base_demo_usage_error "Unknown demo option '$1'."
                return $?
                ;;
            *)
                if [[ -z "$project" ]]; then
                    project="$1"
                else
                    base_demo_usage_error "The 'demo' command accepts one project name."
                    return $?
                fi
                shift
                ;;
        esac
    done

    [[ "$workspace_requested" != "1" || -n "$project" ]] || {
        base_demo_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    [[ -n "$project" ]] && project_args+=("$project")
    resolve_output="$("$wrapper" --project base base_projects demo-script "${project_args[@]}" "${args[@]}")" || return $?
    IFS=$'\t' read -r -a resolve_fields <<<"$resolve_output"
    resolved_name="${resolve_fields[0]:-}"
    project_root="${resolve_fields[1]:-}"
    manifest_path="${resolve_fields[2]:-}"
    demo_script="${resolve_fields[3]:-}"
    command_runner="$(base_project_command_runner_from_field "${resolve_fields[4]:-}" || true)"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$demo_script" ]] || {
        fatal_error "Unable to resolve demo script for project '${project:-current project}'."
    }

    command_runner="${command_runner:-}"
    printf -v quoted_demo_script '%q' "$demo_script"
    command_to_run="$(base_command_with_runner "$command_runner" "$quoted_demo_script" "${extra_args[@]}")" || return $?
    display_command="$(base_display_command_with_runner "$command_runner" "$quoted_demo_script" "${extra_args[@]}")" || return $?

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run demo for project %q in %q: %s\n' \
            "$resolved_name" "$project_root" "$display_command"
        return 0
    fi

    base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "${resolve_fields[@]:4}" || return $?
    base_project_activate_environment "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "${resolve_fields[@]:4}" >/dev/null

    log_info "Running demo for project '$resolved_name': $display_command"
    if [[ -z "$command_runner" ]]; then
        (cd "$project_root" && "$demo_script" "${extra_args[@]}")
        return $?
    fi
    base_validate_command_runner "$command_runner"
    base_project_run_shell_command "$project_root" "$command_to_run" basectl-demo "${extra_args[@]}"
}
