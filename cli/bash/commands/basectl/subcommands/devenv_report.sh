#!/usr/bin/env bash

[[ -n "${_base_devenv_report_subcommand_sourced:-}" ]] && return 0
_base_devenv_report_subcommand_sourced=1
readonly _base_devenv_report_subcommand_sourced

base_devenv_report_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl devenv-report [project] [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <format>   Output format: text or json.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Report how a Base project manifest maps to Nix/devenv without generating files or requiring Nix.
EOF
}

base_devenv_report_usage_error() {
    base_devenv_report_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_devenv_report_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path
    local output_format="text" workspace_requested=0
    local args=() setup_args=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_devenv_report_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_devenv_report_usage_error "Option '--workspace' requires an argument."
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
            --format)
                [[ -n "${2:-}" ]] || {
                    base_devenv_report_usage_error "Option '--format' requires an argument."
                    return $?
                }
                output_format="$2"
                shift 2
                ;;
            --format=*)
                output_format="${1#--format=}"
                shift
                ;;
            -*)
                base_devenv_report_usage_error "Unknown devenv-report option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project" ]]; then
                    base_devenv_report_usage_error "The 'devenv-report' command accepts exactly one project name."
                    return $?
                fi
                project="$1"
                shift
                ;;
        esac
    done

    [[ "$output_format" == "text" || "$output_format" == "json" ]] || {
        base_devenv_report_usage_error "Unsupported devenv-report format '$output_format'. Expected text or json."
        return $?
    }
    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_devenv_report_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    if [[ -n "$project" ]]; then
        resolve_output="$("$wrapper" --project base base_projects resolve "$project" "${args[@]}" --format command-protocol)" || return $?
        base_command_protocol_decode_one project-route "$resolve_output" || {
            fatal_error "Unable to resolve project for devenv-report."
        }
    else
        resolve_output="$("$wrapper" --project base base_projects current --format command-protocol)" || return $?
        base_command_protocol_decode_one project-reference "$resolve_output" || {
            fatal_error "Unable to resolve project for devenv-report."
        }
    fi
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        fatal_error "Unable to resolve project for devenv-report."
    }

    setup_args=(--manifest "$manifest_path" --action devenv-report --format "$output_format" "$resolved_name")
    "$wrapper" --project base base_setup "${setup_args[@]}"
}
