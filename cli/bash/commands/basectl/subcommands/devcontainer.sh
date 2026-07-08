#!/usr/bin/env bash

[[ -n "${_base_devcontainer_subcommand_sourced:-}" ]] && return 0
_base_devcontainer_subcommand_sourced=1
readonly _base_devcontainer_subcommand_sourced

base_devcontainer_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl devcontainer [project] [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <format>   Output format: text or json.
  --write             Write .devcontainer/devcontainer.json. Refuses to replace an existing file.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Preview or write a Dev Containers configuration derived from a Base project manifest.
The default mode is a dry-run preview; no files are written unless --write is present.
EOF
}

base_devcontainer_usage_error() {
    base_devcontainer_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_devcontainer_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path
    local output_format="text" workspace_requested=0 write=0
    local args=() setup_args=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_devcontainer_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_devcontainer_usage_error "Option '--workspace' requires an argument."
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
                    base_devcontainer_usage_error "Option '--format' requires an argument."
                    return $?
                }
                output_format="$2"
                shift 2
                ;;
            --format=*)
                output_format="${1#--format=}"
                shift
                ;;
            --write)
                write=1
                shift
                ;;
            -*)
                base_devcontainer_usage_error "Unknown devcontainer option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project" ]]; then
                    base_devcontainer_usage_error "The 'devcontainer' command accepts exactly one project name."
                    return $?
                fi
                project="$1"
                shift
                ;;
        esac
    done

    [[ "$output_format" == "text" || "$output_format" == "json" ]] || {
        base_devcontainer_usage_error "Unsupported devcontainer format '$output_format'. Expected text or json."
        return $?
    }
    [[ -n "$project" || "$workspace_requested" != "1" ]] || {
        base_devcontainer_usage_error "Option '--workspace' requires an explicit project name."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    if [[ -n "$project" ]]; then
        resolve_output="$("$wrapper" --project base base_projects resolve "$project" "${args[@]}")" || return $?
    else
        resolve_output="$("$wrapper" --project base base_projects current)" || return $?
    fi
    IFS=$'\t' read -r resolved_name project_root manifest_path _ <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        fatal_error "Unable to resolve project for devcontainer export."
    }

    setup_args=(--manifest "$manifest_path" --action devcontainer --format "$output_format")
    [[ "$write" != "1" ]] || setup_args+=(--write)
    setup_args+=("$resolved_name")

    "$wrapper" --project base base_setup "${setup_args[@]}"
}
