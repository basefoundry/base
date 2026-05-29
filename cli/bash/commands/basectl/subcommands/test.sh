[[ -n "${_base_test_subcommand_sourced:-}" ]] && return
_base_test_subcommand_sourced=1
readonly _base_test_subcommand_sourced

base_test_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl test [project] [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to BASE_HOME's parent.
  --dry-run           Print the project test command without running it.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a Base-managed project's declared test command from its project root.
EOF
}

base_test_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_test_subcommand_usage
                return 0
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
    "$wrapper" --project base base_test "${args[@]}"
}
