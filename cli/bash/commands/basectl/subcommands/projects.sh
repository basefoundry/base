# shellcheck shell=bash
[[ -n "${_base_projects_subcommand_sourced:-}" ]] && return
_base_projects_subcommand_sourced=1
readonly _base_projects_subcommand_sourced

base_projects_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl projects list [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <format>   Output format for list: text or json.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

List Base-managed projects discovered through base_manifest.yaml files.
EOF
}

base_projects_subcommand_main() {
    local project_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()

    case "$project_command" in
        ""|-h|--help)
            base_projects_subcommand_usage
            return 0
            ;;
        list)
            shift
            ;;
        *)
            base_projects_subcommand_usage >&2
            fatal_error "Unknown projects command '$project_command'."
            ;;
    esac

    while (($# > 0)); do
        case "$1" in
            -v)
                args+=(--debug)
                shift
                ;;
            -h|--help)
                base_projects_subcommand_usage
                return 0
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    "$wrapper" --project base base_projects list "${args[@]}"
}
