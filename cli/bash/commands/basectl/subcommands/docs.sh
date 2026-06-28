# shellcheck shell=bash
[[ -n "${_base_docs_subcommand_sourced:-}" ]] && return 0
_base_docs_subcommand_sourced=1
readonly _base_docs_subcommand_sourced

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
    print_error "$*"
    return 2
}

base_docs_platform_opener() {
    local opener

    for opener in open xdg-open wslview; do
        if command -v "$opener" >/dev/null 2>&1; then
            printf '%s\n' "$opener"
            return 0
        fi
    done

    return 1
}

base_docs_open_url() {
    local opener

    if ! opener="$(base_docs_platform_opener)"; then
        print_error "No supported browser opener was found. Use 'basectl docs --show-url' to print the URL."
        return 1
    fi

    "$opener" "$BASE_DOCS_URL"
}

base_docs_subcommand_main() {
    local show_url=0

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_docs_subcommand_usage
                return 0
                ;;
            --show-url)
                show_url=1
                shift
                ;;
            -*)
                base_docs_usage_error "Unknown docs option '$1'."
                return $?
                ;;
            *)
                base_docs_usage_error "The 'docs' command does not accept positional arguments."
                return $?
                ;;
        esac
    done

    if ((show_url)); then
        printf '%s\n' "$BASE_DOCS_URL"
        return 0
    fi

    base_docs_open_url
}
