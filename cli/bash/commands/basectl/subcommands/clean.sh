# shellcheck shell=bash
[[ -n "${_base_clean_subcommand_sourced:-}" ]] && return 0
_base_clean_subcommand_sourced=1
readonly _base_clean_subcommand_sourced

import_base_lib arg/lib_arg.sh

base_clean_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl clean [--older-than <age>] [--keep-last <count>] [options]

Options:
  --older-than <age>  Select runtime artifacts older than <age>.
                      Accepts integer ages with suffix d, h, m, or s.
                      Examples: 30d, 12h, 45m, 60s.
  --keep-last <count> Keep the newest completed run bundles per owner namespace.
  --dry-run           Explicitly preview cleanup without deleting anything.
  --yes               Delete matched artifacts after reviewing the preview.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Preview cleanup of old Base CLI runtime logs, temp files, and cache entries.
Deletion requires --yes, and at least one cleanup criterion is required.
EOF
}

base_clean_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local has_older_than=0
    local has_keep_last=0
    local args=() parser_args=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "debug|flag|-v"
        "older_than|value|--older-than"
        "keep_last|value|--keep-last"
    )
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a positionals=()
    local -A parsed_options=()

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_clean_subcommand_usage
                return 0
                ;;
            -v)
                parser_args+=("$1")
                args+=(--debug)
                shift
                ;;
            --older-than|--keep-last|--dry-run|--yes)
                args+=("$1")
                if [[ "$1" == "--older-than" || "$1" == "--keep-last" ]]; then
                    if [[ "$1" == "--older-than" ]]; then
                        has_older_than=1
                    else
                        has_keep_last=1
                    fi
                    [[ -n "${2:-}" ]] || {
                        base_clean_subcommand_usage >&2
                        base_std_print_error "Option '$1' requires an argument."
                        return 2
                    }
                    parser_args+=("$1=$2")
                    args+=("$2")
                    shift 2
                else
                    shift
                fi
                ;;
            --older-than=*)
                has_older_than=1
                parser_args+=("$1")
                args+=("$1")
                shift
                ;;
            --keep-last=*)
                has_keep_last=1
                parser_args+=("$1")
                args+=("$1")
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_clean_subcommand_usage >&2
        base_std_print_error "Could not parse clean arguments."
        return 2
    fi

    has_older_than="${parsed_options[older_than]:-0}"
    has_keep_last="${parsed_options[keep_last]:-0}"

    if (( ! has_older_than && ! has_keep_last )); then
        base_clean_subcommand_usage >&2
        base_std_print_error "One of '--older-than' or '--keep-last' is required."
        return 2
    fi

    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    "$wrapper" --project base base_clean "${args[@]}"
}
