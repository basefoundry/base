# shellcheck shell=bash
[[ -n "${_base_clean_subcommand_sourced:-}" ]] && return
_base_clean_subcommand_sourced=1
readonly _base_clean_subcommand_sourced

base_clean_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl clean [--older-than <age>] [--keep-last <count>] [options]

Options:
  --older-than <age>  Remove runtime artifacts older than <age>.
                      Accepts integer ages with suffix d, h, m, or s.
                      Examples: 30d, 12h, 45m, 60s.
  --keep-last <count> Keep the newest count log files per CLI log directory.
  --dry-run           Print what would be removed without deleting anything.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Remove old Base CLI runtime logs, temp files, and cache entries. At least one
cleanup criterion is required.
EOF
}

base_clean_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local has_older_than=0
    local has_keep_last=0
    local args=()

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_clean_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --older-than|--keep-last|--dry-run)
                args+=("$1")
                if [[ "$1" == "--older-than" || "$1" == "--keep-last" ]]; then
                    if [[ "$1" == "--older-than" ]]; then
                        has_older_than=1
                    else
                        has_keep_last=1
                    fi
                    [[ -n "${2:-}" ]] || {
                        base_clean_subcommand_usage >&2
                        print_error "Option '$1' requires an argument."
                        return 2
                    }
                    args+=("$2")
                    shift 2
                else
                    shift
                fi
                ;;
            --older-than=*)
                has_older_than=1
                args+=("$1")
                shift
                ;;
            --keep-last=*)
                has_keep_last=1
                args+=("$1")
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    if (( ! has_older_than && ! has_keep_last )); then
        base_clean_subcommand_usage >&2
        print_error "One of '--older-than' or '--keep-last' is required."
        return 2
    fi

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    "$wrapper" --project base base_clean "${args[@]}"
}
