[[ -n "${_base_clean_subcommand_sourced:-}" ]] && return
_base_clean_subcommand_sourced=1
readonly _base_clean_subcommand_sourced

base_clean_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl clean --older-than <age> [options]

Options:
  --older-than <age>  Remove runtime artifacts older than an age such as 30d.
  --dry-run           Print what would be removed without deleting anything.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Remove old Base CLI runtime logs, temp files, and cache entries.
EOF
}

base_clean_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local has_older_than=0
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
            --older-than|--dry-run)
                args+=("$1")
                if [[ "$1" == "--older-than" ]]; then
                    has_older_than=1
                    [[ -n "${2:-}" ]] || {
                        base_clean_subcommand_usage >&2
                        printf 'ERROR: Option '\''--older-than'\'' requires an argument.\n' >&2
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
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    if (( ! has_older_than )); then
        base_clean_subcommand_usage >&2
        printf 'ERROR: Option '\''--older-than'\'' is required.\n' >&2
        return 2
    fi

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    "$wrapper" --project base base_clean "${args[@]}"
}
