#!/usr/bin/env bash

#
# banyanenv.sh
#     Sets up the Base CLI shell environment.
#     Source this file from bash-wrapper or from ~/.bashrc / ~/.zshrc:
#         source /path/to/base/cli/env/banyanenv.sh
#     Compatible with both bash and zsh.
#

banyanenv_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

banyanenv_is_sourced() {
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

banyanenv_get_source_path() {
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

banyanenv_prepend_path() {
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

banyanenv_main() {
    local source_path env_dir cli_root repo_root bash_root python_root

    source_path="$(banyanenv_get_source_path)" || {
        banyanenv_error "Unable to determine the path to banyanenv.sh."
        return 1
    }
    [[ -n "$source_path" ]] || {
        banyanenv_error "Unable to determine the path to banyanenv.sh."
        return 1
    }

    env_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || {
        banyanenv_error "Unable to resolve cli/env root from '$source_path'."
        return 1
    }
    cli_root="$(cd -- "$env_dir/.." && pwd -P)" || {
        banyanenv_error "Unable to resolve cli root from '$env_dir'."
        return 1
    }
    repo_root="$(cd -- "$cli_root/.." && pwd -P)" || {
        banyanenv_error "Unable to resolve repository root from '$cli_root'."
        return 1
    }

    bash_root="$cli_root/bash"
    python_root="$cli_root/python"

    export BANYAN_REPO_ROOT="$repo_root"
    export BANYAN_CLI_ROOT="$cli_root"
    export BANYAN_CLI_ENV_DIR="$env_dir"
    export BANYAN_CLI_ENV_SCRIPT="$env_dir/banyanenv.sh"
    export BANYAN_BASH_ROOT="$bash_root"
    export BANYAN_BASH_BIN_DIR="$bash_root/bin"
    export BANYAN_BASH_LIB_DIR="$bash_root/lib"
    export BANYAN_BASH_COMMANDS_DIR="$bash_root/commands"
    export BANYAN_PYTHON_ROOT="$python_root"

    banyanenv_prepend_path "$BANYAN_BASH_BIN_DIR"

    return 0
}

if ! banyanenv_is_sourced; then
    banyanenv_error "banyanenv.sh must be sourced, not executed."
    banyanenv_error "Use: source /path/to/base/cli/env/banyanenv.sh"
    exit 1
fi

banyanenv_main
_banyanenv_rc=$?
unset -f banyanenv_error banyanenv_is_sourced banyanenv_get_source_path banyanenv_prepend_path banyanenv_main
if [[ $_banyanenv_rc -ne 0 ]]; then
    return "$_banyanenv_rc"
fi
unset _banyanenv_rc
