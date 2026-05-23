#!/usr/bin/env bash

#
# caff: call caffeinate for a named process.
#

caff_show_help() {
    cat <<'EOF'
Caffeinate a named process.

Usage:
  caff [-s] <process-name>

Options:
  -s          Suppress the already-caffeinating message.
  -h, --help  Show this help text.
EOF
}

caff_describe() {
    printf '%s\n' "Caffeinate a named process"
}

main() {
    local silent=0
    local process_name
    local target_pid
    local caffeinate_pid
    local caffeinated_pid

    case "${1:-}" in
        -h|--help)
            caff_show_help
            return 0
            ;;
        --describe)
            caff_describe
            return 0
            ;;
        -s)
            silent=1
            shift
            ;;
    esac

    if ! command -v caffeinate >/dev/null 2>&1; then
        print_error "There is no caffeinate command on your system."
        return 1
    fi

    if (($# != 1)); then
        print_error "A process name is required."
        caff_show_help >&2
        return 2
    fi

    process_name="$1"
    target_pid="$(pgrep "$process_name" | head -1)"
    if [[ ! "$target_pid" ]]; then
        print_warn "'$process_name' process is not running."
        return 1
    fi

    caffeinate_pid="$(pgrep caffeinate | head -1)"
    if [[ "$caffeinate_pid" ]]; then
        caffeinated_pid="$(ps -o args -p "$caffeinate_pid" | awk 'NR==2 {print $3}')"
        if [[ "$caffeinated_pid" == "$target_pid" ]]; then
            ((silent)) || printf '%s\n' "Already caffeinating: $process_name pid=$target_pid, caffeinate pid=$caffeinate_pid"
            return 0
        fi
    fi

    printf '%s\n' "Caffeinating PID $target_pid"
    caffeinate -iw "$target_pid" & disown
}
