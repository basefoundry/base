# shellcheck shell=bash
[[ -n "${_base_release_subcommand_sourced:-}" ]] && return 0
_base_release_subcommand_sourced=1
readonly _base_release_subcommand_sourced

base_release_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl release check --version <version> [options]
  basectl release plan --version <version> [options]
  basectl release notes --version <version> [options]
  basectl release publish --version <version> [options]

Subcommands:
  check    Verify release readiness for version, changelog, Git, and GitHub.
  plan     Show the release plan without creating tags or releases.
  notes    Print the changelog notes for the target version.
  publish  Tag the release and create the GitHub Release.

Options:
  --version <version>  Release version to inspect.
  --manifest <path>   Use a specific base_manifest.yaml path.
  --format <text|json>
                      Select human text or stable inspection JSON for check.
  --dry-run           Print publish actions without creating tags or releases.
  --yes               Publish without an interactive confirmation prompt.
  -h, --help          Show this help text.

Inspect release readiness, plan, changelog notes, and guarded GitHub publishing.
Typical order: check -> plan -> notes -> publish.
Homebrew tap updates remain a manual handoff.
EOF
}

base_release_leaf_usage() {
    local release_command="$1"
    local purpose=""

    case "$release_command" in
        check)
            purpose="Verify release readiness for the version, changelog, Git, and GitHub."
            ;;
        plan)
            purpose="Show the release plan without creating tags or releases."
            ;;
        notes)
            purpose="Print changelog notes for the target version."
            ;;
        publish)
            purpose="Tag the release and create the GitHub Release after readiness passes."
            ;;
        *)
            return 1
            ;;
    esac

    if [[ "$release_command" == "publish" ]]; then
        cat <<EOF
Usage:
  basectl release publish --version <version> [--manifest <path>] [--dry-run] [--yes]

Purpose:
  $purpose

Options:
  --version <version>  Release version to publish.
  --manifest <path>    Use a specific base_manifest.yaml path.
  --dry-run            Print publish actions without creating tags or releases.
  --yes                Publish without an interactive confirmation prompt.
  -h, --help           Show this help text.
EOF
        return 0
    fi

    if [[ "$release_command" == "check" ]]; then
        cat <<EOF
Usage:
  basectl release check --version <version> [--manifest <path>] [--format <text|json>]

Purpose:
  $purpose

Options:
  --version <version>  Release version to inspect.
  --manifest <path>    Use a specific base_manifest.yaml path.
  --format <text|json> Select human text or stable inspection JSON.
  -h, --help           Show this help text.
EOF
        return 0
    fi

    cat <<EOF
Usage:
  basectl release $release_command --version <version> [--manifest <path>]

Purpose:
  $purpose

Options:
  --version <version>  Release version to inspect.
  --manifest <path>    Use a specific base_manifest.yaml path.
  -h, --help           Show this help text.
EOF
}

base_release_args_request_help() {
    local arg

    for arg in "$@"; do
        case "$arg" in
            -h|--help) return 0 ;;
        esac
    done
    return 1
}

base_release_usage_error() {
    base_release_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_release_subcommand_main() {
    local release_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"

    case "$release_command" in
        ""|-h|--help|help)
            base_release_subcommand_usage
            return 0
            ;;
        check|plan|notes|publish)
            ;;
        *)
            base_release_usage_error "Unknown release command '$release_command'."
            return $?
            ;;
    esac

    if base_release_args_request_help "${@:2}"; then
        base_release_leaf_usage "$release_command"
        return $?
    fi

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_CLI_DISPLAY_COMMAND="basectl release" "$wrapper" --project base base_release "$@"
}
