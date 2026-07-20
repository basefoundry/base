#!/usr/bin/env bash

[[ -n "${_base_run_subcommand_sourced:-}" ]] && return 0
_base_run_subcommand_sourced=1
readonly _base_run_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

base_run_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl run [project] <command> [options] [-- extra args...]
  basectl run [project] --list [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --project <name>    Select a project explicitly; required for a current command named like a project.
  --dry-run           Print the resolved command without running it.
  --list              List runnable commands for a project. Defaults to the nearest project.
  --format <format>   List output format: text, csv, tsv, yaml, or json. Defaults to text.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared command from its project root. The first positional
value remains a project when it names a registered project; otherwise Base uses
the nearest project and treats that value as the command name.
Use -- to pass additional arguments to the declared command.
EOF
}

base_run_usage_error() {
    base_run_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_run_print_command_record() {
    local display_text
    local resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    local command_name="${BASE_COMMAND_PROTOCOL_FIELDS[command_name]}"
    local command_text="${BASE_COMMAND_PROTOCOL_FIELDS[command]}"
    local command_runner="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"

    if [[ ! -t 1 ]]; then
        printf '%s\t%s\t%s\t%s\n' "$resolved_name" "$command_name" "$command_text" "$command_runner"
        return 0
    fi
    if ((printed_header == 0)); then
        printf "Commands for project '%s'\n\n" "$resolved_name"
        printed_header=1
    fi
    display_text="$(base_display_command_with_runner "$command_runner" "$command_text")" || return $?
    printf '%-20s %s\n' "$command_name" "$display_text"
}

base_run_list_commands() {
    local project="$1"
    local explicit_project="$2"
    local output_format="$3"
    shift 3
    local args=("$@")
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local command_args=(run-commands)
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
    base_command_protocol_each named-command "$list_output" base_run_print_command_record
}

base_run_subcommand_main() {
    local project="" explicit_project="" command_name="" wrapper resolve_output resolved_name project_root manifest_path run_command command_runner
    local command_to_run display_command
    local dry_run=0 list_commands=0
    local output_format="text"
    local args=() extra_args=() operands=()
    local route_venv_dir uses_uv_manager trust_required

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
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                args+=("$1")
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    base_run_usage_error "Option '--project' requires an argument."
                    return $?
                }
                [[ -z "$explicit_project" ]] || {
                    base_run_usage_error "Option '--project' may be specified only once."
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
                list_commands=1
                shift
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_run_usage_error "Option '--format' requires an argument."
                    return $?
                }
                output_format="$2"
                shift 2
                ;;
            -*)
                base_run_usage_error "Unknown run option '$1'."
                return $?
                ;;
            *)
                operands+=("$1")
                shift
                ;;
        esac
    done

    [[ "$output_format" == "text" || "$output_format" == "csv" || "$output_format" == "tsv" || "$output_format" == "yaml" || "$output_format" == "json" ]] || {
        base_run_usage_error "Unsupported run format '$output_format'. Expected text, csv, tsv, yaml, or json."
        return $?
    }
    if [[ "$list_commands" == "1" ]]; then
        [[ "$dry_run" == "0" ]] || {
            base_run_usage_error "Option '--list' cannot be combined with --dry-run."
            return $?
        }
        if [[ -n "$explicit_project" ]]; then
            [[ ${#operands[@]} -eq 0 ]] || {
                base_run_usage_error "Option '--list' does not accept a positional project with --project."
                return $?
            }
        else
            [[ ${#operands[@]} -le 1 ]] || {
                base_run_usage_error "Option '--list' accepts at most one positional project."
                return $?
            }
            project="${operands[0]:-}"
        fi
        [[ ${#extra_args[@]} -eq 0 ]] || {
            base_run_usage_error "Option '--list' cannot be combined with extra command arguments."
            return $?
        }
        base_run_list_commands "$project" "$explicit_project" "$output_format" "${args[@]}"
        return $?
    fi

    [[ "$output_format" == "text" ]] || {
        base_run_usage_error "Option '--format' requires --list."
        return $?
    }
    if [[ -n "$explicit_project" ]]; then
        [[ ${#operands[@]} -eq 1 ]] || {
            base_run_usage_error "The 'run' command accepts exactly one command name with --project."
            return $?
        }
        command_name="${operands[0]}"
    else
        [[ ${#operands[@]} -ge 1 && ${#operands[@]} -le 2 ]] || {
            base_run_usage_error "The 'run' command requires a command name and accepts an optional positional project."
            return $?
        }
    fi

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    local command_args=(run-command)
    if [[ -n "$explicit_project" ]]; then
        command_args+=(--project "$explicit_project" "$command_name")
    else
        command_args+=("${operands[@]}")
        command_name="${operands[${#operands[@]} - 1]}"
    fi
    resolve_output="$("$wrapper" --project base base_projects "${command_args[@]}" "${args[@]}" --format command-protocol)" || return $?
    base_command_protocol_decode_one project-command "$resolve_output" || {
        fatal_error "Unable to resolve command '$command_name' for project '${explicit_project:-current project}'."
    }
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    route_venv_dir="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    uses_uv_manager="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    trust_required="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_command_trust_required]}"
    base_project_set_history_context "$resolved_name" "$project_root" "$manifest_path"
    run_command="${BASE_COMMAND_PROTOCOL_FIELDS[command]}"
    command_runner="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$run_command" ]] || {
        fatal_error "Unable to resolve command '$command_name' for project '${explicit_project:-current project}'."
    }

    command_runner="${command_runner:-}"
    command_to_run="$(base_command_with_runner "$command_runner" "$run_command" "${extra_args[@]}")" || return $?
    display_command="$(base_display_command_with_runner "$command_runner" "$run_command" "${extra_args[@]}")" || return $?

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run command %q for project %q in %q: %s\n' \
            "$command_name" "$resolved_name" "$project_root" "$display_command"
        return 0
    fi

    base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "$trust_required" || return $?
    base_project_activate_environment \
        "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "$route_venv_dir" "$uses_uv_manager" >/dev/null

    log_info "Running command '$command_name' for project '$resolved_name': $display_command"
    base_validate_command_runner "$command_runner"
    base_project_run_shell_command "$project_root" "$command_to_run" basectl-run "${extra_args[@]}"
}
