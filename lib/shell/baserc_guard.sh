# shellcheck shell=bash

#
# baserc_guard.sh
#     Shared Bash helper for safely loading user-managed ~/.baserc.
#
# Purpose:
#     - source ~/.baserc at most once per shell
#     - allow simple user-managed Base preferences such as BASE_DEBUG=1
#     - reject and restore Base-owned variables when ~/.baserc tries to set them
#     - keep Bash dotfile snippets and runtime rcfile from duplicating this logic
#
# Callers should define their own debug function, then call:
#
#     base_baserc_guard_source caller_debug_function
#
# This helper is Bash-only. Zsh startup snippets keep their own implementation
# until Base has stronger Zsh-specific coverage.
#

[[ -n "${__base_baserc_guard_sourced__:-}" ]] && return 0
readonly __base_baserc_guard_sourced__=1

base_baserc_guard_debug() {
    local debug_function="${1:-}"
    [[ $# -gt 0 ]] && shift

    [[ -n "$debug_function" ]] || return 0
    declare -F "$debug_function" >/dev/null 2>&1 || return 0
    "$debug_function" "$*"
}

base_baserc_guard_owned_vars() {
    cat <<'EOF'
BASE_HOME
BASE_BIN_DIR
BASE_CLI_DIR
BASE_BASH_DIR
BASE_BASH_COMMANDS_DIR
BASE_LIB_DIR
BASE_BASH_LIB_DIR
BASE_SHELL_DIR
BASE_OS
BASE_HOST
BASE_SHELL
BASE_PLATFORM_TOOLS_HOME
BASE_PLATFORM_TOOLS_BIN_DIR
BASE_BASH_COMMAND_NAME
BASE_BASH_COMMAND_DIR
BASE_BASH_COMMAND_SCRIPT
BASE_PROJECT
BASE_PROJECT_ROOT
BASE_PROJECT_MANIFEST
BASE_PROJECT_VENV_DIR
BASE_PROFILE_VERSION
BASE_ENABLE_BASH_DEFAULTS
BASE_ENABLE_ZSH_DEFAULTS
EOF
}

base_baserc_guard_reject_owned_var() {
    local var_name="$1"
    local before_set="$2"
    local before_value="$3"
    local after_set
    local after_value

    after_set="${!var_name+x}"
    after_value="${!var_name-}"

    if [[ "$after_set" == "$before_set" && "$after_value" == "$before_value" ]]; then
        return 0
    fi

    if [[ -n "$before_set" ]]; then
        printf -v "$var_name" '%s' "$before_value"
    else
        unset "$var_name"
    fi

    printf "ERROR: ~/.baserc must not set Base-owned variable '%s'.\n" "$var_name" >&2
    return 1
}

base_baserc_guard_source() {
    local debug_function="${1:-}"
    local baserc="${2:-$HOME/.baserc}"
    local base_owned_vars
    local var_name
    local snapshot_name
    local snapshot_set_name
    local snapshot_value_name
    local before_set
    local before_value
    local baserc_status=0

    [[ -n "${__base_baserc_sourced__:-}" ]] && return 0
    [[ -f "$baserc" && -r "$baserc" ]] || return 0

    base_owned_vars="$(base_baserc_guard_owned_vars)"
    for var_name in $base_owned_vars; do
        snapshot_name="base_baserc_guard_before_$var_name"
        snapshot_set_name="${snapshot_name}_set"
        snapshot_value_name="${snapshot_name}_value"
        local "$snapshot_set_name" "$snapshot_value_name"
        printf -v "$snapshot_set_name" '%s' "${!var_name+x}"
        printf -v "$snapshot_value_name" '%s' "${!var_name-}"
    done

    __base_baserc_sourced__=1
    # shellcheck source=/dev/null
    source "$baserc" || {
        unset __base_baserc_sourced__
        printf "ERROR: Failed to source Base user config '%s'.\n" "$baserc" >&2
        return 1
    }

    for var_name in $base_owned_vars; do
        snapshot_name="base_baserc_guard_before_$var_name"
        snapshot_set_name="${snapshot_name}_set"
        snapshot_value_name="${snapshot_name}_value"
        before_set="${!snapshot_set_name-}"
        before_value="${!snapshot_value_name-}"
        base_baserc_guard_reject_owned_var "$var_name" "$before_set" "$before_value" || baserc_status=1
    done

    if [[ "$baserc_status" -ne 0 ]]; then
        unset __base_baserc_sourced__
        return "$baserc_status"
    fi

    base_baserc_guard_debug "$debug_function" "sourced '$baserc'"
}
