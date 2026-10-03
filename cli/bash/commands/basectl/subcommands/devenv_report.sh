#!/usr/bin/env bash

[[ -n "${_base_devenv_report_subcommand_sourced:-}" ]] && return 0
_base_devenv_report_subcommand_sourced=1
readonly _base_devenv_report_subcommand_sourced

import_base_lib arg/lib_arg.sh

base_devenv_report_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl devenv-report [project] [options]

Options:
  --project <name>     Select a project explicitly, including one named help.
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <format>   Output format: text or json.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Report how a Base project manifest maps to Nix/devenv without generating files or requiring Nix.
EOF
}

base_devenv_report_usage_error() {
    base_devenv_report_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_devenv_report_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path
    local output_format="text" workspace_requested=0
    local args=() setup_args=() arg previous_arg=""
    local -a option_specs=(
        "debug|flag|-v"
        "project|value|--project"
        "workspace|value|--workspace"
        "format|value|--format"
    )
    local -a positionals=()
    local -A parsed_options=()

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                base_devenv_report_subcommand_usage
                return 0
                ;;
            help)
                if [[ "$previous_arg" != --project ]]; then
                    base_devenv_report_subcommand_usage
                    return 0
                fi
                ;;
        esac
        previous_arg="$arg"
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "$@"; then
        base_devenv_report_subcommand_usage >&2
        return 2
    fi

    if ((${#positionals[@]} > 1)); then
        base_devenv_report_usage_error "The 'devenv-report' command accepts exactly one project name."
        return $?
    fi
    if ((${#positionals[@]} == 1)); then
        project="${positionals[0]}"
    fi
    if [[ -n "${parsed_options[project]+set}" ]]; then
        [[ -z "$project" ]] || {
            base_devenv_report_usage_error "The 'devenv-report' command accepts only one project selection."
            return $?
        }
        project="${parsed_options[project]}"
    fi
    if [[ "${parsed_options[debug]:-}" == "1" ]]; then
        args+=(--debug)
    fi
    if [[ -n "${parsed_options[workspace]+set}" ]]; then
        workspace_requested=1
        args+=(--workspace "${parsed_options[workspace]}")
    fi
    if [[ -n "${parsed_options[format]+set}" ]]; then
        output_format="${parsed_options[format]}"
    fi

    [[ "$output_format" == "text" || "$output_format" == "json" ]] || {
        base_devenv_report_usage_error "Unsupported devenv-report format '$output_format'. Expected text or json."
        return $?
    }
    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_devenv_report_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    if [[ -n "$project" ]]; then
        resolve_output="$("$wrapper" --project base base_projects resolve "$project" "${args[@]}" --format command-protocol)" || return $?
        base_command_protocol_decode_one project-route "$resolve_output" || {
            base_std_fatal_error "Unable to resolve project for devenv-report."
        }
    else
        resolve_output="$("$wrapper" --project base base_projects current --format command-protocol)" || return $?
        base_command_protocol_decode_one project-reference "$resolve_output" || {
            base_std_fatal_error "Unable to resolve project for devenv-report."
        }
    fi
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        base_std_fatal_error "Unable to resolve project for devenv-report."
    }

    setup_args=(--manifest "$manifest_path" --action devenv-report --format "$output_format" "$resolved_name")
    "$wrapper" --project base base_setup "${setup_args[@]}"
}
