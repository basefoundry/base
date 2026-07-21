# shellcheck shell=bash
[[ -n "${_base_logs_subcommand_sourced:-}" ]] && return 0
_base_logs_subcommand_sourced=1
readonly _base_logs_subcommand_sourced

base_logs_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl logs [options]
  basectl logs last-failed [--command <name[,name...]>] [--lines <count>] [--format text|csv|tsv|yaml|json]

Options:
  --command <name[,name...]>  Filter by one or more commands (comma-separated).
  --limit <count>   Number of recent log entries to list. Defaults to 10.
  --latest          Print the newest matching log path only. Use --tail or --open to consume it.
  --tail            Tail and follow the most recent matching log.
  --open            Open the most recent matching log in PAGER or EDITOR.
  --lines <count>   Line count to show before following with --tail. Defaults to 40.
  --format <format> Output format: text, csv, tsv, yaml, or json. Defaults to text.
  -v                Enable DEBUG logging for this subcommand.
  -h, --help        Show this help text.

Surface recent Base CLI runtime logs from the Base cache root.
"logs last-failed" prints the latest failed command metadata and a bounded redacted log tail.
EOF
}

base_logs_recent_usage() {
    cat <<'EOF'
Usage:
  basectl logs [options]
  basectl logs last-failed [options]

Purpose:
  List recent Base CLI runtime logs, or inspect the newest matching log.

Commands:
  last-failed  Print the latest failed command metadata and a bounded redacted log tail.

Options:
  --command <name[,name...]>  Filter by one or more commands (comma-separated).
  --limit <count>   Number of recent log entries to list. Defaults to 10.
  --latest          Print the newest matching log path only. Use --tail or --open to consume it.
  --tail            Tail and follow the most recent matching log.
  --open            Open the most recent matching log in PAGER or EDITOR.
  --lines <count>   Line count to show before following with --tail. Defaults to 40.
  -v                Enable DEBUG logging for this subcommand.
  -h, --help        Show this help text.
EOF
}

base_logs_last_failed_usage() {
    cat <<'EOF'
Usage:
  basectl logs last-failed [options]

Purpose:
  Print the latest failed command metadata and a bounded redacted log tail.

Options:
  --command <name[,name...]>  Select the latest failure for one or more commands.
  --lines <count>    Maximum log-tail lines to print. Defaults to 40.
  --format <format>  Output format: text, csv, tsv, yaml, or json. Defaults to text.
  -v                 Enable DEBUG logging for this subcommand.
  -h, --help         Show this help text.
EOF
}

base_logs_help_target() {
    local expect_value=0
    local argument
    local target=recent

    for argument in "$@"; do
        if ((expect_value)); then
            expect_value=0
            continue
        fi
        case "$argument" in
            --command|--limit|--lines|--format)
                expect_value=1
                ;;
            last-failed)
                target=last-failed
                ;;
            -* )
                ;;
            *)
                target="unknown:$argument"
                ;;
        esac
    done
    printf '%s\n' "$target"
}

base_logs_args_request_help() {
    local argument

    for argument in "$@"; do
        case "$argument" in
            -h|--help) return 0 ;;
        esac
    done
    return 1
}

base_logs_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()
    local help_target

    if base_logs_args_request_help "$@"; then
        help_target="$(base_logs_help_target "$@")"
        case "$help_target" in
            last-failed)
                base_logs_last_failed_usage
                return 0
                ;;
            recent)
                base_logs_recent_usage
                return 0
                ;;
            unknown:*)
                base_logs_subcommand_usage >&2
                print_error "Unknown logs command '${help_target#unknown:}'. Supported commands: last-failed."
                return 2
                ;;
        esac
    fi

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_logs_recent_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --command|--limit|--lines|--format)
                [[ -n "${2:-}" ]] || {
                    base_logs_subcommand_usage >&2
                    print_error "Option '$1' requires an argument."
                    return 2
                }
                args+=("$1" "$2")
                shift 2
                ;;
            --command=*|--limit=*|--lines=*|--format=*|--latest|--tail|--open)
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
    BASE_CLI_DISPLAY_COMMAND="basectl logs" "$wrapper" --project base base_logs "${args[@]}"
}
