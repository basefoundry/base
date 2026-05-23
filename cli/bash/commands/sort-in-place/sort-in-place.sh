#!/usr/bin/env bash

#
# sort-in-place: sort files in place.
#

sort_in_place_show_help() {
    cat <<'EOF'
Sort text files in place.

Usage:
  sort-in-place [-u] <file>...

Options:
  -u          Remove duplicate lines while sorting.
  -h, --help  Show this help text.
EOF
}

sort_in_place_describe() {
    printf '%s\n' "Sort text files in place"
}

main() {
    local sort_args=()
    local file
    local temp_file
    local rc=0

    case "${1:-}" in
        -h|--help)
            sort_in_place_show_help
            return 0
            ;;
        --describe)
            sort_in_place_describe
            return 0
            ;;
        -u)
            sort_args=(-u)
            shift
            ;;
    esac

    if (($# == 0)); then
        print_error "At least one file is required."
        sort_in_place_show_help >&2
        return 2
    fi

    for file in "$@"; do
        if [[ ! -f "$file" ]]; then
            print_warn "$file is not a regular file; skipping."
            continue
        fi

        temp_file="$file._tmp"
        if [[ -f "$temp_file" ]]; then
            print_warn "$temp_file already exists; skipping $file."
            continue
        fi

        if ! sort "${sort_args[@]}" "$file" > "$temp_file"; then
            print_error "Can't write to '$temp_file'."
            rc=1
            continue
        fi

        if ! mv -- "$temp_file" "$file"; then
            print_error "Can't move '$temp_file' to '$file'."
            rc=1
        fi
    done

    return "$rc"
}
