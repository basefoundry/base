# shellcheck shell=bash
[[ -n "${_base_workspace_subcommand_sourced:-}" ]] && return
_base_workspace_subcommand_sourced=1
readonly _base_workspace_subcommand_sourced

base_workspace_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl workspace <status|check|doctor|clone> [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --manifest <path>   Local workspace manifest describing expected repositories.
  --format <format>   Output format for the workspace command: text or json.
  --include-optional  Include optional workspace manifest repositories when cloning.
  --dry-run           Show planned workspace clone work without cloning repositories.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Show status, check, doctor, or clone output for repositories in the workspace.
EOF
}

base_workspace_usage_error() {
    base_workspace_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_workspace_subcommand_main() {
    local workspace_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()

    case "$workspace_command" in
        ""|-h|--help)
            base_workspace_subcommand_usage
            return 0
            ;;
        status|check|doctor|clone)
            shift
            ;;
        *)
            base_workspace_usage_error "Unknown workspace command '$workspace_command'."
            return $?
            ;;
    esac

    while (($# > 0)); do
        case "$1" in
            -v)
                args+=(--debug)
                shift
                ;;
            -h|--help)
                base_workspace_subcommand_usage
                return 0
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    "$wrapper" --project base base_projects "$workspace_command" "${args[@]}"
}
