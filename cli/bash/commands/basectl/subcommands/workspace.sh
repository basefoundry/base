# shellcheck shell=bash
[[ -n "${_base_workspace_subcommand_sourced:-}" ]] && return 0
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

base_workspace_onboarding_usage() {
    cat <<'EOF'
Usage:
  basectl workspace onboarding [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --manifest <path>   Local workspace manifest describing expected repositories.
                      Overrides workspace.manifest from ~/.base.d/config.yaml.
  --format <format>   Output format for the onboarding summary: text or json.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Summarize first-day workspace onboarding from a workspace manifest without cloning or setup.
EOF
}

base_workspace_init_usage() {
    cat <<'EOF'
Usage:
  basectl workspace init <workspace-source> [options]

Options:
  --owner <owner>     GitHub owner for short workspace repository names.
  --path <path>       Workspace configuration repository checkout path.
  --workspace <path>  Workspace directory for member repositories.
  --manifest <path>   Workspace manifest path or name. Defaults to workspace.yaml in the config repo.
  --include-optional  Include optional workspace manifest repositories when cloning.
  --dry-run           Show planned workspace initialization without writing.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Initialize a workspace from a workspace configuration repository.
EOF
}

base_workspace_configure_usage() {
    cat <<'EOF'
Usage:
  basectl workspace configure [options]

Options:
  --workspace <path>  Workspace directory to configure. Defaults to workspace.root, then BASE_HOME's parent.
  --manifest <path>   Local workspace manifest describing expected repositories.
                      Overrides workspace.manifest from ~/.base.d/config.yaml.
  --dry-run           Show planned workspace configuration without applying repo changes.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Apply or repair Base-managed GitHub repo configuration across workspace repositories.
EOF
}

base_workspace_subcommand_usage() {
    case "${1:-}" in
        status|check|doctor)
            base_workspace_report_usage
            ;;
        onboarding)
            base_workspace_onboarding_usage
            ;;
        clone)
            base_workspace_clone_usage
            ;;
        pull)
            base_workspace_pull_usage
            ;;
        init)
            base_workspace_init_usage
            ;;
        configure)
            base_workspace_configure_usage
            ;;
        *)
            cat <<'EOF'
Usage:
  basectl workspace <status|check|doctor|onboarding|clone|pull|init|configure> [options]

Commands:
  status     Show workspace status. Supports --format text|json.
  check      Run workspace checks. Supports --format text|json.
  doctor     Run workspace diagnostics. Supports --format text|json.
  onboarding Show first-day onboarding summary. Supports --format text|json.
  clone      Clone or validate expected repositories from a workspace manifest.
  pull       Fetch and validate a canonical workspace manifest source.
  init       Initialize a workspace from a workspace configuration repository.
  configure  Apply repo configure across workspace repositories.

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
        ""|-h|--help|help)
            base_workspace_subcommand_usage
            return 0
            ;;
        status|check|doctor|onboarding|clone|pull|init|configure)
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
