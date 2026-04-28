[[ -n "${__base_shell_startup_sourced__:-}" ]] && return 0
readonly __base_shell_startup_sourced__=1

base_shell_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

base_shell_source_defaults() {
    local shell_name="$1"
    local defaults_script=""

    [[ "${BASE_ENABLE_SHELL_DEFAULTS:-false}" == true ]] || return 0

    case "$shell_name" in
        bash) defaults_script="$BASE_HOME/lib/base_defaults.sh" ;;
        zsh)  defaults_script="$BASE_HOME/lib/zsh_defaults.sh" ;;
        *)
            base_shell_error "Unknown shell '$shell_name' for default settings."
            return 1
            ;;
    esac

    [[ -f "$defaults_script" ]] || return 0

    # shellcheck source=/dev/null
    source "$defaults_script"
}

base_shell_source_base_init() {
    local script="$BASE_HOME/base_init.sh"

    [[ -n "${BASE_HOME:-}" ]] || {
        base_shell_error "BASE_HOME is not set."
        return 1
    }
    [[ -f "$script" ]] || {
        base_shell_error "Base init script '$script' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$script"
}

base_shell_startup_interactive() {
    local shell_name="$1"

    base_shell_source_defaults "$shell_name" || return 1
    base_shell_source_base_init || return 1
}
