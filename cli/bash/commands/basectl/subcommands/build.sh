#!/usr/bin/env bash

[[ -n "${_base_build_subcommand_sourced:-}" ]] && return 0
_base_build_subcommand_sourced=1
readonly _base_build_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

base_build_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl build <project> [target...] [options] [-- extra args...]
  basectl build <project> --list [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --dry-run           Print resolved build commands without running them.
  --list              List build targets for a project.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared build targets from their configured working directories.
When no target is provided, Base runs build.default from the project manifest.
Use -- to pass additional arguments to each delegated build command.
EOF
}

base_build_usage_error() {
    base_build_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_build_list_targets() {
    local project="$1"
    shift
    local args=("$@")
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local list_output line resolved_name project_root manifest_path target_name working_dir build_command description command_runner
    local display_text
    local printed_header=0
    local target_fields=()

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    list_output="$("$wrapper" --project base base_projects build-target-list "$project" "${args[@]}")" || return $?
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        IFS=$'\t' read -r -a target_fields <<<"$line"
        resolved_name="${target_fields[0]:-}"
        project_root="${target_fields[1]:-}"
        manifest_path="${target_fields[2]:-}"
        target_name="${target_fields[3]:-}"
        working_dir="${target_fields[4]:-}"
        build_command="${target_fields[5]:-}"
        description="${target_fields[6]:-}"
        command_runner="$(base_project_command_runner_from_field "${target_fields[7]:-}" || true)"
        [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$target_name" && -n "$working_dir" ]] || {
            fatal_error "Unable to parse build targets for project '$project'."
        }
        if ((printed_header == 0)); then
            printf "Build targets for project '%s'\n\n" "$resolved_name"
            printed_header=1
        fi
        command_runner="${command_runner:-}"
        if [[ -n "$description" ]]; then
            display_text="$description"
            if [[ -n "$command_runner" ]]; then
                display_text+=" [runner: $command_runner]"
            fi
        else
            display_text="$(base_display_command_with_runner "$command_runner" "$build_command")" || return $?
        fi
        printf '%-20s %-40s %s\n' "$target_name" "$working_dir" "$display_text"
    done <<<"$list_output"
}

base_build_subcommand_main() {
    local project="" wrapper resolve_output line resolved_name project_root manifest_path target_name working_dir build_command description command_runner
    local command_to_run display_command
    local dry_run=0 list_targets=0 workspace_requested=0 environment_prepared=0
    local args=() extra_args=() targets=()
    local target_fields=()

    while (($#)); do
        case "$1" in
            --)
                shift
                extra_args=("$@")
                break
                ;;
            -h|--help|help)
                base_build_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_build_usage_error "Option '--workspace' requires an argument."
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
                list_targets=1
                shift
                ;;
            -*)
                base_build_usage_error "Unknown build option '$1'."
                return $?
                ;;
            *)
                if [[ -z "$project" ]]; then
                    project="$1"
                else
                    targets+=("$1")
                fi
                shift
                ;;
        esac
    done

    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_build_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }
    [[ -n "$project" ]] || {
        base_build_usage_error "Project name is required."
        return $?
    }

    if [[ "$list_targets" == "1" ]]; then
        [[ ${#targets[@]} -eq 0 ]] || {
            base_build_usage_error "Option '--list' cannot be combined with build targets."
            return $?
        }
        [[ ${#extra_args[@]} -eq 0 ]] || {
            base_build_usage_error "Option '--list' cannot be combined with extra build arguments."
            return $?
        }
        base_build_list_targets "$project" "${args[@]}"
        return $?
    fi

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    resolve_output="$("$wrapper" --project base base_projects build-targets "$project" "${targets[@]}" "${args[@]}")" || return $?
    [[ -n "$resolve_output" ]] || fatal_error "Unable to resolve build targets for project '$project'."

    resolved_name=""
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        IFS=$'\t' read -r -a target_fields <<<"$line"
        resolved_name="${target_fields[0]:-}"
        project_root="${target_fields[1]:-}"
        manifest_path="${target_fields[2]:-}"
        target_name="${target_fields[3]:-}"
        working_dir="${target_fields[4]:-}"
        build_command="${target_fields[5]:-}"
        description="${target_fields[6]:-}"
        command_runner="$(base_project_command_runner_from_field "${target_fields[7]:-}" || true)"
        [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$target_name" && -n "$working_dir" && -n "$build_command" ]] || {
            fatal_error "Unable to parse build target '$target_name' for project '$project'."
        }

        command_runner="${command_runner:-}"
        command_to_run="$(base_command_with_runner "$command_runner" "$build_command" "${extra_args[@]}")" || return $?
        display_command="$(base_display_command_with_runner "$command_runner" "$build_command" "${extra_args[@]}")" || return $?

        if [[ "$dry_run" == "1" ]]; then
            printf '[DRY-RUN] Would build target %q for project %q in %q: %s\n' \
                "$target_name" "$resolved_name" "$working_dir" "$display_command"
            continue
        fi

        if ((environment_prepared == 0)); then
            base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "${target_fields[@]:7}" || return $?
            base_project_activate_environment "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "${target_fields[@]:7}" >/dev/null
            environment_prepared=1
        fi

        log_info "Building target '$target_name' for project '$resolved_name': $display_command"
        base_validate_command_runner "$command_runner"
        base_project_run_shell_command "$working_dir" "$command_to_run" basectl-build "${extra_args[@]}" || return $?
    done <<<"$resolve_output"
}
