#!/usr/bin/env bash

#
# base_init.sh
#     Base runtime bootstrap for Bash commands and Base-enabled Bash shells.
#
# Purpose:
#     - validate that the runtime is Bash 4.2 or newer
#     - establish the exported BASE_* environment contract
#     - source the Base Bash standard library
#     - provide import_base_lib for convention-based Base library imports
#
# This file is intentionally not part of normal dotfile startup. It is sourced
# by bin/basectl before running Base commands/scripts, and by the Base runtime
# Bash shell started with `basectl` or `basectl shell`.
#

[[ -n "${__base_init_sourced__:-}" ]] && return 0
readonly __base_init_sourced__=1

base_init_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

base_init_resolve_path() {
    local source_path="${1:-}"
    local link_dir
    local target

    [[ -n "$source_path" ]] || return 1

    while [[ -L "$source_path" ]]; do
        link_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || return 1
        target="$(readlink "$source_path")" || return 1
        if [[ "$target" == /* ]]; then
            source_path="$target"
        else
            source_path="$link_dir/$target"
        fi
    done

    link_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || return 1
    printf '%s/%s\n' "$link_dir" "$(basename -- "$source_path")"
}

base_init_require_bash() {
    local current_version

    if [[ -z "${BASH_VERSION:-}" ]]; then
        base_init_error "Base runtime requires Bash."
        return 1
    fi

    current_version="${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}"
    if ((current_version < 42)); then
        base_init_error "Base runtime requires Bash 4.2 or newer; current version is ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}."
        return 1
    fi
}

base_init_resolve_home() {
    local source_path
    local source_dir

    if [[ -n "${BASE_HOME:-}" ]]; then
        [[ -d "$BASE_HOME" ]] || {
            base_init_error "BASE_HOME '$BASE_HOME' is not a directory or is not accessible."
            return 1
        }
        cd -- "$BASE_HOME" && pwd -P
        return $?
    fi

    source_path="$(base_init_resolve_path "${BASH_SOURCE[0]}")" || return 1
    source_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || return 1
    printf '%s\n' "$source_dir"
}

base_init_export_contract() {
    local base_home

    base_home="$(base_init_resolve_home)" || return 1

    export BASE_HOME="$base_home"
    export BASE_BIN_DIR="$BASE_HOME/bin"
    export BASE_CLI_DIR="$BASE_HOME/cli"
    export BASE_BASH_DIR="$BASE_CLI_DIR/bash"
    export BASE_BASH_COMMANDS_DIR="$BASE_BASH_DIR/commands"
    export BASE_LIB_DIR="$BASE_HOME/lib"
    export BASE_BASH_LIB_DIR="$BASE_LIB_DIR/bash"
    export BASE_SHELL_DIR="$BASE_LIB_DIR/shell"
    export BASE_OS="$(uname -s)"
    export BASE_HOST="$(hostname -s)"
}

base_init_source_stdlib() {
    local stdlib_path="$BASE_BASH_LIB_DIR/std/lib_std.sh"

    [[ -f "$stdlib_path" ]] || {
        base_init_error "Base Bash stdlib '$stdlib_path' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$stdlib_path"
}

import_base_lib() {
    local relative_path="${1:-}"
    local lib_path

    [[ -n "$relative_path" ]] || fatal_error "import_base_lib: no library path provided."
    [[ "$relative_path" != /* ]] || fatal_error "import_base_lib: expected a path relative to '$BASE_BASH_LIB_DIR', got '$relative_path'."

    case "$relative_path" in
        ..|../*|*/..|*/../*)
            fatal_error "import_base_lib: refusing path outside Base Bash library root: '$relative_path'."
            ;;
    esac

    lib_path="$BASE_BASH_LIB_DIR/$relative_path"
    [[ -f "$lib_path" ]] || fatal_error "Base library '$relative_path' was not found at '$lib_path'."

    # shellcheck source=/dev/null
    source "$lib_path" || fatal_error "Failed to import Base library '$lib_path'."
}

base_init_main() {
    base_init_require_bash || return 1
    base_init_export_contract || return 1
    base_init_source_stdlib "$@" || return 1

    add_to_path -p "$BASE_BIN_DIR"
    export PATH
}

base_init_main "$@" || return $?
