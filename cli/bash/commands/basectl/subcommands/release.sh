# shellcheck shell=bash
[[ -n "${_base_release_subcommand_sourced:-}" ]] && return
_base_release_subcommand_sourced=1
readonly _base_release_subcommand_sourced

base_release_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl release check --version <version> [options]
  basectl release plan --version <version> [options]
  basectl release notes --version <version> [options]

Options:
  --version <version>  Release version to inspect.
  --manifest <path>   Use a specific base_manifest.yaml path.
  -h, --help          Show this help text.

Inspect release readiness, plan, and changelog notes without creating tags,
publishing GitHub Releases, or editing Homebrew taps.
EOF
}

base_release_subcommand_main() {
    local release_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"

    case "$release_command" in
        ""|-h|--help|help)
            base_release_subcommand_usage
            return 0
            ;;
        check|plan|notes)
            ;;
        *)
            base_release_subcommand_usage >&2
            fatal_error "Unknown release command '$release_command'."
            ;;
    esac

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    "$wrapper" --project base base_release "$@"
}
