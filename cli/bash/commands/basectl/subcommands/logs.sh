# shellcheck shell=bash
[[ -n "${_base_logs_subcommand_sourced:-}" ]] && return
_base_logs_subcommand_sourced=1
readonly _base_logs_subcommand_sourced

base_logs_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl logs [options]

Options:
  --command <name>  Filter by basectl command or Python CLI name.
  --limit <count>   Number of recent log entries to list. Defaults to 10.
  --path            Print the most recent matching log path only.
  --tail            Tail and follow the most recent matching log.
  --open            Open the most recent matching log in PAGER or EDITOR.
  --lines <count>   Line count to show before following with --tail. Defaults to 40.
  -v                Enable DEBUG logging for this subcommand.
  -h, --help        Show this help text.

Surface recent Base CLI runtime logs from the Base cache root.
EOF
}

base_logs_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_logs_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --command|--limit|--lines)
                [[ -n "${2:-}" ]] || {
                    base_logs_subcommand_usage >&2
                    print_error "Option '$1' requires an argument."
                    return 2
                }
                args+=("$1" "$2")
                shift 2
                ;;
            --command=*|--limit=*|--lines=*|--path|--tail|--open)
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
    "$wrapper" --project base base_logs "${args[@]}"
}
