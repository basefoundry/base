# shellcheck shell=bash
[[ -n "${_base_docs_subcommand_sourced:-}" ]] && return 0
_base_docs_subcommand_sourced=1
readonly _base_docs_subcommand_sourced

import_base_lib arg/lib_arg.sh

BASE_DOCS_URL="https://github.com/basefoundry/base#readme"
readonly BASE_DOCS_URL

base_docs_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl docs [options]

Options:
  --show-url   Print the documentation URL without opening a browser.
  -h, --help   Show this help text.

Open the Base documentation home page on GitHub.
EOF
}

base_docs_usage_error() {
    base_docs_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_docs_platform_opener() {
    local opener opener_path

    for opener in open xdg-open wslview; do
        if base_std_command_path opener_path "$opener" && [[ -n "$opener_path" ]]; then
            printf '%s\n' "$opener"
            return 0
        fi
    done

    return 1
}

base_docs_open_url() {
    local opener

    if ! opener="$(base_docs_platform_opener)"; then
        base_std_print_error "No supported browser opener was found. Use 'basectl docs --show-url' to print the URL."
        return 1
    fi

    "$opener" "$BASE_DOCS_URL"
}

base_docs_subcommand_main() {
    local arg
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=("show_url|flag|--show-url") positionals=()
    local -A parsed_options=()

    for arg in "$@"; do
        case "$arg" in
            -h|--help|help)
                base_docs_subcommand_usage
                return 0
                ;;
            --show-url)
                ;;
            --|-*)
                base_docs_usage_error "Unknown docs option '$arg'."
                return $?
                ;;
            *)
                base_docs_usage_error "The 'docs' command does not accept positional arguments."
                return $?
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "$@"; then
        base_docs_usage_error "Could not parse docs arguments."
        return $?
    fi

    if [[ "${parsed_options[show_url]:-}" == "1" ]]; then
        printf '%s\n' "$BASE_DOCS_URL"
        return 0
    fi

    base_docs_open_url
}
