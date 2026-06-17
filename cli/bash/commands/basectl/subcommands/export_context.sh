#!/usr/bin/env bash

[[ -n "${_base_export_context_subcommand_sourced:-}" ]] && return
_base_export_context_subcommand_sourced=1
readonly _base_export_context_subcommand_sourced

base_export_context_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl export-context [project] [options]

Options:
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
    print_error "$*"
    return 2
}

base_export_context_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path
    local output_format="markdown" output_path="" print_bundle=0 list_files=0 workspace_requested=0
    local resolve_args=() exporter_args=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_export_context_subcommand_usage
                return 0
                ;;
            -v)
                exporter_args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_export_context_usage_error "Option '--workspace' requires an argument."
                    return $?
                }
                workspace_requested=1
                resolve_args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                workspace_requested=1
                resolve_args+=("$1")
                shift
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_export_context_usage_error "Option '--format' requires an argument."
                    return $?
                }
                output_format="$2"
                shift 2
                ;;
            --format=*)
                output_format="${1#--format=}"
                shift
                ;;
            --output)
                [[ -n "${2:-}" ]] || {
                    base_export_context_usage_error "Option '--output' requires an argument."
                    return $?
                }
                output_path="$2"
                shift 2
                ;;
            --output=*)
                output_path="${1#--output=}"
                shift
                ;;
            --print)
                print_bundle=1
                shift
                ;;
            --list-files)
                list_files=1
                shift
                ;;
            -*)
                base_export_context_usage_error "Unknown export-context option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project" ]]; then
                    base_export_context_usage_error "The 'export-context' command accepts exactly one project name."
                    return $?
                fi
                project="$1"
                shift
                ;;
        esac
    done

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
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    if [[ -n "$project" ]]; then
        resolve_output="$("$wrapper" --project base base_projects resolve "$project" "${resolve_args[@]}")" || return $?
    else
        resolve_output="$("$wrapper" --project base base_projects current)" || return $?
    fi
    IFS=$'\t' read -r resolved_name project_root manifest_path <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        fatal_error "Unable to resolve project for export-context."
    }

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
