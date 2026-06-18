# shellcheck shell=bash
[[ -n "${_base_workspace_subcommand_sourced:-}" ]] && return
_base_workspace_subcommand_sourced=1
readonly _base_workspace_subcommand_sourced

base_workspace_report_usage() {
    cat <<'EOF'
Usage:
  basectl workspace <status|check|doctor> [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --manifest <path>   Local workspace manifest describing expected repositories.
                      Overrides workspace.manifest from ~/.base.d/config.yaml.
  --format <format>   Output format for the workspace command: text or json.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Show status, check, or doctor output for repositories in the workspace.
EOF
}

base_workspace_clone_usage() {
    cat <<'EOF'
Usage:
  basectl workspace clone [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --manifest <path>   Local workspace manifest describing expected repositories.
                      Overrides workspace.manifest from ~/.base.d/config.yaml.
  --include-optional  Include optional workspace manifest repositories when cloning.
  --dry-run           Show planned workspace clone work without writing.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Clone or validate expected repositories from a workspace manifest.
EOF
}

base_workspace_pull_usage() {
    cat <<'EOF'
Usage:
  basectl workspace pull [options]

Options:
  --source <url-or-path>
                      Canonical workspace manifest source for workspace pull.
                      Overrides workspace.manifest_source from ~/.base.d/config.yaml.
  --manifest <path>   Local workspace manifest describing expected repositories.
                      Overrides workspace.manifest from ~/.base.d/config.yaml.
  --dry-run           Show planned workspace pull work without writing.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Fetch and validate a canonical workspace manifest before updating the local manifest.
EOF
}

base_workspace_subcommand_usage() {
    case "${1:-}" in
        status|check|doctor)
            base_workspace_report_usage
            ;;
        clone)
            base_workspace_clone_usage
            ;;
        pull)
            base_workspace_pull_usage
            ;;
        *)
            cat <<'EOF'
Usage:
  basectl workspace <status|check|doctor|clone|pull> [options]

Commands:
  status   Show workspace status. Supports --format text|json.
  check    Run workspace checks. Supports --format text|json.
  doctor   Run workspace diagnostics. Supports --format text|json.
  clone    Clone or validate expected repositories from a workspace manifest.
  pull     Fetch and validate a canonical workspace manifest source.

Run `basectl workspace <command> --help` for command-specific options.
EOF
            ;;
    esac
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
        status|check|doctor|clone|pull)
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
                base_workspace_subcommand_usage "$workspace_command"
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
