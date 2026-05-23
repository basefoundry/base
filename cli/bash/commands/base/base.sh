#!/usr/bin/env bash

base_cli_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

base_cli_show_help() {
    cat <<'EOF'
Usage: basectl [options] <command> [args...]

Commands:
  setup [options]
    Install and bootstrap the local Base CLI environment on macOS.
  check [options]
    Verify the local Base CLI environment without making changes.
  update-profile [options]
    Create or update Base-managed sections in Bash and Zsh startup files.
  shell
    Start an interactive Bash shell with the Base runtime loaded.
  help
    Show this help text.

Options:
  -v       Enable DEBUG logging for the selected command.
  -x       Enable Bash xtrace before running the command.
  -h       Show this help text.

Notes:
  - `basectl setup` is the preferred entrypoint for machine bootstrap.
  - `basectl check` verifies the same local requirements without making changes.
  - Invoking `basectl` with no command opens an interactive shell when attached to
    a terminal; otherwise it prints this help text.
EOF
}

base_cli_describe() {
    printf '%s\n' "Base umbrella CLI"
}

base_cli_usage_error() {
    base_cli_error "$*"
    base_cli_show_help >&2
    return 2
}

base_cli_get_base_home() {
    [[ -n "${HOME:-}" ]] || {
        base_cli_error "Environment variable 'HOME' is not set."
        return 1
    }
    [[ -d "$HOME" ]] || {
        base_cli_error "\$HOME '$HOME' is not a directory."
        return 1
    }

    [[ -n "${BASE_HOME:-}" ]] || {
        base_cli_error "BASE_HOME is not set. Run this command through bin/basectl."
        return 1
    }
    [[ -d "$BASE_HOME" ]] || {
        base_cli_error "BASE_HOME '$BASE_HOME' is not a directory."
        return 1
    }
    export BASE_HOME
}

base_cli_verify_home() {
    local base_home="$1"
    local file missing=()

    if [[ ! -d "$base_home" ]]; then
        BASE_CLI_ERROR_MESSAGE="Base home '$base_home' is not a directory."
        return 1
    fi

    for file in base_init.sh lib/shell/bash_profile lib/shell/bashrc lib/bash/runtime/bashrc bin/basectl cli/bash/commands/base/base.sh; do
        if [[ ! -f "$base_home/$file" ]]; then
            missing+=("$file")
        fi
    done

    if (( ${#missing[@]} > 0 )); then
        BASE_CLI_ERROR_MESSAGE="Files missing in Base home '$base_home': ${missing[*]}"
        return 1
    fi

    return 0
}

base_cli_runtime_base_home() {
    if base_cli_verify_home "$BASE_HOME"; then
        printf '%s\n' "$BASE_HOME"
        return 0
    fi

    return 1
}

base_cli_shell_rc_path() {
    local base_home

    base_home="$(base_cli_runtime_base_home)" || return 1
    printf '%s\n' "$base_home/lib/bash/runtime/bashrc"
}


base_cli_enable_debug_logging() {
    set_log_level DEBUG
    export LOG_DEBUG=1
}

base_cli_source_subcommand_module() {
    local module_name="$1"
    local subcommand_script="$__SCRIPT_DIR__/subcommands/${module_name}.sh"

    [[ -f "$subcommand_script" ]] || {
        base_cli_error "Subcommand module '$subcommand_script' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$subcommand_script"
}

base_cli_do_setup() {
    base_cli_source_subcommand_module setup || return 1
    base_setup_subcommand_main "$@"
}

base_cli_do_check() {
    base_cli_source_subcommand_module check || return 1
    base_check_subcommand_main "$@"
}

base_cli_do_update_profile() {
    base_cli_source_subcommand_module update_profile || return 1
    base_update_profile_subcommand_main "$@"
}

base_cli_do_shell() {
    local shell_rc

    shell_rc="$(base_cli_shell_rc_path)" || {
        base_cli_error "$BASE_CLI_ERROR_MESSAGE"
        return 1
    }

    export BASE_HOME
    export BASE_SHELL=1
    exec "${BASH:-bash}" --rcfile "$shell_rc"
}


base_cli_main() {
    local base_debug=0 command=""
    local opt

    if [[ "${1:-}" =~ ^(-h|--help|-help|help)$ ]]; then
        base_cli_show_help
        return 0
    fi

    if [[ "${1:-}" == "--describe" ]]; then
        base_cli_describe
        return 0
    fi

    case "${1:-}" in
        --*)
            base_cli_usage_error "Unknown option '$1'"
            return $?
            ;;
    esac

    OPTIND=1
    OPTERR=0
    while getopts ":hvx" opt; do
        case "$opt" in
            v) base_debug=1 ;;
            x) set -x ;;
            h)
                base_cli_show_help
                return 0
                ;;
            \?)
                base_cli_usage_error "Unknown option '-$OPTARG'"
                return $?
                ;;
            :)
                base_cli_usage_error "Option '-$OPTARG' requires an argument."
                return $?
                ;;
        esac
    done
    shift $((OPTIND - 1))

    command="${1:-}"
    [[ -n "$command" ]] && shift

    base_cli_get_base_home || return 1
    ((base_debug)) && base_cli_enable_debug_logging
    log_debug "Running basectl command '${command:-<none>}' with args: $*"

    case "$command" in
        check)            base_cli_do_check "$@" ;;
        setup)            base_cli_do_setup "$@" ;;
        help)             base_cli_show_help ;;
        shell)            base_cli_do_shell ;;
        update-profile)   base_cli_do_update_profile "$@" ;;
        "")
            if is_interactive; then
                base_cli_do_shell
            else
                base_cli_show_help
            fi
            ;;
        *)
            base_cli_usage_error "Unrecognized command: $command"
            ;;
    esac
}

main() {
    base_cli_main "$@"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
