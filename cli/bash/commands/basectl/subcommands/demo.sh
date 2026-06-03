#!/usr/bin/env bash

[[ -n "${_base_demo_subcommand_sourced:-}" ]] && return
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
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_demo_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path demo_script venv_dir
    local dry_run=0 workspace_requested=0
    local args=() extra_args=() project_args=()

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
    IFS=$'\t' read -r resolved_name project_root manifest_path demo_script <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$demo_script" ]] || {
        fatal_error "Unable to resolve demo script for project '${project:-current project}'."
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

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run demo for project %q in %q: %q%s\n' \
            "$resolved_name" "$project_root" "$demo_script" "$(base_format_extra_args "${extra_args[@]}")"
        return 0
    fi

    log_info "Running demo for project '$resolved_name': $demo_script$(base_format_extra_args "${extra_args[@]}")"
    (cd "$project_root" && "$demo_script" "${extra_args[@]}")
}
