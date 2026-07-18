# shellcheck shell=bash
[[ -n "${_base_history_subcommand_sourced:-}" ]] && return 0
_base_history_subcommand_sourced=1
readonly _base_history_subcommand_sourced

base_history_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl history [options]

Options:
  --project <name>      Filter by Base project name.
  --command <name>      Filter by basectl command name.
  --status <ok|warn|error>
                        Filter by command status.
  --limit <count>       Number of recent history records to list. Defaults to 10.
  --format <text|markdown|json>
                        Output format. Defaults to text, or Markdown with --report.
  --report              Print a privacy-conscious Markdown or JSON activity report.
  --include-internal    Include delegated internal steps in the output.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

List recent Base command runs from the local command history index.
EOF
}

base_history_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_history_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --report)
                args+=("$1")
                shift
                ;;
            --include-internal)
                args+=("$1")
                shift
                ;;
            --project|--command|--status|--limit|--format)
                [[ -n "${2:-}" ]] || {
                    base_history_subcommand_usage >&2
                    print_error "Option '$1' requires an argument."
                    return 2
                }
                args+=("$1" "$2")
                shift 2
                ;;
            --project=*|--command=*|--status=*|--limit=*|--format=*)
                args+=("$1")
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_CLI_DISPLAY_COMMAND="basectl history" "$wrapper" --project base base_history "${args[@]}"
}
