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
  --project <name>              Select a project explicitly, including one named help.
  --workspace <path>            Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <text|csv|tsv|yaml|json>
                                Output format for status. Defaults to text.
  --manifest-sha256 <sha256>    Expected manifest SHA-256 for allow.
  --test-requirements-sha256 <sha256>
                                Expected SHA-256 for the declared test-requirements file.
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
  --project <name>       Select a project explicitly, including one named help.
  --workspace <path>    Workspace directory to scan.
  --format <text|csv|tsv|yaml|json>
                        Output format. Defaults to text.
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
  --project <name>            Select a project explicitly, including one named help.
  --workspace <path>          Workspace directory to scan.
  --manifest-sha256 <sha256>  Require the current manifest to match this digest.
  --test-requirements-sha256 <sha256>
                              Require the declared test-requirements file to match this digest.
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
  --project <name>      Select a project explicitly, including one named help.
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
    base_std_print_error "$*"
    return 2
}

base_trust_subcommand_main() {
    local trust_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=() project_name="" explicit_project=""

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
            --project)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_trust_usage_error "Option '--project' requires an argument."
                    return $?
                fi
                if [[ -n "$explicit_project" ]]; then
                    base_trust_usage_error "The 'trust' command accepts only one project selection."
                    return $?
                fi
                explicit_project="$1"
                shift
                ;;
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

    if [[ -n "$explicit_project" ]]; then
        if ((${#args[@]} > 1)); then
            base_trust_usage_error "The 'trust' command accepts only one project selection."
            return $?
        fi
        args+=("$explicit_project")
    fi

    if [[ "$trust_command" != status || ${#args[@]} -gt 1 ]]; then
        project_name="${args[1]:-}"
    fi
    if [[ -n "$project_name" && "$project_name" != -* ]]; then
        export BASE_CLI_HISTORY_PROJECT="$project_name"
    fi

    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_TRUST_ACTIVE_PROJECT="${BASE_PROJECT:-}" \
        BASE_TRUST_ACTIVE_PROJECT_MANIFEST="${BASE_PROJECT_MANIFEST:-}" \
        BASE_CLI_DISPLAY_COMMAND="basectl trust" \
        "$wrapper" --project base base_trust "${args[@]}"
}
