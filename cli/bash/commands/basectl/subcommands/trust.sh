# shellcheck shell=bash
[[ -n "${_base_trust_subcommand_sourced:-}" ]] && return 0
_base_trust_subcommand_sourced=1
readonly _base_trust_subcommand_sourced

base_trust_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl trust status [project] [options]
  basectl trust allow <project> [options]
  basectl trust revoke <project> [options]

Options:
  --workspace <path>            Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <text|json>          Output format for status. Defaults to text.
  --manifest-sha256 <sha256>    Expected manifest SHA-256 for allow.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Inspect trust for one project or all discovered projects, and manage local
approval for manifest-declared project commands.
EOF
}

base_trust_leaf_usage() {
    local trust_command="$1"

    case "$trust_command" in
        status)
            cat <<'EOF'
Usage:
  basectl trust status [project] [options]

Purpose:
  Show manifest command trust for one project, or for all discovered
  command-bearing projects when no project is supplied.

Options:
  --workspace <path>    Workspace directory to scan.
  --format <text|json>  Output format. Defaults to text.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.
EOF
            ;;
        allow)
            cat <<'EOF'
Usage:
  basectl trust allow <project> [options]

Purpose:
  Approve the current manifest command contract for one project on this
  machine.

Options:
  --workspace <path>          Workspace directory to scan.
  --manifest-sha256 <sha256>  Require the current manifest to match this digest.
  -v                          Enable DEBUG logging for this subcommand.
  -h, --help                  Show this help text.
EOF
            ;;
        revoke)
            cat <<'EOF'
Usage:
  basectl trust revoke <project> [options]

Purpose:
  Remove local manifest command approval for one project.

Options:
  --workspace <path>  Workspace directory to scan.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.
EOF
            ;;
        *)
            return 1
            ;;
    esac
}

base_trust_usage_error() {
    base_trust_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_trust_subcommand_main() {
    local trust_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()

    case "$trust_command" in
        ""|-h|--help|help)
            base_trust_subcommand_usage
            return 0
            ;;
        status|allow|revoke)
            args+=("$trust_command")
            shift
            ;;
        *)
            base_trust_usage_error "Unknown trust command '$trust_command'."
            return $?
            ;;
    esac

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_trust_leaf_usage "$trust_command"
                return $?
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_TRUST_ACTIVE_PROJECT="${BASE_PROJECT:-}" \
        BASE_TRUST_ACTIVE_PROJECT_MANIFEST="${BASE_PROJECT_MANIFEST:-}" \
        BASE_CLI_DISPLAY_COMMAND="basectl trust" \
        "$wrapper" --project base base_trust "${args[@]}"
}
