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
  basectl build [project] [target...] [options] [-- extra args...]
  basectl build [project] --list [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --project <name>    Select a project explicitly; required for a current target named like a project.
  --dry-run           Print resolved build commands without running them.
  --list              List build targets for a project.
  --format <format>   List output format: text, csv, tsv, yaml, or json. Defaults to text.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared build targets from their configured working directories.
The first positional value remains a project when it names a registered project;
otherwise Base uses the nearest project and treats all values as target names.
When no target is provided, Base runs build.default from the project manifest.
Use -- to pass additional arguments to each delegated build command.
EOF
}

base_build_usage_error() {
    base_build_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_build_print_target_record() {
    local display_text
    local resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    local target_name="${BASE_COMMAND_PROTOCOL_FIELDS[target_name]}"
    local working_dir="${BASE_COMMAND_PROTOCOL_FIELDS[working_dir]}"
    local build_command="${BASE_COMMAND_PROTOCOL_FIELDS[command]}"
    local description="${BASE_COMMAND_PROTOCOL_FIELDS[description]}"
    local command_runner="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"

    if [[ ! -t 1 ]]; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
            "$resolved_name" "$target_name" "$working_dir" "$build_command" "$description" "$command_runner"
        return 0
    fi
    if ((printed_header == 0)); then
        printf "Build targets for project '%s'\n\n" "$resolved_name"
        printed_header=1
    fi
    if [[ -n "$description" ]]; then
        display_text="$description"
        if [[ -n "$command_runner" ]]; then
            display_text+=" [runner: $command_runner]"
        fi
    else
        display_text="$(base_display_command_with_runner "$command_runner" "$build_command")" || return $?
    fi
    printf '%-20s %-40s %s\n' "$target_name" "$working_dir" "$display_text"
}

base_build_run_target_record() {
    local resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    local project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    local manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    local route_venv_dir="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    local uses_uv_manager="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    local trust_required="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_command_trust_required]}"
    local target_name="${BASE_COMMAND_PROTOCOL_FIELDS[target_name]}"
    local working_dir="${BASE_COMMAND_PROTOCOL_FIELDS[working_dir]}"
    local build_command="${BASE_COMMAND_PROTOCOL_FIELDS[command]}"
    local command_runner="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"
    local command_to_run display_command

    base_project_set_history_context "$resolved_name" "$project_root" "$manifest_path"

    command_to_run="$(base_command_with_runner "$command_runner" "$build_command" "${extra_args[@]}")" || return $?
    display_command="$(base_display_command_with_runner "$command_runner" "$build_command" "${extra_args[@]}")" || return $?

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would build target %q for project %q in %q: %s\n' \
            "$target_name" "$resolved_name" "$working_dir" "$display_command"
        return 0
    fi

    if ((environment_prepared == 0)); then
        base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "$trust_required" || return $?
        base_project_activate_environment \
            "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "$route_venv_dir" "$uses_uv_manager" >/dev/null
        environment_prepared=1
    fi

    log_info "Building target '$target_name' for project '$resolved_name': $display_command"
    base_validate_command_runner "$command_runner"
    base_project_run_shell_command "$working_dir" "$command_to_run" basectl-build "${extra_args[@]}"
}

base_build_list_targets() {
    local project="$1"
    local explicit_project="$2"
    local output_format="$3"
    shift 3
    local args=("$@")
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local command_args=(build-target-list)
    local list_output
    local printed_header=0

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    if [[ -n "$explicit_project" ]]; then
        command_args+=(--project "$explicit_project")
    elif [[ -n "$project" ]]; then
        command_args+=("$project")
    fi

    if [[ "$output_format" != "text" ]]; then
        "$wrapper" --project base base_projects "${command_args[@]}" "${args[@]}" --dry-run --format "$output_format"
        return $?
    fi

    list_output="$("$wrapper" --project base base_projects "${command_args[@]}" "${args[@]}" --dry-run --format command-protocol)" || return $?
    base_command_protocol_each build-target "$list_output" base_build_print_target_record
}

base_build_subcommand_main() {
    local project="" explicit_project="" wrapper resolve_output
    local dry_run=0 list_targets=0 environment_prepared=0
    local output_format="text"
    local args=() extra_args=() targets=()

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
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                args+=("$1")
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    base_build_usage_error "Option '--project' requires an argument."
                    return $?
                }
                [[ -z "$explicit_project" ]] || {
                    base_build_usage_error "Option '--project' may be specified only once."
                    return $?
                }
                explicit_project="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            --list)
                list_targets=1
                shift
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_build_usage_error "Option '--format' requires an argument."
                    return $?
                }
                output_format="$2"
                shift 2
                ;;
            -*)
                base_build_usage_error "Unknown build option '$1'."
                return $?
                ;;
            *)
                targets+=("$1")
                shift
                ;;
        esac
    done

    [[ "$output_format" == "text" || "$output_format" == "csv" || "$output_format" == "tsv" || "$output_format" == "yaml" || "$output_format" == "json" ]] || {
        base_build_usage_error "Unsupported build format '$output_format'. Expected text, csv, tsv, yaml, or json."
        return $?
    }

    if [[ "$list_targets" == "1" ]]; then
        [[ "$dry_run" == "0" ]] || {
            base_build_usage_error "Option '--list' cannot be combined with --dry-run."
            return $?
        }
        if [[ -n "$explicit_project" ]]; then
            [[ ${#targets[@]} -eq 0 ]] || {
                base_build_usage_error "Option '--list' does not accept a positional project with --project."
                return $?
            }
        else
            [[ ${#targets[@]} -le 1 ]] || {
                base_build_usage_error "Option '--list' accepts at most one positional project."
                return $?
            }
            project="${targets[0]:-}"
        fi
        [[ ${#extra_args[@]} -eq 0 ]] || {
            base_build_usage_error "Option '--list' cannot be combined with extra build arguments."
            return $?
        }
        base_build_list_targets "$project" "$explicit_project" "$output_format" "${args[@]}"
        return $?
    fi

    [[ "$output_format" == "text" ]] || {
        base_build_usage_error "Option '--format' requires --list."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    local command_args=(build-targets)
    [[ -z "$explicit_project" ]] || command_args+=(--project "$explicit_project")
    command_args+=("${targets[@]}")
    resolve_output="$("$wrapper" --project base base_projects "${command_args[@]}" "${args[@]}" --format command-protocol)" || return $?
    [[ -n "$resolve_output" ]] || fatal_error "Unable to resolve build targets for project '${explicit_project:-current project}'."

    base_command_protocol_each build-target "$resolve_output" base_build_run_target_record
}
