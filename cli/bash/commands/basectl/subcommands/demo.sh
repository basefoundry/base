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
  --project <name>    Select a project explicitly instead of the positional or nearest project.
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
    local project="" explicit_project="" wrapper resolve_output resolved_name project_root manifest_path demo_script command_runner
    local quoted_demo_script command_to_run display_command
    local dry_run=0
    local args=() extra_args=() project_args=()
    local route_venv_dir uses_uv_manager trust_required

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
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                args+=("$1")
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    base_demo_usage_error "Option '--project' requires an argument."
                    return $?
                }
                [[ -z "$explicit_project" ]] || {
                    base_demo_usage_error "Option '--project' may be specified only once."
                    return $?
                }
                explicit_project="$2"
                shift 2
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

    [[ -z "$explicit_project" || -z "$project" ]] || {
        base_demo_usage_error "The 'demo' command does not accept a positional project with --project."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    if [[ -n "$explicit_project" ]]; then
        project_args+=(--project "$explicit_project")
    elif [[ -n "$project" ]]; then
        project_args+=("$project")
    fi
    resolve_output="$("$wrapper" --project base base_projects demo-script "${project_args[@]}" "${args[@]}" --format command-protocol)" || return $?
    base_command_protocol_decode_one demo "$resolve_output" || {
        fatal_error "Unable to resolve demo script for project '${project:-current project}'."
    }
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    route_venv_dir="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    uses_uv_manager="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    trust_required="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_command_trust_required]}"
    base_project_set_history_context "$resolved_name" "$project_root" "$manifest_path"
    demo_script="${BASE_COMMAND_PROTOCOL_FIELDS[demo_script]}"
    command_runner="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"

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

    base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "$trust_required" || return $?
    base_project_activate_environment \
        "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "$route_venv_dir" "$uses_uv_manager" >/dev/null

    log_info "Running demo for project '$resolved_name': $display_command"
    if [[ -z "$command_runner" ]]; then
        (cd "$project_root" && "$demo_script" "${extra_args[@]}")
        return $?
    fi
    base_validate_command_runner "$command_runner"
    base_project_run_shell_command "$project_root" "$command_to_run" basectl-demo "${extra_args[@]}"
}
