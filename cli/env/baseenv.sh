#!/usr/bin/env bash

#
# baseenv.sh
#     Sets up the Base CLI shell environment.
#     Source this file from base-wrapper or from ~/.bashrc / ~/.zshrc:
#         source /path/to/base/cli/env/baseenv.sh
#     Compatible with both bash and zsh.
#

baseenv_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

baseenv_is_sourced() {
    if [[ -n "${BASH_VERSION:-}" ]]; then
        [[ "${BASH_SOURCE[0]}" != "$0" ]]
        return
    fi

    if [[ -n "${ZSH_VERSION:-}" ]]; then
        [[ "$(eval 'printf "%s\n" "${(%):-%x}"')" != "$0" ]]
        return
    fi

    return 1
}

baseenv_get_source_path() {
    if [[ -n "${BASH_VERSION:-}" ]]; then
        printf '%s\n' "${BASH_SOURCE[0]}"
        return 0
    fi

    if [[ -n "${ZSH_VERSION:-}" ]]; then
        eval 'printf "%s\n" "${(%):-%x}"'
        return 0
    fi

    return 1
}

baseenv_prepend_path() {
    local dir="$1"

    [[ -n "$dir" && -d "$dir" ]] || return 0

    case ":${PATH:-}:" in
        *":$dir:"*) ;;
        *)
            if [[ -n "${PATH:-}" ]]; then
                PATH="$dir:$PATH"
            else
                PATH="$dir"
            fi
            export PATH
            ;;
    esac
}

baseenv_main() {
    local source_path env_dir cli_root repo_root bash_root python_root

    source_path="$(baseenv_get_source_path)" || {
        baseenv_error "Unable to determine the path to baseenv.sh."
        return 1
    }
    [[ -n "$source_path" ]] || {
        baseenv_error "Unable to determine the path to baseenv.sh."
        return 1
    }

    env_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || {
        baseenv_error "Unable to resolve cli/env root from '$source_path'."
        return 1
    }
    cli_root="$(cd -- "$env_dir/.." && pwd -P)" || {
        baseenv_error "Unable to resolve cli root from '$env_dir'."
        return 1
    }
    repo_root="$(cd -- "$cli_root/.." && pwd -P)" || {
        baseenv_error "Unable to resolve repository root from '$cli_root'."
        return 1
    }

    bash_root="$cli_root/bash"
    python_root="$cli_root/python"

    export BASE_REPO_ROOT="$repo_root"
    export BASE_CLI_ROOT="$cli_root"
    export BASE_CLI_ENV_SCRIPT="$env_dir/baseenv.sh"
    export BASE_BASH_ROOT="$bash_root"
    export BASE_PYTHON_ROOT="$python_root"

    BASE_CLI_ENV_DIR="$env_dir"
    BASE_BASH_BIN_DIR="$bash_root/bin"
    BASE_BASH_LIB_DIR="$repo_root/lib/bash"
    BASE_BASH_COMMANDS_DIR="$bash_root/commands"

    baseenv_prepend_path "$BASE_BASH_BIN_DIR"

    return 0
}

if ! baseenv_is_sourced; then
    baseenv_error "baseenv.sh must be sourced, not executed."
    baseenv_error "Use: source /path/to/base/cli/env/baseenv.sh"
    exit 1
fi

baseenv_main
_baseenv_rc=$?
unset -f baseenv_error baseenv_is_sourced baseenv_get_source_path baseenv_prepend_path baseenv_main
if [[ $_baseenv_rc -ne 0 ]]; then
    return "$_baseenv_rc"
fi
unset _baseenv_rc
