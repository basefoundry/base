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

caff_first_pgrep_match() {
    local pattern="$1"
    local pgrep_output status

    pgrep_output="$(pgrep "$pattern" 2>/dev/null)"
    status=$?
    if [[ "$status" -eq 0 ]]; then
        [[ -n "$pgrep_output" ]] || return 1
        printf '%s\n' "$pgrep_output" | sed -n '1p'
        return 0
    fi
    if [[ "$status" -eq 1 ]]; then
        return 1
    fi

    print_error "Unable to query process list for '$pattern'."
    return 2
}

caff_wait_pid_from_caffeinate_args() {
    local args_line="$1"
    local arg rest
    local waiting_for_pid=false
    local args=()

    read -r -a args <<< "$args_line"
    for arg in "${args[@]:1}"; do
        if [[ "$waiting_for_pid" == true ]]; then
            printf '%s\n' "$arg"
            return 0
        fi

        case "$arg" in
            -w)
                waiting_for_pid=true
                ;;
            -w[0-9]*)
                printf '%s\n' "${arg#-w}"
                return 0
                ;;
            -*w*)
                rest="${arg#*w}"
                if [[ -n "$rest" ]]; then
                    printf '%s\n' "$rest"
                    return 0
                fi
                waiting_for_pid=true
                ;;
        esac
    done

    return 1
}

main() {
    local silent=0
    local process_name
    local target_pid
    local caffeinate_pid
    local caffeinated_pid
    local pgrep_status

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
    target_pid="$(caff_first_pgrep_match "$process_name")"
    pgrep_status=$?
    if [[ "$pgrep_status" -eq 1 ]]; then
        print_warn "'$process_name' process is not running."
        return 1
    fi
    [[ "$pgrep_status" -eq 0 ]] || return 1

    caffeinate_pid="$(caff_first_pgrep_match caffeinate)"
    pgrep_status=$?
    if [[ "$pgrep_status" -eq 2 ]]; then
        return 1
    fi
    if [[ "$pgrep_status" -eq 0 ]]; then
        caffeinated_pid="$(ps -o args= -p "$caffeinate_pid" | while IFS= read -r line; do caff_wait_pid_from_caffeinate_args "$line" && break; done)"
        if [[ "$caffeinated_pid" == "$target_pid" ]]; then
            ((silent)) || printf '%s\n' "Already caffeinating: $process_name pid=$target_pid, caffeinate pid=$caffeinate_pid"
            return 0
        fi
    fi

    printf '%s\n' "Caffeinating PID $target_pid"
    caffeinate -iw "$target_pid" & disown
}
