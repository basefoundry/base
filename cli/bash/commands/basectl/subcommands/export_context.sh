#!/usr/bin/env bash

[[ -n "${_base_export_context_subcommand_sourced:-}" ]] && return 0
_base_export_context_subcommand_sourced=1
readonly _base_export_context_subcommand_sourced

import_base_lib arg/lib_arg.sh

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

base_export_context_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl export-context [project] [options]

Options:
  --project <name>          Select a project explicitly, including one named help.
  --workspace <path>       Workspace directory to scan for a named project.
  --format <markdown|zip>  Export format. Defaults to markdown.
  --output <path>          Write the export bundle to this path.
  --print                  Print the Markdown export bundle to stdout.
  --list-files             Print the files in export order without writing a bundle.
  -v                       Enable DEBUG logging for this subcommand.
  -h, --help               Show this help text.

Export a Base-managed project's .ai-context directory for manual upload or
copy/paste into AI tools.
EOF
}

base_export_context_usage_error() {
    base_export_context_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_export_context_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path
    local output_format="markdown" output_path="" print_bundle=0 list_files=0 workspace_requested=0
    local resolve_args=() exporter_args=()
    local arg previous_arg=""
    # shellcheck disable=SC2034 # Passed by name to cli_parse_options.
    local -a option_specs=(
        "debug|flag|-v"
        "project|value|--project"
        "workspace|value|--workspace"
        "format|value|--format"
        "output|value|--output"
        "print|flag|--print"
        "list_files|flag|--list-files"
    )
    local -a positionals=()
    local -A parsed_options=()

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                base_export_context_subcommand_usage
                return 0
                ;;
            help)
                if [[ "$previous_arg" != --project ]]; then
                    base_export_context_subcommand_usage
                    return 0
                fi
                ;;
        esac
        previous_arg="$arg"
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "$@"; then
        base_export_context_subcommand_usage >&2
        return 2
    fi

    if ((${#positionals[@]} > 1)); then
        base_export_context_usage_error "The 'export-context' command accepts exactly one project name."
        return $?
    fi
    if ((${#positionals[@]} == 1)); then
        project="${positionals[0]}"
    fi
    if [[ -n "${parsed_options[project]+set}" ]]; then
        [[ -z "$project" ]] || {
            base_export_context_usage_error "The 'export-context' command accepts only one project selection."
            return $?
        }
        project="${parsed_options[project]}"
    fi
    if [[ "${parsed_options[debug]:-}" == "1" ]]; then
        exporter_args+=(--debug)
    fi
    if [[ -n "${parsed_options[workspace]+set}" ]]; then
        workspace_requested=1
        resolve_args+=(--workspace "${parsed_options[workspace]}")
    fi
    if [[ -n "${parsed_options[format]+set}" ]]; then
        output_format="${parsed_options[format]}"
    fi
    if [[ -n "${parsed_options[output]+set}" ]]; then
        output_path="${parsed_options[output]}"
    fi
    print_bundle="${parsed_options[print]:-0}"
    list_files="${parsed_options[list_files]:-0}"

    case "$output_format" in
        markdown|zip) ;;
        *)
            base_export_context_usage_error "Unsupported export-context format '$output_format'. Expected markdown or zip."
            return $?
            ;;
    esac
    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_export_context_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }
    [[ "$print_bundle" != "1" || "$output_format" == "markdown" ]] || {
        base_export_context_usage_error "Option '--print' only supports markdown exports."
        return $?
    }
    [[ "$print_bundle" != "1" || -z "$output_path" ]] || {
        base_export_context_usage_error "Options '--print' and '--output' cannot be combined."
        return $?
    }
    [[ "$list_files" != "1" || ( "$print_bundle" != "1" && -z "$output_path" ) ]] || {
        base_export_context_usage_error "Option '--list-files' cannot be combined with '--print' or '--output'."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    if [[ -n "$project" ]]; then
        resolve_output="$("$wrapper" --project base base_projects resolve "$project" "${resolve_args[@]}" --format command-protocol)" || return $?
        base_command_protocol_decode_one project-route "$resolve_output" || {
            base_std_fatal_error "Unable to resolve project for export-context."
        }
    else
        resolve_output="$("$wrapper" --project base base_projects current --format command-protocol)" || return $?
        base_command_protocol_decode_one project-reference "$resolve_output" || {
            base_std_fatal_error "Unable to resolve project for export-context."
        }
    fi
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        base_std_fatal_error "Unable to resolve project for export-context."
    }
    base_project_set_history_context "$resolved_name" "$project_root" "$manifest_path"

    exporter_args+=(
        --project-name "$resolved_name"
        --project-root "$project_root"
        --format "$output_format"
    )
    [[ -z "$output_path" ]] || exporter_args+=(--output "$output_path")
    [[ "$print_bundle" != "1" ]] || exporter_args+=(--print)
    [[ "$list_files" != "1" ]] || exporter_args+=(--list-files)

    "$wrapper" --project base base_export_context "${exporter_args[@]}"
}
